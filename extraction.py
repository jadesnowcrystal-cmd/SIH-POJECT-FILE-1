import re
import json
import hashlib
import numpy as np
from datetime import datetime
from typing import List, Dict, Any, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import spacy


try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    raise OSError("Please run: python -m spacy download en_core_web_sm")

LABEL_MAPPINGS = {
    "PERSON": "PERSON",
    "ORG": "ORGANIZATION",
    "GPE": "LOCATION",
    "LOC": "LOCATION",
    "FAC": "LOCATION",
    "DATE": "DATE",
    "TIME": "TIME",
    "MONEY": "MONEY"
}

REGEX_PATTERNS = {
    "PHONE": r"\b(?:\+91[\s-]?)?[6-9]\d{9}\b",
    "VEHICLE": r"\b[A-Z]{2}[-\s]?\d{1,2}[-\s]?[A-Z]{1,3}[-\s]?\d{4}\b",
    "MONEY": r"(?:₹|Rs\.?|INR)\s?\d+(?:,\d+)*(?:\.\d+)?",
    "DATE": r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b"
}

ACTION_KEYWORDS = {
    "MEETING": ["met", "meeting", "visited", "gathered", "spotted at", "seen with"],
    "COMMUNICATION": ["called", "contacted", "phoned", "texted", "messaged", "emailed"],
    "TRANSACTION": ["transferred", "sent", "paid", "gave", "deposited", "wired"],
    "MOVEMENT": ["travelled", "drove", "fled", "arrived", "left", "escaped"]
}

DOMAIN_KEYWORDS = [
    "robbery", "theft", "fraud", "murder", "assault", "smuggling", 
    "extortion", "kidnapping", "cash", "vehicle", "deposit", "threat"
]


# =====================================================================
# 2. VECTOR SEARCH & RAG RETRIEVAL ENGINE
# =====================================================================
class SimpleVectorStore:
    """
    In-memory vector store simulating a vector database (e.g., ChromaDB, Pinecone).
    Chunks text, builds TF-IDF embeddings, and performs similarity searches.
    """
    def __init__(self, chunk_size: int = 150):
        self.chunk_size = chunk_size
        self.chunks: List[Dict[str, Any]] = []
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.tfidf_matrix = None

    def chunk_text(self, text: str) -> List[str]:
        """Splits full text into overlapping sentence chunks."""
        doc = nlp(text)
        sentences = [sent.text.strip() for sent in doc.sents]
        chunks = []
        current_chunk = []
        current_len = 0

        for sent in sentences:
            current_chunk.append(sent)
            current_len += len(sent)
            if current_len >= self.chunk_size:
                chunks.append(" ".join(current_chunk))
                current_chunk = current_chunk[-1:]  # Overlap 1 sentence
                current_len = len(current_chunk[0])

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return list(set(chunks))

    def index_document(self, doc_id: str, text: str):
        """Indexes text chunks into vector space."""
        raw_chunks = self.chunk_text(text)
        self.chunks = [
            {"doc_id": doc_id, "chunk_id": f"{doc_id}_c{i}", "text": chunk}
            for i, chunk in enumerate(raw_chunks)
        ]
        chunk_texts = [c["text"] for c in self.chunks]
        if chunk_texts:
            self.tfidf_matrix = self.vectorizer.fit_transform(chunk_texts)

    def retrieve(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Retrieves top_k relevant context chunks for a given query."""
        if self.tfidf_matrix is None or len(self.chunks) == 0:
            return []

        query_vec = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            score = float(similarities[idx])
            if score > 0.05:  # Relevance threshold
                results.append({
                    "chunk": self.chunks[idx],
                    "relevance_score": round(score, 4)
                })
        return results



# 3. EXTRACTION & RESOLUTION LOGIC
# =====================================================================
class EntityResolver:
    """Handles entity normalization and deterministic hash ID generation."""
    @staticmethod
    def generate_id(entity_type: str, normalized_value: str) -> str:
        raw_str = f"{entity_type}:{normalized_value.lower().strip()}"
        hash_digest = hashlib.md5(raw_str.encode("utf-8")).hexdigest()[:6]
        return f"{entity_type.lower()}_{hash_digest}"

    @staticmethod
    def normalize_value(entity_type: str, raw_val: str) -> str:
        clean_val = raw_val.strip()
        if entity_type == "PHONE":
            digits = re.sub(r"\D", "", clean_val)
            return f"+91{digits[-10:]}"
        elif entity_type == "VEHICLE":
            return re.sub(r"[\s-]", "", clean_val).upper()
        elif entity_type in ["PERSON", "LOCATION", "ORGANIZATION"]:
            return re.sub(r"\s+", " ", clean_val).title()
        return clean_val


class RAGExtractorEngine:
    """Core extraction pipeline leveraging RAG context retrieval."""
    def __init__(self):
        self.vector_store = SimpleVectorStore()
        self.resolver = EntityResolver()

    def _extract_raw_entities(self, text: str) -> List[Dict[str, Any]]:
        raw_entities = []

        # 1. Regex Extraction
        for e_type, pattern in REGEX_PATTERNS.items():
            for match in re.finditer(pattern, text, re.IGNORECASE):
                raw_entities.append({
                    "type": e_type,
                    "value": match.group().strip()
                })

        # 2. spaCy NER Extraction
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
        doc = nlp(text)

        for sent in doc.sents:
            sent_text = sent.text.strip()
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
        """Runs the complete RAG + Extraction Pipeline."""
        # Clean text
        clean_doc = re.sub(r"\s+", " ", document_text).strip()

        # Step 1: Index document into local Vector Store
        self.vector_store.index_document(doc_id=case_id, text=clean_doc)

        # Step 2: Use RAG mode to retrieve highly relevant context blocks
        rag_queries = ["phone vehicle money transfer", "met visited called meeting", "extortion robbery fraud"]
        retrieved_contexts = []
        for q in rag_queries:
            results = self.vector_store.retrieve(query=q, top_k=2)
            for res in results:
                retrieved_contexts.append(res)

        # Step 3: Extract Entities and Relations from Full Context
        raw_entities = self._extract_raw_entities(clean_doc)
        entities = self._resolve_entities(raw_entities)
        relations = self._extract_relations(clean_doc, entities)
        keywords = self._extract_keywords(clean_doc)

        # Step 4: Construct structured JSON payload
        return {
            "metadata": {
                "case_id": case_id,
                "processed_at": datetime.now().isoformat(),
                "rag_indexed_chunks": len(self.vector_store.chunks),
                "status": "SUCCESS"
            },
            "rag_retrieved_evidence": retrieved_contexts,
            "entities": entities,
            "relations": relations,
            "keywords": sorted(list(set(keywords)))
        }


# =====================================================================
# 4. RUN PROTOTYPE & DISPLAY OUTPUT
# =====================================================================
if __name__ == "__main__":
    sample_case_report = """
    On 14 August 2026, Rahul Sharma met Sameer Verma near Vashi Station in Mumbai. 
    Rahul called Sameer on 9876543210 regarding a pending transaction. 
    Later that evening, Sameer transferred Rs. 80,000 to Rahul. 
    A black SUV with vehicle number MH-04-AB-1234 was spotted near the transfer site during the extortion attempt. 
    The suspect fled toward Pune after receiving the cash.
    """

    print("==================================================================")
    print("                      RAW INPUT CASE REPORT                       ")
    print("==================================================================")
    print(sample_case_report.strip())

    # Instantiate RAG Engine and process document
    rag_engine = RAGExtractorEngine()
    output_payload = rag_engine.process(sample_case_report, case_id="CASE-2026-INV-99")

    print("\n==================================================================")
    print("                     STRUCTURED RAG JSON OUTPUT                   ")
    print("==================================================================")
    print(json.dumps(output_payload, indent=2))
