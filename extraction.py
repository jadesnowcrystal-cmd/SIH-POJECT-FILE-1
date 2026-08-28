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
logger = logging.getLogger("RAGExtractorEngine")

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
    """
    In-memory Vector Store simulating a RAG retrieval system.
    Handles chunking, vectorization, indexing, and semantic similarity search.
    """
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
            logger.warning("Retrieval attempted on an empty or unindexed VectorStore.")
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
    """Handles entity normalization and deterministic MD5 unique ID assignment."""
    @staticmethod
    def generate_id(entity_type: str, normalized_value: str) -> str:
        raw_str = f"{entity_type.upper()}:{normalized_value.lower().strip()}"
        hash_digest = hashlib.md5(raw_str.encode("utf-8")).hexdigest()[:6]
        return f"{entity_type.lower()}_{hash_digest}"

    @staticmethod
    def normalize_value(entity_type: str, raw_val: str) -> str:
        clean_val = raw_val.strip()
        if entity_type == "PHONE":
            digits = re.sub(r"\D", "", clean_val)
            return f"+91{digits[-10:]}" if len(digits) >= 10 else clean_val
        elif entity_type == "VEHICLE":
            return re.sub(r"[\s-]", "", clean_val).upper()
        elif entity_type in ["PERSON", "LOCATION", "ORGANIZATION"]:
            return re.sub(r"\s+", " ", clean_val).title()
        return clean_val


class RAGExtractorEngine:
    """Primary pipeline class handling feature extraction and context retrieval."""
    def __init__(self, chunk_size: int = 150):
        self.vector_store = SimpleVectorStore(chunk_size=chunk_size)
        self.resolver = EntityResolver()

    def _extract_raw_entities(self, text: str) -> List[Dict[str, Any]]:
        raw_entities = []

        # 1. Regex Entity Processing
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
            e_id = self.resolver.generate_id(e_type, norm_val)

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

    def _extract_keywords(self, text: str) -> List[str]:
        text_lower = text.lower()
        return [
            kw for kw in DOMAIN_KEYWORDS 
            if re.search(rf"\b{re.escape(kw)}\b", text_lower)
        ]

    def process(self, document_text: str, case_id: str = "CASE-RAG-001") -> Dict[str, Any]:
        """Runs the complete RAG + Extraction Pipeline on raw input text."""
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

        raw_entities = self._extract_raw_entities(clean_doc)
        entities = self._resolve_entities(raw_entities)
        relations = self._extract_relations(clean_doc, entities)
        keywords = self._extract_keywords(clean_doc)

        return {
            "metadata": {
                "case_id": case_id,
                "processed_at": datetime.now().isoformat(),
                "rag_indexed_chunks": indexed_chunks_count,
                "total_entities_found": len(entities),
                "total_relations_found": len(relations),
                "status": "SUCCESS"
            },
            "rag_retrieved_evidence": retrieved_contexts,
            "entities": entities,
            "relations": relations,
            "keywords": sorted(list(set(keywords)))
        }


def process_case_data(case_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Adapter routine to ingest synthetic dictionary outputs generated by 
    fakedatagenration.py and translate them into full unstructured intelligence reports.
    """
    victim = case_data.get("Victim") or {}
    accused = case_data.get("Accused") or {}
    witness = case_data.get("Witness") or {}
    informant = case_data.get("Informant") or {}

    accused_name = accused.get('Name', 'Unknown Suspect')
    accused_addr = accused.get('Address', 'Unknown Location')
    accused_phone = accused.get('Phone number', 'N/A')

    accused_str = (
        f"The suspect involved was identified as {accused_name} living at {accused_addr} "
        f"(Phone: {accused_phone})." if accused else "The suspect remains unknown."
    )

    narrative_report = f"""
    On {case_data.get('Occurrence Date', 'N/A')} at {case_data.get('Occurrence Time', 'N/A')}, an incident of {case_data.get('Case Type', 'Crime')} occurred in {case_data.get('Place of Occurrence', 'Location')}, {case_data.get('District', 'Region')}.
    The incident was formally reported on {case_data.get('Report Date', 'N/A')} at {case_data.get('Report Time', 'N/A')}.
    The victim involved is {victim.get('Name', 'Unknown')} residing at {victim.get('Address', 'Unknown')} (Phone: {victim.get('Phone number', 'N/A')}).
    Informant {informant.get('Name', 'Unknown')} reported the matter to local authorities. 
    Witness {witness.get('Name', 'Unknown')} was present near the scene of occurrence.
    {accused_str}
    Initial investigation classified this as a {case_data.get('Connectivity', 'General')} event.
    """

    engine = RAGExtractorEngine()
    district_code = case_data.get('District', 'SYS').upper().replace(" ", "_")
    case_id = f"CASE-{district_code}-{datetime.now().strftime('%M%S')}"
    return engine.process(narrative_report, case_id=case_id)


def batch_process_cases(case_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Batch processes multiple case records generated by synthetic modules."""
    results = []
    logger.info(f"Starting batch extraction on {len(case_list)} case items...")
    for index, case_item in enumerate(case_list):
        try:
            processed = process_case_data(case_item)
            results.append(processed)
        except Exception as err:
            logger.error(f"Failed to process case at index {index}: {err}")
    logger.info(f"Batch processing complete. Successfully extracted {len(results)} records.")
    return results


if __name__ == "__main__":
    sample_case_report = """
    On 14 August 2026, Rahul Sharma met Sameer Verma near Vashi Station in Mumbai. 
    Rahul called Sameer on 9876543210 regarding a pending transaction. 
    Later that evening, Sameer transferred Rs. 80,000 to Rahul. 
    A black SUV with vehicle number MH-04-AB-1234 was spotted near the transfer site during the extortion attempt. 
    The suspect fled toward Pune after receiving the cash.
    """

    logger.info("Running standalone extraction execution test...")
    rag_engine = RAGExtractorEngine()
    output_payload = rag_engine.process(sample_case_report, case_id="CASE-2026-INV-99")
    print(json.dumps(output_payload, indent=2))
