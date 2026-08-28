import os
import json
import logging
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from neo4j import GraphDatabase
import networkx as nx

logging.basicConfig(level=logging.INFO)

# ==========================================
# 1. NEO4J PERSISTENCE ENGINE & INDEXING
# ==========================================

class Neo4jEngine:
    def __init__(self):
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "password")
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self._setup_database_schema()

    def close(self):
        self.driver.close()

    def _setup_database_schema(self):
        """Create uniqueness constraints and indexes for high-performance lookup."""
        constraints = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Person) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (ph:Phone) REQUIRE ph.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (a:FinancialAccount) REQUIRE a.id IS UNIQUE",
            "CREATE INDEX IF NOT EXISTS FOR (p:Person) ON (p.name)"
        ]
        with self.driver.session() as session:
            for constraint in constraints:
                session.run(constraint)
        logging.info("Neo4j Schema constraints and indexes verified.")

    def batch_upsert_network(self, entities: List[Dict[str, Any]], relationships: List[Dict[str, Any]]):
        """Perform high-performance batch operations using Cypher UNWIND."""
        query_nodes = """
        UNWIND $entities AS entity
        CALL apoc.merge.node([entity.type], {id: entity.id}, entity.properties, {}) YIELD node
        RETURN count(node)
        """
        # Standard fallback if APOC is not enabled:
        cypher_nodes = """
        UNWIND $entities AS entity
        MERGE (n:Entity {id: entity.id})
        SET n.type = entity.type, n += entity.properties
        """
        
        cypher_rels = """
        UNWIND $relationships AS rel
        MATCH (source {id: rel.source})
        MATCH (target {id: rel.target})
        MERGE (source)-[r:RELATIONSHIP {type: rel.type}]->(target)
        SET r.confidence = rel.confidence, r.frequency = rel.frequency
        """
        with self.driver.session() as session:
            session.run(cypher_nodes, entities=entities)
            session.run(cypher_rels, relationships=relationships)

    def get_subgraph(self, entity_id: str, depth: int = 2) -> Dict[str, Any]:
        """Fetch surrounding graph topology."""
        query = f"""
        MATCH (start {{id: $entity_id}})
        MATCH path = (start)-[*1..{depth}]-(connected)
        UNWIND nodes(path) AS n
        UNWIND relationships(path) AS r
        RETURN collect(DISTINCT {{id: n.id, type: n.type, name: n.name}}) AS nodes,
               collect(DISTINCT {{source: startNode(r).id, target: endNode(r).id, type: r.type}}) AS relationships
        """
        with self.driver.session() as session:
            res = session.run(query, entity_id=entity_id).single()
            if not res:
                return {"nodes": [], "relationships": []}
            return {"nodes": res["nodes"], "relationships": res["relationships"]}

    def get_shortest_path(self, source_id: str, target_id: str) -> Optional[Dict[str, Any]]:
        query = """
        MATCH (start {id: $source_id}), (end {id: $target_id})
        MATCH path = shortestPath((start)-[*..10]-(end))
        RETURN [node IN nodes(path) | node.id] AS nodes,
               [rel IN relationships(path) | rel.type] AS relationships
        """
        with self.driver.session() as session:
            res = session.run(query, source_id=source_id, target_id=target_id).single()
            if res:
                return {"nodes": res["nodes"], "relationships": res["relationships"]}
            return None

# ==========================================
# 2. AUTOMATED INGESTION & PARSING ENGINE
# ==========================================

class IngestionEngine:
    """Parses raw metadata extractions into standardized graph documents."""
    
    @staticmethod
    def process_raw_extracted_payload(payload: Dict[str, Any]) -> tuple:
        entities = []
        relationships = []
        
        for item in payload.get("extracted_entities", []):
            entities.append({
                "id": item["entity_id"],
                "type": item["entity_type"],
                "properties": item.get("metadata", {})
            })
            
        for rel in payload.get("extracted_relations", []):
            relationships.append({
                "source": rel["src"],
                "target": rel["dst"],
                "type": rel["relation"],
                "confidence": rel.get("confidence", 1.0),
                "frequency": rel.get("frequency", 1)
            })
            
        return entities, relationships

# ==========================================
# 3. REST API SERVICE (FASTAPI)
# ==========================================

app = FastAPI(title="Network Intelligence Query Service API", version="1.0.0")
db_engine = Neo4jEngine()

class IngestRequest(BaseModel):
    extracted_entities: List[Dict[str, Any]]
    extracted_relations: List[Dict[str, Any]]

@app.post("/api/v1/ingest")
async def ingest_data(payload: IngestRequest):
    """Ingest extracted unstructured metadata into graph database."""
    try:
        entities, relationships = IngestionEngine.process_raw_extracted_payload(payload.dict())
        db_engine.batch_upsert_network(entities, relationships)
        return {"status": "success", "ingested_nodes": len(entities), "ingested_edges": len(relationships)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/graph/subgraph")
async def fetch_subgraph(entity_id: str = Query(..., description="Target node ID"), depth: int = Query(2, ge=1, le=5)):
    """API Endpoint for frontend UI graph visualization."""
    data = db_engine.get_subgraph(entity_id, depth)
    if not data["nodes"]:
        raise HTTPException(status_code=404, detail="Entity not found or isolated.")
    return data

@app.get("/api/v1/graph/path")
async def fetch_shortest_path(source: str, target: str):
    """Find key connecting path between target entities."""
    result = db_engine.get_shortest_path(source, target)
    if not result:
        raise HTTPException(status_code=404, detail="No path exists between specified entities.")
    return result

# Run via: uvicorn filename:app --reload
