"""
Module 3: Network Analytics Engine
Single-File Implementation

Objectives:
1. Ingest structured entity and triplet graph JSON payloads.
2. Calculate node centrality (Degree, Betweenness, Closeness, PageRank).
3. Detect critical bridges and inter-cell liaison links.
4. Partition network into distinct sub-gang communities using Greedy Modularity.
5. Export interactive PyVis visual graphs and structured hand-off JSON payloads.
"""

import os
import json
import pandas as pd
import networkx as nx
from pyvis.network import Network
from datetime import datetime
from typing import List, Dict, Any, Tuple

# =====================================================================
# 1. CONFIGURATION & CONSTANTS
# =====================================================================
HIGH_RISK_PERCENTILE = 0.85
MEDIUM_RISK_PERCENTILE = 0.50

# Visual Styling Rules for PyVis Graphs
TYPE_COLOR_MAP = {
    "PERSON": "#E74C3C",        # Red
    "PHONE": "#3498DB",         # Blue
    "VEHICLE": "#F1C40F",       # Yellow
    "LOCATION": "#2ECC71",      # Green
    "ORGANIZATION": "#9B59B6",  # Purple
    "MONEY": "#E67E22"          # Orange
}

DEFAULT_NODE_COLOR = "#95A5A6"
BRIDGE_EDGE_COLOR = "#FF0000"
DEFAULT_EDGE_COLOR = "#BDC3C7"


# =====================================================================
# 2. SCHEMA BUILDERS
# =====================================================================
def build_node_metrics(
    node_id: str, 
    node_type: str, 
    degree: int, 
    betweenness: float, 
    closeness: float, 
    pagerank: float, 
    risk_score: str, 
    community_id: int
) -> Dict[str, Any]:
    """Formats calculated node metrics into clean dictionaries for UI hand-off."""
    return {
        "id": node_id,
        "type": node_type,
        "metrics": {
            "degree": degree,
            "betweenness": round(betweenness, 4),
            "closeness": round(closeness, 4),
            "pagerank": round(pagerank, 4)
        },
        "risk_score": risk_score,
        "community_id": community_id
    }


def build_bridge_payload(source: str, target: str, bridge_type: str = "Inter-Cell Liaison") -> Dict[str, Any]:
    """Formats bridge connection records."""
    return {
        "source": source,
        "target": target,
        "type": bridge_type
    }


# =====================================================================
# 3. GRAPH BUILDER MODULE
# =====================================================================
class GraphBuilder:
    """Ingests extraction module JSON outputs and constructs NetworkX graph objects."""
    
    @staticmethod
    def build_graph(extraction_data: Dict[str, Any]) -> nx.Graph:
        """Converts entity arrays and relation triplets into an undirected NetworkX Graph."""
        G = nx.Graph()

        # Add Nodes with attributes
        entities = extraction_data.get("entities", [])
        for ent in entities:
            G.add_node(
                ent["id"],
                type=ent.get("type", "UNKNOWN"),
                label=ent.get("value", ent["id"]),
                normalized=ent.get("normalized_value", ent.get("value", ""))
            )

        # Add Edges with relation context
        relations = extraction_data.get("relations", [])
        for rel in relations:
            src = rel["source"]
            tgt = rel["target"]
            
            # Ensure both endpoints exist in the graph
            if not G.has_node(src):
                G.add_node(src, type="UNKNOWN", label=src)
            if not G.has_node(tgt):
                G.add_node(tgt, type="UNKNOWN", label=tgt)

            # Weight increments for repeated connections
            if G.has_edge(src, tgt):
                G[src][tgt]["weight"] += 1
                G[src][tgt]["actions"].append(rel.get("action", "ASSOCIATED"))
            else:
                G.add_edge(
                    src, 
                    tgt, 
                    weight=1, 
                    action=rel.get("action", "ASSOCIATED"),
                    actions=[rel.get("action", "ASSOCIATED")],
                    context=rel.get("context", "")
                )

        return G


# =====================================================================
# 4. CENTRALITY & RISK ANALYZER MODULE
# =====================================================================
class CentralityAnalyzer:
    """Calculates node importance across multiple centrality metrics and evaluates risk levels."""
    
    def __init__(self, graph: nx.Graph):
        self.G = graph

    def compute_all_metrics(self) -> pd.DataFrame:
        """Calculates Degree, Betweenness, Closeness, and PageRank."""
        if len(self.G) == 0:
            return pd.DataFrame()

        degrees = dict(self.G.degree())
        betweenness = nx.betweenness_centrality(self.G)
        closeness = nx.closeness_centrality(self.G)
        
        try:
            pagerank = nx.pagerank(self.G, alpha=0.85)
        except Exception:
            pagerank = {node: 0.0 for node in self.G.nodes()}

        node_types = nx.get_node_attributes(self.G, "type")

        data = []
        for node in self.G.nodes():
            data.append({
                "id": node,
                "type": node_types.get(node, "UNKNOWN"),
                "degree": degrees.get(node, 0),
                "betweenness": betweenness.get(node, 0.0),
                "closeness": closeness.get(node, 0.0),
                "pagerank": pagerank.get(node, 0.0)
            })

        df = pd.DataFrame(data)
        
        # Calculate composite importance score
        max_degree = max(df["degree"].max(), 1)
        df["composite_score"] = (
            (df["degree"] / max_degree) * 0.3 +
            df["betweenness"] * 0.4 +
            df["pagerank"] * 0.3
        )
        return df

    def assign_risk_scores(self, df: pd.DataFrame) -> pd.DataFrame:
        """Categorizes entities into High, Medium, or Low risk tiers based on composite scores."""
        if df.empty:
            return df

        high_cutoff = df["composite_score"].quantile(HIGH_RISK_PERCENTILE)
        med_cutoff = df["composite_score"].quantile(MEDIUM_RISK_PERCENTILE)

        def determine_tier(score):
            if score >= high_cutoff and score > 0:
                return "High"
            elif score >= med_cutoff and score > 0:
                return "Medium"
            return "Low"

        df["risk_score"] = df["composite_score"].apply(determine_tier)
        return df.sort_values(by="composite_score", ascending=False)


# =====================================================================
# 5. BRIDGE & BOTTLENECK DETECTOR MODULE
# =====================================================================
class BridgeDetector:
    """Detects critical structural bridges and bottleneck nodes between network sub-clusters."""
    
    def __init__(self, graph: nx.Graph):
        self.G = graph

    def find_critical_bridges(self) -> List[Dict[str, Any]]:
        """Finds bridge edges whose removal would disconnect network components."""
        if len(self.G) == 0:
            return []

        if not nx.is_connected(self.G):
            bridges = []
            for comp in nx.connected_components(self.G):
                subgraph = self.G.subgraph(comp)
                bridges.extend(list(nx.bridges(subgraph)))
        else:
            bridges = list(nx.bridges(self.G))

        bridge_payloads = []
        for u, v in bridges:
            bridge_payloads.append(build_bridge_payload(
                source=u,
                target=v,
                bridge_type="Inter-Cell Liaison"
            ))

        return bridge_payloads

    def find_articulation_points(self) -> List[str]:
        """Identifies key bottleneck nodes (cut vertices)."""
        if len(self.G) == 0:
            return []
        return list(nx.articulation_points(self.G))


# =====================================================================
# 6. COMMUNITY & CELL CLUSTER DETECTOR MODULE
# =====================================================================
class CommunityDetector:
    """Partitions network graph into dense sub-gangs/cells using Greedy Modularity Optimization."""
    
    def __init__(self, graph: nx.Graph):
        self.G = graph

    def detect_communities(self) -> Tuple[Dict[str, int], List[Dict[str, Any]]]:
        """Runs Greedy Modularity algorithm to map nodes to community clusters."""
        if len(self.G) == 0:
            return {}, []

        try:
            communities_generator = nx.community.greedy_modularity_communities(self.G)
            raw_communities = [list(c) for c in communities_generator]
        except Exception:
            raw_communities = [list(self.G.nodes())]

        node_community_map = {}
        formatted_communities = []

        for comm_id, members in enumerate(raw_communities):
            for member in members:
                node_community_map[member] = comm_id

            formatted_communities.append({
                "community_id": comm_id,
                "member_count": len(members),
                "members": members
            })

        return node_community_map, formatted_communities


# =====================================================================
# 7. PYVIS GRAPH VISUALIZER MODULE
# =====================================================================
class GraphVisualizer:
    """Generates interactive PyVis HTML visual network visualizations."""
    
    def __init__(self, graph: nx.Graph):
        self.G = graph

    def export_interactive_html(
        self, 
        bridges: List[Dict[str, Any]], 
        community_map: Dict[str, int], 
        output_filepath: str = "network_map.html"
    ) -> str:
        """Renders the graph to an interactive HTML canvas file using PyVis."""
        if len(self.G) == 0:
            return ""

        net = Network(height="750px", width="100%", bgcolor="#222222", font_color="white")
        net.barcode = False

        # Identify bridge pairs for fast lookup styling
        bridge_pairs = set((b["source"], b["target"]) for b in bridges) | \
                       set((b["target"], b["source"]) for b in bridges)

        # Add Nodes with Type-based colors
        for node, attrs in self.G.nodes(data=True):
            n_type = attrs.get("type", "UNKNOWN")
            color = TYPE_COLOR_MAP.get(n_type, DEFAULT_NODE_COLOR)
            label = attrs.get("label", node)
            comm_id = community_map.get(node, 0)

            title = f"ID: {node}<br>Type: {n_type}<br>Community: Cell-{comm_id}"
            
            net.add_node(
                node, 
                label=f"{label} ({n_type})", 
                color=color, 
                title=title,
                size=20
            )

        # Add Edges with Bridge Highlighting
        for u, v, attrs in self.G.edges(data=True):
            is_bridge = (u, v) in bridge_pairs
            edge_color = BRIDGE_EDGE_COLOR if is_bridge else DEFAULT_EDGE_COLOR
            width = 3 if is_bridge else 1
            action = attrs.get("action", "LINKED")

            net.add_edge(
                u, 
                v, 
                title=f"Action: {action}", 
                color=edge_color, 
                width=width
            )

        # Generate layout settings
        net.force_atlas_2based()
        
        output_dir = os.path.dirname(output_filepath)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            
        net.save_graph(output_filepath)
        return output_filepath


# =====================================================================
# 8. NETWORK ANALYTICS ENGINE (MAIN ORCHESTRATOR)
# =====================================================================
class NetworkAnalyticsEngine:
    """Orchestrator class tying all execution components together."""
    
    def __init__(self):
        self.builder = GraphBuilder()

    def analyze(self, extraction_payload: Dict[str, Any], output_html_path: str = "output/network.html") -> Dict[str, Any]:
        """Executes full graph processing pipeline on input entity data."""
        # Step 1: Construct Graph Instance
        G = self.builder.build_graph(extraction_payload)

        if len(G) == 0:
            return {
                "summary": {"total_nodes": 0, "total_edges": 0, "density": 0.0},
                "top_suspects": [],
                "critical_bridges": [],
                "communities": [],
                "visualization_path": ""
            }

        # Step 2: Centrality Analysis & Risk Scoring
        centrality_engine = CentralityAnalyzer(G)
        metrics_df = centrality_engine.compute_all_metrics()
        scored_df = centrality_engine.assign_risk_scores(metrics_df)

        # Step 3: Bridge & Bottleneck Detection
        bridge_engine = BridgeDetector(G)
        critical_bridges = bridge_engine.find_critical_bridges()

        # Step 4: Community & Cell Clustering
        community_engine = CommunityDetector(G)
        community_map, communities = community_engine.detect_communities()

        # Step 5: Format Top Suspects Payload
        top_suspects = []
        for _, row in scored_df.iterrows():
            top_suspects.append(build_node_metrics(
                node_id=row["id"],
                node_type=row["type"],
                degree=int(row["degree"]),
                betweenness=row["betweenness"],
                closeness=row["closeness"],
                pagerank=row["pagerank"],
                risk_score=row["risk_score"],
                community_id=community_map.get(row["id"], -1)
            ))

        # Step 6: Render Interactive PyVis Graph
        visualizer = GraphVisualizer(G)
        html_path = visualizer.export_interactive_html(
            bridges=critical_bridges,
            community_map=community_map,
            output_filepath=output_html_path
        )

        # Step 7: Summary Metadata
        summary = {
            "case_id": extraction_payload.get("metadata", {}).get("case_id", "UNKNOWN_CASE"),
            "processed_at": datetime.now().isoformat(),
            "total_nodes": G.number_of_nodes(),
            "total_edges": G.number_of_edges(),
            "density": round(nx.density(G), 4),
            "total_communities": len(communities),
            "critical_bridge_count": len(critical_bridges)
        }

        return {
            "summary": summary,
            "top_suspects": top_suspects,
            "critical_bridges": critical_bridges,
            "communities": communities,
            "visualization_path": html_path
        }


# =====================================================================
# 9. STANDALONE EXECUTION & TEST DRIVE
# =====================================================================
if __name__ == "__main__":
    # Mock input payload matching Module 1 / Module 2 extraction specifications
    sample_extraction_payload = {
        "metadata": {"case_id": "CASE-2026-MUMBAI-89"},
        "entities": [
            {"id": "person_01", "type": "PERSON", "value": "Rahul Sharma"},
            {"id": "person_02", "type": "PERSON", "value": "Sameer Verma"},
            {"id": "person_03", "type": "PERSON", "value": "Amit Patel"},
            {"id": "person_04", "type": "PERSON", "value": "Vijay Shah"},
            {"id": "phone_01", "type": "PHONE", "value": "+919876543210"},
            {"id": "vehicle_01", "type": "VEHICLE", "value": "MH04AB1234"},
            {"id": "location_01", "type": "LOCATION", "value": "Vashi Station"}
        ],
        "relations": [
            {"source": "person_01", "target": "person_02", "action": "MEETING", "context": "Rahul met Sameer"},
            {"source": "person_01", "target": "phone_01", "action": "USED", "context": "Rahul called using phone"},
            {"source": "person_02", "target": "phone_01", "action": "RECEIVED", "context": "Sameer received call"},
            {"source": "person_02", "target": "person_03", "action": "TRANSFER", "context": "Sameer transferred money to Amit"},
            {"source": "person_03", "target": "person_04", "action": "MEETING", "context": "Amit met Vijay"},
            {"source": "person_02", "target": "vehicle_01", "action": "DROVE", "context": "Sameer used vehicle"}
        ]
    }

    print("==================================================================")
    print("                MODULE 3: NETWORK ANALYTICS ENGINE                ")
    print("==================================================================")

    # Initialize Engine and process graph
    engine = NetworkAnalyticsEngine()
    result = engine.analyze(sample_extraction_payload, output_html_path="output/network_map.html")

    # Display Engine Summary Output
    print("\n[1] ENGINE SUMMARY:")
    print(json.dumps(result["summary"], indent=2))

    print("\n[2] TOP SUSPECTS RANKING (CENTRALITY & RISK):")
    print(json.dumps(result["top_suspects"][:3], indent=2))

    print("\n[3] CRITICAL BRIDGES & BOTTLENECKS:")
    print(json.dumps(result["critical_bridges"], indent=2))

    print("\n[4] COMMUNITIES / SUB-CELLS DETECTED:")
    print(json.dumps(result["communities"], indent=2))

    print(f"\n[5] VISUALIZATION MAP GENERATED: {result['visualization_path']}")
    print("==================================================================")
