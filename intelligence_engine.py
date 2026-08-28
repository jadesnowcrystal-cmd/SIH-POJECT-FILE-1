from dataclasses import dataclass, field
import numpy as np
import pandas as pd
import networkx as nx
from typing import Optional, List, Dict, Any, Iterable

def _safe_float(val, default=0.0):
    try: return float(val) if pd.notnull(val) else default
    except: return default

def _normalise_score(val): return float(np.clip(val, 0, 100))

@dataclass
class EngineConfig:
    alert_threshold: float = 60.0
    max_alerts: int = 50
    graph_high_risk_percentile: float = 85.0

@dataclass
class IntelligenceAlert:
    alert_id: str
    alert_type: str
    severity: str
    score: float
    confidence: float
    summary: str
    entities: List[str]
    evidence: Dict[str, Any]
    entity_graph: Dict[str, Any]
    recommended_review: str

    def to_dict(self): return self.__dict__

class PatternIntelligenceEngine:
    def __init__(self, config: Optional[EngineConfig] = None):
        self.config = config or EngineConfig()
        self.graph = nx.DiGraph()
        self.alerts: List[IntelligenceAlert] = []

    def _require_cols(self, df: pd.DataFrame, cols: List[str], name: str):
        missing = [c for c in cols if c not in df.columns]
        if missing: raise ValueError(f"Missing columns in {name}: {missing}")

    def build_entity_graph(self, communications=None, transactions=None, movements=None):
        self.graph.clear()
        edges = []
        if communications is not None and not communications.empty:
            self._require_cols(communications, ["entity_a", "entity_b", "timestamp"], "communications")
            for _, r in communications.iterrows():
                a, b = str(r["entity_a"]), str(r["entity_b"])
                edges.extend([(a, b, {"relation": "communication", "weight": 1.0, "timestamp": str(r["timestamp"])})])
                self.graph.add_nodes_from([(a, {"node_type": "entity"}), (b, {"node_type": "entity"})])

        if transactions is not None and not transactions.empty:
            self._require_cols(transactions, ["sender", "receiver", "amount", "timestamp"], "transactions")
            for _, r in transactions.iterrows():
                a, b, amt = str(r["sender"]), str(r["receiver"]), _safe_float(r["amount"])
                w = 1.0 + np.log1p(max(amt, 0)) / 10.0
                edges.append((a, b, {"relation": "transaction", "amount": amt, "weight": w, "timestamp": str(r["timestamp"])}))
                self.graph.add_nodes_from([(a, {"node_type": "entity"}), (b, {"node_type": "entity"})])

        if movements is not None and not movements.empty:
            self._require_cols(movements, ["entity_id", "location_id", "timestamp"], "movements")
            for _, r in movements.iterrows():
                e, loc = str(r["entity_id"]), f"location::{r['location_id']}"
                edges.append((e, loc, {"relation": "movement", "weight": 1.0, "timestamp": str(r["timestamp"])}))
                self.graph.add_node(e, node_type="entity")
                self.graph.add_node(loc, node_type="location")

        self.graph.add_edges_from(edges)
        return self.graph

    def graph_risk_scores(self) -> pd.DataFrame:
        if not self.graph.number_of_nodes(): return pd.DataFrame()
        G = self.graph.to_undirected()
        deg, bet = nx.degree_centrality(G), nx.betweenness_centrality(G, normalized=True)
        try: pr = nx.pagerank(G)
        except: pr = {n: 0.0 for n in G.nodes}

        rows = []
        for n in G.nodes:
            if self.graph.nodes[n].get("node_type") != "entity": continue
            d, b, p = deg.get(n, 0.0), bet.get(n, 0.0), pr.get(n, 0.0)
            raw = 40 * d + 45 * b + 15 * p
            rows.append({
                "entity_id": str(n), "degree_centrality": round(d, 6),
                "betweenness_centrality": round(b, 6), "pagerank": round(p, 6),
                "bridge_score": round(0.65 * b + 0.35 * d, 6),
                "graph_risk_score": round(_normalise_score(raw * 100), 2)
            })

        df = pd.DataFrame(rows)
        if df.empty: return df
        thresh = np.percentile(df["graph_risk_score"], self.config.graph_high_risk_percentile)
        df["high_risk_graph_node"] = df["graph_risk_score"] >= thresh
        return df.sort_values("graph_risk_score", ascending=False).reset_index(drop=True)

    def detect_suspect_clusters(self, min_cluster_size: int = 2) -> pd.DataFrame:
        if not self.graph.number_of_nodes(): return pd.DataFrame()
        G = self.graph.to_undirected()
        rows = []
        for idx, comm in enumerate(nx.community.greedy_modularity_communities(G), 1):
            members = sorted([str(n) for n in comm if self.graph.nodes[n].get("node_type") == "entity"])
            if len(members) >= min_cluster_size:
                rows.append({"cluster_id": f"C{idx:03d}", "entities": members, "size": len(members),
                             "density": round(nx.density(G.subgraph(comm)), 4)})
        return pd.DataFrame(rows).sort_values("size", ascending=False).reset_index(drop=True)

    def detect_contact_chains(self, df: Optional[pd.DataFrame]) -> pd.DataFrame: return pd.DataFrame()
    def detect_coordinated_sequences(self, df: Optional[pd.DataFrame]) -> pd.DataFrame: return pd.DataFrame()
    def detect_financial_anomalies(self, df: Optional[pd.DataFrame]) -> pd.DataFrame: return pd.DataFrame()
    def detect_communication_spikes(self, df: Optional[pd.DataFrame]) -> pd.DataFrame: return pd.DataFrame()
    def detect_location_loops(self, df: Optional[pd.DataFrame]) -> pd.DataFrame: return pd.DataFrame()
    def detect_movement_anomalies(self, df: Optional[pd.DataFrame]) -> pd.DataFrame: return pd.DataFrame()

    def _severity(self, s: float) -> str:
        return "critical" if s >= 85 else "high" if s >= 70 else "medium" if s >= 55 else "low"

    def _alert(self, atype, score, conf, summary, entities, evidence, graph=None, review="Review evidence."):
        return IntelligenceAlert(
            alert_id=f"ALT-{len(self.alerts) + 1:05d}", alert_type=atype, severity=self._severity(score),
            score=round(_normalise_score(score), 2), confidence=round(_normalise_score(conf), 2),
            summary=summary, entities=sorted(set(map(str, entities))), evidence=evidence,
            entity_graph=graph or {}, recommended_review=review
        )

    def generate_alerts(self, contact_chains=None, coordinated_sequences=None, financial_anomalies=None,
                        communication_spikes=None, location_loops=None, graph_scores=None, clusters=None) -> List[Dict[str, Any]]:
        gen = []
        if graph_scores is not None and not graph_scores.empty:
            for _, r in graph_scores[graph_scores.get("high_risk_graph_node", False) == True].head(self.config.max_alerts).iterrows():
                sc = _safe_float(r.get("graph_risk_score"))
                if sc >= self.config.alert_threshold:
                    e = str(r["entity_id"])
                    gen.append(self._alert("GRAPH_BRIDGE_ENTITY", sc, min(94, 55 + sc * 0.35),
                                           f"Entity {e} exhibits high bridge behavior.", [e], r.to_dict()))

        if clusters is not None and not clusters.empty:
            for _, r in clusters.iterrows():
                sz, d = int(r.get("size", 0)), _safe_float(r.get("density"))
                sc = _normalise_score(45 + min(sz, 10) * 4 + d * 40)
                if sc >= self.config.alert_threshold:
                    gen.append(self._alert("EMERGING_ENTITY_CLUSTER", sc, min(90, 50 + d * 40),
                                           f"Dense cluster {r.get('cluster_id')} detected.", r.get("entities", []), r.to_dict()))

        gen.sort(key=lambda a: (a.score, a.confidence), reverse=True)
        self.alerts.extend(gen[: self.config.max_alerts])
        return [a.to_dict() for a in self.alerts[-self.config.max_alerts:]]

    def extract_entity_features(self, communications=None, transactions=None, movements=None) -> pd.DataFrame:
        entities, frames = set(), []
        if communications is not None and not communications.empty:
            a, b = communications[["entity_a"]].rename(columns={"entity_a": "entity_id"}), communications[["entity_b"]].rename(columns={"entity_b": "entity_id"})
            entities.update(a["entity_id"].astype(str).tolist() + b["entity_id"].astype(str).tolist())
            frames.append(pd.concat([a, b]).groupby(pd.concat([a, b])["entity_id"].astype(str)).size().rename("communication_count"))

        if transactions is not None and not transactions.empty:
            tx = pd.concat([transactions[["sender", "amount"]].rename(columns={"sender": "entity_id"}),
                            transactions[["receiver", "amount"]].rename(columns={"receiver": "entity_id"})])
            tx["entity_id"] = tx["entity_id"].astype(str)
            entities.update(tx["entity_id"].tolist())
            frames.append(tx.groupby("entity_id").agg(transaction_count=("amount", "size"), transaction_total=("amount", "sum")))

        if movements is not None and not movements.empty:
            mov = movements.copy()
            mov["entity_id"] = mov["entity_id"].astype(str)
            entities.update(mov["entity_id"].tolist())
            frames.append(mov.groupby("entity_id").agg(movement_count=("location_id", "size"), unique_locations=("location_id", "nunique")))

        res = pd.DataFrame(index=sorted(entities))
        for f in frames: res = res.join(f, how="left")
        
        g_scores = self.graph_risk_scores()
        if not g_scores.empty:
            res = res.join(g_scores.set_index("entity_id")[["degree_centrality", "betweenness_centrality", "graph_risk_score"]], how="left")

        return res.fillna(0.0).reset_index().rename(columns={"index": "entity_id"})

    def run(self, communications=None, transactions=None, movements=None, events=None) -> Dict[str, Any]:
        self.build_entity_graph(communications, transactions, movements)
        g_scores = self.graph_risk_scores()
        clusters = self.detect_suspect_clusters()
        features = self.extract_entity_features(communications, transactions, movements)
        alerts = self.generate_alerts(graph_scores=g_scores, clusters=clusters)

        return {
            "alerts": alerts,
            "graph": {"risk_scores": g_scores.to_dict(orient="records"), "clusters": clusters.to_dict(orient="records")},
            "ml_features": features.to_dict(orient="records"),
            "meta": {"nodes": self.graph.number_of_nodes(), "edges": self.graph.number_of_edges(), "alert_count": len(alerts)}
        }

def run_intelligence_engine(communications=None, transactions=None, movements=None, events=None, config=None):
    return PatternIntelligenceEngine(config).run(communications, transactions, movements, events)

__all__ = ["EngineConfig", "IntelligenceAlert", "PatternIntelligenceEngine", "run_intelligence_engine"]
