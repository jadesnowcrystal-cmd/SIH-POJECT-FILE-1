import re
import json
import logging
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Configure logging for production debugging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger("JanviNLPModule")

# Optional spaCy loading with fallback configuration
try:
    import spacy
    nlp = spacy.load("en_core_web_sm")
    logger.info("Loaded spaCy NLP model 'en_core_web_sm' successfully.")
except Exception as e:
    nlp = None
    logger.warning("spaCy not found or model not downloaded. Defaulting to regex/rule-based processing.")

# Advanced Entity & Mapping Definitions
LABEL_MAPPINGS = {
    "PERSON": "PERSON",
    "ORG": "ORGANIZATION",
    "GPE": "LOCATION",
    "LOC": "LOCATION",
    "FAC": "LOCATION",
    "DATE": "DATE",
    "TIME": "TIME",
    "MONEY": "MONEY",
    "LAW": "LEGAL_REFERENCE",
    "NORP": "GROUP_IDENTITY"
}

REGEX_PATTERNS = {
    "PHONE": r"\b(?:\+91[\s-]?)?[6-9]\d{9}\b|\(\d{3}\)\s\d{3}-\d{4}",
    "VEHICLE": r"\b[A-Z]{2}[-\s]?\d{1,2}[-\s]?[A-Z]{1,3}[-\s]?\d{4}\b",
    "MONEY": r"(?:₹|Rs\.?|INR)\s?\d+(?:,\d+)*(?:\.\d+)?",
    "DATE": r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b",
    "TIME": r"\b(?:[01]?\d|2[0-3]):[0-5]\d(?:\s?[AP]M)?\b"
}

ACTION_KEYWORDS = {
    "MEETING": ["met", "meeting", "visited", "gathered", "spotted at", "seen with", "rendezvous"],
    "COMMUNICATION": ["called", "contacted", "phoned", "texted", "messaged", "emailed", "spoke"],
    "TRANSACTION": ["transferred", "sent", "paid", "gave", "deposited", "wired", "bribed"],
    "MOVEMENT": ["travelled", "drove", "fled", "arrived", "left", "escaped", "headed"]
}

DOMAIN_KEYWORDS = [
    "robbery", "theft", "fraud", "murder", "assault", "smuggling", 
    "extortion", "kidnapping", "cash", "vehicle", "deposit", "threat",
    "investigation", "suspect", "witness", "victim", "informant"
]


class ExtractionEngineError(Exception):
    """Custom exception class for Extraction and RAG processing pipeline."""
    pass


class SimpleVectorStore:
    """In-memory Vector Store handling chunking, vectorization, and indexing."""
    def __init__(self, chunk_size: int = 150, overlap: int = 1):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.chunks: List[Dict[str, Any]] = []
        self.vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1, 2))
        self.tfidf_matrix = None

    def chunk_text(self, text: str) -> List[str]:
        """Splits narrative reports into sliding structural sentence chunks."""
        if not text:
            return []
            
        if nlp:
            doc = nlp(text)
            sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
        else:
            sentences = [s.strip() for s in re.split(r'[.\n]+', text) if s.strip()]

        chunks = []
        current_chunk = []
        current_len = 0

        for sent in sentences:
            current_chunk.append(sent)
            current_len += len(sent)
            if current_len >= self.chunk_size:
                chunks.append(" ".join(current_chunk))
                current_chunk = current_chunk[-self.overlap:]
                current_len = sum(len(s) for s in current_chunk)

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return list(set(chunks))

    def index_document(self, doc_id: str, text: str) -> int:
        """Vectorizes text chunks and stores TF-IDF embeddings."""
        raw_chunks = self.chunk_text(text)
        if not raw_chunks:
            logger.warning(f"No valid chunks generated for document ID: {doc_id}")
            return 0

        self.chunks = [
            {
                "doc_id": doc_id,
                "chunk_id": f"{doc_id}_c{i}",
                "text": chunk,
                "length": len(chunk)
            }
            for i, chunk in enumerate(raw_chunks)
        ]

        chunk_texts = [c["text"] for c in self.chunks]
        try:
            self.tfidf_matrix = self.vectorizer.fit_transform(chunk_texts)
            logger.info(f"Successfully indexed {len(self.chunks)} chunks for document {doc_id}.")
        except Exception as err:
            logger.error(f"Failed to index document chunks: {err}")
            raise ExtractionEngineError(f"Vector indexing failed: {err}")
            
        return len(self.chunks)

    def retrieve(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Queries indexed document chunks based on cosine similarity."""
        if self.tfidf_matrix is None or len(self.chunks) == 0:
            return []

        try:
            query_vec = self.vectorizer.transform([query])
            similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
            top_indices = np.argsort(similarities)[::-1][:top_k]

            results = []
            for idx in top_indices:
                score = float(similarities[idx])
                if score > 0.02:
                    results.append({
                        "chunk": self.chunks[idx],
                        "relevance_score": round(score, 4)
                    })
            return results
        except Exception as err:
            logger.error(f"Error during query retrieval: {err}")
            return []


class EntityResolver:
    """Handles entity normalization and deterministic unique ID assignment."""
    @staticmethod
    def generate_id(entity_type: str, normalized_value: str) -> str:
        raw_str = f"{entity_type.upper()}:{normalized_value.lower().strip()}"
        hash_digest = hashlib.md5(raw_str.encode("utf-8")).hexdigest()[:6]
        return f"{entity_type.lower()}_{hash_digest}"

    @staticmethod
    def normalize_value(entity_type: str, raw_val: str) -> str:
        clean_val = str(raw_val).strip()
        if entity_type == "PHONE":
            digits = re.sub(r"\D", "", clean_val)
            return f"+91{digits[-10:]}" if len(digits) >= 10 else clean_val
        elif entity_type == "VEHICLE":
            return re.sub(r"[\s-]", "", clean_val).upper()
        elif entity_type in ["PERSON", "LOCATION", "ORGANIZATION"]:
            return re.sub(r"\s+", " ", clean_val).title()
        return clean_val


class RAGExtractorEngine:
    """Primary NLP & Network extraction engine connected to NEXUS database structure."""
    def __init__(self, chunk_size: int = 150):
        self.vector_store = SimpleVectorStore(chunk_size=chunk_size)
        self.resolver = EntityResolver()

    def _extract_raw_entities(self, text: str) -> List[Dict[str, Any]]:
        raw_entities = []

        # 1. Regex Entity Extraction
        for e_type, pattern in REGEX_PATTERNS.items():
            for match in re.finditer(pattern, text, re.IGNORECASE):
                raw_entities.append({
                    "type": e_type,
                    "value": match.group().strip()
                })

        # 2. spaCy NER Processing
        if nlp:
            doc = nlp(text)
            for ent in doc.ents:
                if ent.label_ in LABEL_MAPPINGS:
                    raw_entities.append({
                        "type": LABEL_MAPPINGS[ent.label_],
                        "value": ent.text.strip()
                    })

        return raw_entities

    def _resolve_entities(self, raw_entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        resolved = {}
        for entity in raw_entities:
            e_type = entity["type"]
            raw_val = entity["value"]
            norm_val = self.resolver.normalize_value(e_type, raw_val)
            
            # Preserve existing entity ID if available, otherwise generate deterministic ID
            e_id = entity.get("id") or self.resolver.generate_id(e_type, norm_val)

            if e_id not in resolved:
                resolved[e_id] = {
                    "id": e_id,
                    "type": e_type,
                    "value": raw_val,
                    "normalized_value": norm_val
                }
        return list(resolved.values())

    def _extract_relations(self, text: str, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        relations = []
        
        if nlp:
            sentences = [sent.text.strip() for sent in nlp(text).sents]
        else:
            sentences = [s.strip() for s in re.split(r'[.\n]+', text) if s.strip()]

        for sent_text in sentences:
            sent_lower = sent_text.lower()
            matching_entities = [
                e for e in entities 
                if e["value"] in sent_text or e["normalized_value"] in sent_text
            ]

            if len(matching_entities) >= 2:
                detected_action = "ASSOCIATED_WITH"
                for action, keywords in ACTION_KEYWORDS.items():
                    if any(kw in sent_lower for kw in keywords):
                        detected_action = action
                        break

                for i in range(len(matching_entities) - 1):
                    relations.append({
                        "source": matching_entities[i]["id"],
                        "target": matching_entities[i + 1]["id"],
                        "action": detected_action,
                        "context": sent_text
                    })

        return relations

    def _compute_network_analytics(self, entities: List[Dict[str, Any]], relations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculates degree centrality and key network metrics (Janvi's task)."""
        degree_count = {e["id"]: 0 for e in entities}
        
        for rel in relations:
            src, tgt = rel["source"], rel["target"]
            if src in degree_count:
                degree_count[src] += 1
            if tgt in degree_count:
                degree_count[tgt] += 1

        total_nodes = len(entities)
        centrality = {
            k: round(v / (total_nodes - 1), 4) if total_nodes > 1 else 0
            for k, v in degree_count.items()
        }

        # Find most central entity
        sorted_centrality = sorted(centrality.items(), key=lambda x: x[1], reverse=True)
        top_central_id = sorted_centrality[0][0] if sorted_centrality else None

        return {
            "node_count": total_nodes,
            "edge_count": len(relations),
            "degree_centrality": centrality,
            "top_central_entity_id": top_central_id
        }

    def process(self, document_text: str, case_id: str = "CASE-RAG-001", structured_entities: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Runs the complete RAG + Extraction + Network Analytics Pipeline."""
        clean_doc = re.sub(r"\s+", " ", document_text).strip()

        indexed_chunks_count = self.vector_store.index_document(doc_id=case_id, text=clean_doc)

        rag_queries = [
            "phone vehicle money transfer", 
            "met visited called meeting", 
            "extortion robbery fraud murder",
            "suspect victim witness report"
        ]
        
        retrieved_contexts = []
        for q in rag_queries:
            results = self.vector_store.retrieve(query=q, top_k=2)
            for res in results:
                retrieved_contexts.append(res)

        # Extract entities from unstructured text
        extracted_raw = self._extract_raw_entities(clean_doc)
        
        # Merge structured entities from Aditya's module if provided
        if structured_entities:
            extracted_raw.extend(structured_entities)

        entities = self._resolve_entities(extracted_raw)
        relations = self._extract_relations(clean_doc, entities)
        network_analytics = self._compute_network_analytics(entities, relations)

        return {
            "metadata": {
                "case_id": case_id,
                "processed_at": datetime.now().isoformat(),
                "rag_indexed_chunks": indexed_chunks_count,
                "total_entities_found": len(entities),
                "total_relations_found": len(relations),
                "status": "SUCCESS"
            },
            "network_analytics": network_analytics,
            "rag_retrieved_evidence": retrieved_contexts,
            "entities": entities,
            "relations": relations
        }


def process_case_data(case_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Adapter routine that ingests standard synthetic FIR structures generated by
    Aditya's module and translates them into investigative network intelligence.
    """
    case_id = case_data.get("case_id", f"CASE-{datetime.now().strftime('%M%S')}")
    rep_details = case_data.get("report_details", {})
    occ_details = case_data.get("occurrence_details", {})
    entities_data = case_data.get("entities", {})

    victim = entities_data.get("victim", {})
    accused = entities_data.get("accused") if isinstance(entities_data.get("accused"), dict) else {}
    witness = entities_data.get("witness", {})
    informant = entities_data.get("informant", {})

    accused_str = (
        f"The suspect involved was identified as {accused.get('name')} living at {accused.get('address')} "
        f"(Phone: {accused.get('phone_number')})." if accused else "The suspect remains unknown."
    )

    # Reconstruct readable narrative for RAG Vector Indexing
    narrative_report = f"""
    On {occ_details.get('date', 'N/A')} at {occ_details.get('time', 'N/A')}, an incident of {case_data.get('case_type', 'Crime')} occurred in {occ_details.get('place', 'Location')}, {case_data.get('district', 'Region')}.
    The incident was formally reported on {rep_details.get('date', 'N/A')} at {rep_details.get('time', 'N/A')}.
    The victim involved is {victim.get('name', 'Unknown')} residing at {victim.get('address', 'Unknown')} (Phone: {victim.get('phone_number', 'N/A')}).
    Informant {informant.get('name', 'Unknown')} reported the matter to local authorities. 
    Witness {witness.get('name', 'Unknown')} was present near the scene of occurrence.
    {accused_str}
    Initial investigation classified this as a {case_data.get('connectivity', 'General')} event.
    """

    # Format pre-structured person entities from Aditya's output
    structured_person_entities = []
    for role, person in entities_data.items():
        if isinstance(person, dict) and person.get("name"):
            structured_person_entities.append({
                "id": person.get("person_id"),
                "type": "PERSON",
                "value": person.get("name")
            })
            if person.get("phone_number"):
                structured_person_entities.append({
                    "type": "PHONE",
                    "value": person.get("phone_number")
                })

    engine = RAGExtractorEngine()
    return engine.process(narrative_report, case_id=case_id, structured_entities=structured_person_entities)


def batch_process_cases(case_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Batch processes multiple FIR records."""
    results = []
    logger.info(f"Starting batch extraction on {len(case_list)} case items...")
    for index, case_item in enumerate(case_list):
        try:
            processed = process_case_data(case_item)
            results.append(processed)
        except Exception as err:
            logger.error(f"Failed to process case at index {index}: {err}")
    logger.info(f"Batch processing complete. Successfully processed {len(results)} records.")
    return results


# ==========================================
# EXECUTION & INTEGRATION TEST
# ==========================================
if __name__ == "__main__":
    # Integration test with Aditya's generator format
    sample_fir = {
        "case_id": "FIR-2026-0001",
        "district": "Thane",
        "case_type": "Robbery",
        "connectivity": "Planed",
        "report_details": {"date": "25-08-26", "time": "14:30"},
        "occurrence_details": {"date": "20-08-26", "time": "21:00", "place": "Airoli"},
        "entities": {
            "informant": {"person_id": "PER-1001", "name": "Rahul Sharma", "phone_number": "(987) 654-3210"},
            "victim": {"person_id": "PER-1002", "name": "Amit Patel", "address": "Thane", "phone_number": "(912) 345-6789"},
            "witness": {"person_id": "PER-1003", "name": "Rohan Verma"},
            "accused": {"person_id": "PER-1004", "name": "Mogambo Singh", "address": "Airoli", "phone_number": "(999) 888-7777"}
        }
    }

    logger.info("Running integrated NLP and network analytics test...")
    output = process_case_data(sample_fir)
    print(json.dumps(output, indent=2))
