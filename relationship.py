import os
import json
import logging
import datetime
from typing import Dict, List, Any, Optional, Tuple, Set

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks, Path
from pydantic import BaseModel, Field
from neo4j import GraphDatabase, Driver, Session
from neo4j.exceptions import ServiceUnavailable, AuthError, CypherSyntaxError
import networkx as nx

# Configure structured logging for production auditing
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger("RiaGraphDatabaseEngine")


# ==========================================
# 1. PHOENIX CONFIGURATION & DATA MODELS
# ==========================================

class Neo4jConfig:
    """Environment configuration for Neo4j cluster connections."""
    URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    USER: str = os.getenv("NEO4J_USER", "neo4j")
    PASSWORD: str = os.getenv("NEO4J_PASSWORD", "password")
    DATABASE: str = os.getenv("NEO4J_DATABASE", "neo4j")
    MAX_CONNECTION_LIFETIME: int = int(os.getenv("NEO4J_MAX_CONN_LIFETIME", "3600"))
    MAX_CONNECTION_POOL_SIZE: int = int(os.getenv("NEO4J_MAX_POOL_SIZE", "50"))


class EntityPayloadModel(BaseModel):
    id: str = Field(..., description="Unique entity ID (e.g., person_a1b2c3)")
    type: str = Field(..., description="Entity category: PERSON, PHONE, VEHICLE, MONEY, LOCATION, etc.")
    value: str = Field(..., description="Raw text value of the entity")
    normalized_value: Optional[str] = Field(None, description="Cleaned, standardized entity value")


class RelationPayloadModel(BaseModel):
    source: str = Field(..., description="Source entity ID")
    target: str = Field(..., description="Target entity ID")
    action: str = Field("ASSOCIATED_WITH", description="Detected action or relation type")
    context: Optional[str] = Field(None, description="Sentence context from narrative report")


class JanviNLPOutputModel(BaseModel):
    """
    Validation schema matching Janvi's NLP Engine output structure.
    """
    metadata: Dict[str, Any]
    network_analytics: Optional[Dict[str, Any]] = None
    rag_retrieved_evidence: Optional[List[Dict[str, Any]]] = None
    entities: List[EntityPayloadModel]
    relations: List[RelationPayloadModel]


# ==========================================
# 2. NEO4J PERSISTENCE ENGINE & ANALYTICS
# ==========================================

class Neo4jEngine:
    """
    High-performance graph persistence layer managing indexes, batch insertions, 
    pathfinding algorithms, and network metrics computation.
    """
    def __init__(self, config: Neo4jConfig = Neo4jConfig()):
        self.config = config
        self.driver: Optional[Driver] = None
        self._initialize_driver()
        self.verify_and_setup_schema()

    def _initialize_driver(self):
        """Initializes thread-safe Neo4j driver connection pool."""
        try:
            self.driver = GraphDatabase.driver(
                self.config.URI,
                auth=(self.config.USER, self.config.PASSWORD),
                max_connection_lifetime=self.config.MAX_CONNECTION_LIFETIME,
                max_connection_pool_size=self.config.MAX_CONNECTION_POOL_SIZE
            )
            self.driver.verify_connectivity()
            logger.info(f"Successfully connected to Neo4j database cluster at {self.config.URI}")
        except (ServiceUnavailable, AuthError) as e:
            logger.error(f"Failed to connect to Neo4j instance: {str(e)}")
            self.driver = None

    def close(self):
        """Gracefully closes Neo4j driver pool."""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j database connection pool closed.")

    def verify_and_setup_schema(self):
        """
        Guarantees that database constraints and indices exist for fast node lookups.
        Creates specialized constraints for all legal entity types.
        """
        if not self.driver:
            logger.warning("Database driver uninitialized. Skipping schema setup.")
            return

        constraints = [
            "CREATE CONSTRAINT c_entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE",
            "CREATE CONSTRAINT c_person_id IF NOT EXISTS FOR (p:PERSON) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT c_phone_id IF NOT EXISTS FOR (ph:PHONE) REQUIRE ph.id IS UNIQUE",
            "CREATE CONSTRAINT c_vehicle_id IF NOT EXISTS FOR (v:VEHICLE) REQUIRE v.id IS UNIQUE",
            "CREATE CONSTRAINT c_money_id IF NOT EXISTS FOR (m:MONEY) REQUIRE m.id IS UNIQUE",
            "CREATE CONSTRAINT c_location_id IF NOT EXISTS FOR (l:LOCATION) REQUIRE l.id IS UNIQUE",
            "CREATE CONSTRAINT c_case_id IF NOT EXISTS FOR (c:Case) REQUIRE c.case_id IS UNIQUE",
            
            # Performance Indexes
            "CREATE INDEX idx_entity_value IF NOT EXISTS FOR (e:Entity) ON (e.normalized_value)",
            "CREATE INDEX idx_person_name IF NOT EXISTS FOR (p:PERSON) ON (p.value)",
            "CREATE INDEX idx_phone_num IF NOT EXISTS FOR (ph:PHONE) ON (ph.normalized_value)"
        ]

        with self.driver.session(database=self.config.DATABASE) as session:
            for query in constraints:
                try:
                    session.run(query)
                except CypherSyntaxError as cse:
                    logger.warning(f"Cypher execution warning during schema setup: {cse}")
                except Exception as ex:
                    logger.error(f"Error executing schema query '{query}': {ex}")

        logger.info("Neo4j database schema constraints and indices verified successfully.")

    def ingest_janvi_nlp_payload(self, janvi_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Consumes the output produced by Janvi's NLP & Extraction pipeline, 
        writing nodes, relationships, and metadata directly to the graph.
        """
        if not self.driver:
            raise HTTPException(status_code=503, detail="Database connection unavailable.")

        metadata = janvi_output.get("metadata", {})
        case_id = metadata.get("case_id", f"UNKNOWN_CASE_{datetime.datetime.now().timestamp()}")
        entities = janvi_output.get("entities", [])
        relations = janvi_output.get("relations", [])

        # 1. Upsert Case Master Node
        cypher_case = """
        MERGE (c:Case {case_id: $case_id})
        SET c.processed_at = $processed_at,
            c.rag_indexed_chunks = $rag_chunks,
            c.total_entities = $total_entities,
            c.total_relations = $total_relations,
            c.last_updated = timestamp()
        RETURN c
        """

        # 2. Batch Upsert Entities using dynamic Cypher label processing
        cypher_entities = """
        UNWIND $entities AS ent
        MERGE (e:Entity {id: ent.id})
        SET e.value = ent.value,
            e.normalized_value = ent.normalized_value,
            e.type = ent.type,
            e.case_id = $case_id
        
        WITH e, ent
        CALL apoc.create.addLabels(e, [ent.type]) YIELD node
        RETURN count(node)
        """

        # Fallback Standard Cypher without APOC dependency
        cypher_entities_fallback = """
        UNWIND $entities AS ent
        MERGE (e:Entity {id: ent.id})
        SET e.value = ent.value,
            e.normalized_value = ent.normalized_value,
            e.type = ent.type,
            e.case_id = $case_id
        """

        # 3. Dynamic Relation Linker Query
        cypher_relations = """
        UNWIND $relations AS rel
        MATCH (src:Entity {id: rel.source})
        MATCH (tgt:Entity {id: rel.target})
        MERGE (src)-[r:INVESTIGATIVE_LINK {action: rel.action}]->(tgt)
        ON CREATE SET r.context = rel.context, r.weight = 1, r.first_seen = timestamp()
        ON MATCH SET r.weight = r.weight + 1, r.last_seen = timestamp()
        
        WITH src, tgt, rel
        MERGE (c:Case {case_id: $case_id})
        MERGE (src)-[:EVIDENCE_IN_CASE]->(c)
        MERGE (tgt)-[:EVIDENCE_IN_CASE]->(c)
        """

        with self.driver.session(database=self.config.DATABASE) as session:
            # Transaction execution
            session.run(cypher_case, 
                        case_id=case_id, 
                        processed_at=metadata.get("processed_at", datetime.datetime.now().isoformat()),
                        rag_chunks=metadata.get("rag_indexed_chunks", 0),
                        total_entities=len(entities),
                        total_relations=len(relations))

            try:
                session.run(cypher_entities, entities=entities, case_id=case_id)
            except Exception:
                # Fallback to standard execution if APOC procedure fails or isn't installed
                session.run(cypher_entities_fallback, entities=entities, case_id=case_id)

            session.run(cypher_relations, relations=relations, case_id=case_id)

        logger.info(f"Ingested Case {case_id} successfully into Neo4j: {len(entities)} Entities, {len(relations)} Relations.")
        return {
            "case_id": case_id,
            "status": "INGESTED",
            "nodes_written": len(entities),
            "edges_written": len(relations)
        }

    def get_subgraph(self, entity_id: str, depth: int = 2) -> Dict[str, Any]:
        """Traverse the graph topology from a starting entity up to N hops."""
        if not self.driver:
            raise HTTPException(status_code=503, detail="Database unavailable.")

        query = f"""
        MATCH (start:Entity {{id: $entity_id}})
        MATCH path = (start)-[*1..{depth}]-(connected:Entity)
        UNWIND nodes(path) AS n
        UNWIND relationships(path) AS r
        RETURN collect(DISTINCT {{
                    id: n.id, 
                    type: n.type, 
                    value: n.value,
                    normalized_value: n.normalized_value
               }}) AS nodes,
               collect(DISTINCT {{
                    source: startNode(r).id, 
                    target: endNode(r).id, 
                    action: coalesce(r.action, "ASSOCIATED_WITH"),
                    weight: coalesce(r.weight, 1)
               }}) AS relationships
        """

        with self.driver.session(database=self.config.DATABASE) as session:
            result = session.run(query, entity_id=entity_id).single()

            if not result or not result["nodes"]:
                # Try single node fetch if isolated
                single_query = "MATCH (e:Entity {id: $entity_id}) RETURN e.id AS id, e.type AS type, e.value AS value"
                res_single = session.run(single_query, entity_id=entity_id).single()
                if res_single:
                    return {
                        "nodes": [{"id": res_single["id"], "type": res_single["type"], "value": res_single["value"]}],
                        "relationships": []
                    }
                return {"nodes": [], "relationships": []}

            return {
                "nodes": result["nodes"],
                "relationships": result["relationships"]
            }

    def find_shortest_path(self, source_id: str, target_id: str, max_depth: int = 10) -> Optional[Dict[str, Any]]:
        """Calculates shortest investigative connection path between two targets."""
        if not self.driver:
            raise HTTPException(status_code=503, detail="Database unavailable.")

        query = f"""
        MATCH (start:Entity {{id: $source_id}}), (end:Entity {{id: $target_id}})
        MATCH path = shortestPath((start)-[*..{max_depth}]-(end))
        RETURN [node IN nodes(path) | {{
            id: node.id, 
            type: node.type, 
            value: node.value
        }}] AS path_nodes,
        [rel IN relationships(path) | {{
            source: startNode(rel).id,
            target: endNode(rel).id,
            action: coalesce(rel.action, "CONNECTED_TO")
        }}] AS path_edges,
        length(path) AS total_hops
        """

        with self.driver.session(database=self.config.DATABASE) as session:
            res = session.run(query, source_id=source_id, target_id=target_id).single()
            if res:
                return {
                    "total_hops": res["total_hops"],
                    "path_nodes": res["path_nodes"],
                    "path_edges": res["path_edges"]
                }
            return None

    def Calculate_network_centrality_in_memory(self, case_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Uses NetworkX to perform advanced graph topological analytics (Degree, Betweenness, Closeness Centrality)
        by downloading subgraph instances directly from Neo4j.
        """
        if not self.driver:
            raise HTTPException(status_code=503, detail="Database unavailable.")

        if case_id:
            cypher = """
            MATCH (e:Entity {case_id: $case_id})-[r:INVESTIGATIVE_LINK]->(target:Entity)
            RETURN e.id AS source, target.id AS target, coalesce(r.action, 'LINK') as action
            """
            params = {"case_id": case_id}
        else:
            cypher = """
            MATCH (e:Entity)-[r:INVESTIGATIVE_LINK]->(target:Entity)
            RETURN e.id AS source, target.id AS target, coalesce(r.action, 'LINK') as action
            LIMIT 5000
            """
            params = {}

        nx_graph = nx.Graph()

        with self.driver.session(database=self.config.DATABASE) as session:
            records = session.run(cypher, **params)
            for rec in records:
                nx_graph.add_edge(rec["source"], rec["target"], action=rec["action"])

        if nx_graph.number_of_nodes() == 0:
            return {
                "message": "Graph empty or specified case not found.",
                "total_nodes": 0,
                "total_edges": 0
            }

        # Calculate analytics using NetworkX
        deg_centrality = nx.degree_centrality(nx_graph)
        betweenness = nx.betweenness_centrality(nx_graph)
        
        # Sort and identify primary suspects/hubs
        sorted_hubs = sorted(deg_centrality.items(), key=lambda x: x[1], reverse=True)
        sorted_bridges = sorted(betweenness.items(), key=lambda x: x[1], reverse=True)

        return {
            "network_metrics": {
                "total_nodes": nx_graph.number_of_nodes(),
                "total_edges": nx_graph.number_of_edges(),
                "density": round(nx.density(nx_graph), 4),
                "is_connected": nx.is_connected(nx_graph) if nx_graph.number_of_nodes() > 0 else False
            },
            "top_central_hubs": [{"entity_id": k, "centrality": round(v, 4)} for k, v in sorted_hubs[:5]],
            "top_key_bridges": [{"entity_id": k, "betweenness": round(v, 4)} for k, v in sorted_bridges[:5]]
        }


# ==========================================
# 3. REST API SERVICE (FASTAPI MODULE)
# ==========================================

app = FastAPI(
    title="NEXUS Criminal Intelligence - Graph DB Engine (Ria's Module)",
    description="Graph database processing, dynamic entity linking, and network analytics layer.",
    version="2.1.0"
)

# Global engine instance
db_engine = Neo4jEngine()


@app.on_event("shutdown")
def shutdown_event():
    db_engine.close()


@app.get("/health")
async def health_check():
    """Service status and database connection health check."""
    status = "CONNECTED" if db_engine.driver else "DISCONNECTED"
    return {
        "status": "UP",
        "neo4j_status": status,
        "timestamp": datetime.datetime.now().isoformat()
    }


@app.post("/api/v1/graph/ingest/janvi-payload")
async def ingest_janvi_nlp_data(payload: JanviNLPOutputModel):
    """
    Direct ingestion endpoint for receiving Janvi's processed NLP payload.
    Maps extracted entities, relations, and narrative data directly into Neo4j.
    """
    try:
        raw_dict = payload.dict()
        result = db_engine.ingest_janvi_nlp_payload(raw_dict)
        return {
            "success": True,
            "message": f"Successfully ingested NLP payload for case {result['case_id']}",
            "data": result
        }
    except Exception as e:
        logger.error(f"Error during NLP payload ingestion: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@app.get("/api/v1/graph/subgraph/{entity_id}")
async def fetch_subgraph(
    entity_id: str = Path(..., description="The entity unique identifier (e.g., person_a1b2c3)"),
    depth: int = Query(2, ge=1, le=5, description="Search depth limit (hops)")
):
    """Fetches full graph topology surrounding a target entity for frontend visualizers."""
    data = db_engine.get_subgraph(entity_id=entity_id, depth=depth)
    if not data["nodes"]:
        raise HTTPException(status_code=404, detail=f"Entity '{entity_id}' not found in the graph.")
    return {
        "success": True,
        "entity_id": entity_id,
        "depth": depth,
        "graph_topology": data
    }


@app.get("/api/v1/graph/shortest-path")
async def fetch_shortest_path(
    source_id: str = Query(..., description="Starting node identifier"),
    target_id: str = Query(..., description="Destination node identifier"),
    max_depth: int = Query(8, ge=1, le=15, description="Maximum path length limit")
):
    """Calculates the shortest investigative link between two nodes."""
    path = db_engine.find_shortest_path(source_id=source_id, target_id=target_id, max_depth=max_depth)
    if not path:
        raise HTTPException(
            status_code=404, 
            detail=f"No connecting investigative path found between '{source_id}' and '{target_id}' within {max_depth} hops."
        )
    return {
        "success": True,
        "source": source_id,
        "target": target_id,
        "path": path
    }


@app.get("/api/v1/graph/analytics/centrality")
async def compute_graph_analytics(
    case_id: Optional[str] = Query(None, description="Optional Case ID to constrain analytics scope")
):
    """
    Calculates Network Centrality metrics across the persistent Neo4j graph using NetworkX algorithms.
    Identifies high-priority criminal targets and communication bridges.
    """
    try:
        analytics = db_engine.Calculate_network_centrality_in_memory(case_id=case_id)
        return {
            "success": True,
            "case_id_filter": case_id,
            "analytics": analytics
        }
    except Exception as e:
        logger.error(f"Failed to calculate graph network analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# 4. DIRECT INTEGRATION SIMULATION TEST
# ==========================================

if __name__ == "__main__":
    """
    Local Integration Runner:
    Simulates Janvi's Module sending an output payload to Ria's Graph engine.
    """
    import uvicorn

    print("=========================================================================")
    print("RUNNING RIA'S GRAPH DATABASE MODULE (INTEGRATION TEST MODE)")
    print("=========================================================================")

    # Simulated output matching Janvi's Module output
    sample_janvi_output = {
        "metadata": {
            "case_id": "FIR-2026-0001",
            "processed_at": datetime.datetime.now().isoformat(),
            "rag_indexed_chunks": 4,
            "total_entities_found": 4,
            "total_relations_found": 3,
            "status": "SUCCESS"
        },
        "network_analytics": {
            "node_count": 4,
            "edge_count": 3
        },
        "entities": [
            {"id": "PER-1001", "type": "PERSON", "value": "Rahul Sharma", "normalized_value": "Rahul Sharma"},
            {"id": "PER-1002", "type": "PERSON", "value": "Amit Patel", "normalized_value": "Amit Patel"},
            {"id": "PER-1004", "type": "PERSON", "value": "Mogambo Singh", "normalized_value": "Mogambo Singh"},
            {"id": "phone_e1a2b3", "type": "PHONE", "value": "(999) 888-7777", "normalized_value": "+919998887777"}
        ],
        "relations": [
            {"source": "PER-1001", "target": "PER-1002", "action": "COMMUNICATION", "context": "Rahul called Amit"},
            {"source": "PER-1004", "target": "PER-1002", "action": "MEETING", "context": "Mogambo met Amit at Airoli"},
            {"source": "PER-1004", "target": "phone_e1a2b3", "action": "ASSOCIATED_WITH", "context": "Mogambo uses phone"}
        ]
    }

    try:
        logger.info("Directly executing database ingestion test...")
        ingest_summary = db_engine.ingest_janvi_nlp_payload(sample_janvi_output)
        print("\nIngestion Summary Output:")
        print(json.dumps(ingest_summary, indent=2))

        logger.info("Executing network path calculation test...")
        path_summary = db_engine.find_shortest_path(source_id="PER-1001", target_id="phone_e1a2b3")
        print("\nShortest Path Output:")
        print(json.dumps(path_summary, indent=2))

    except Exception as test_err:
        logger.warning(f"Local test execution completed with warnings (Neo4j server might be offline): {test_err}")

    print("\nStarting Uvicorn REST API Server on http://0.0.0.0:8000 ...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
