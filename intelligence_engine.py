"""
Pattern Detection & Intelligence Engine
=======================================

Single-file analytics module designed to plug into a criminal-network
intelligence dashboard or a larger investigation backend.

Dependencies:
    pandas
    numpy
    networkx
    scikit-learn

Optional:
    pyod

Expected input tables are pandas DataFrames. The engine is intentionally
UI/database agnostic so that other GitHub modules can call these classes
directly.

IMPORTANT:
    Scores produced here are analytical prioritization signals, NOT findings
    of guilt or proof of criminal activity. Human investigators should review
    the underlying evidence before acting on an alert.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from collections import Counter, defaultdict

import numpy as np
import pandas as pd
import networkx as nx

from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


# ---------------------------------------------------------------------------
# Configuration / result objects
# ---------------------------------------------------------------------------

@dataclass
class EngineConfig:
    """Central configuration so another module can construct the engine once."""

    time_window_minutes: int = 60
    communication_spike_z: float = 2.5
    financial_anomaly_contamination: float = 0.05
    location_loop_min_visits: int = 3
    graph_high_risk_percentile: float = 90.0
    alert_threshold: float = 55.0
    max_alerts: int = 100


@dataclass
class IntelligenceAlert:
    """Stable alert contract for dashboards, APIs and databases."""

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

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        x = float(value)
        return default if not np.isfinite(x) else x
    except (TypeError, ValueError):
        return default


def _normalise_score(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return float(np.clip(value, low, high))


def _zscore(series: pd.Series) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce").fillna(0.0)
    std = s.std(ddof=0)
    if std == 0 or not np.isfinite(std):
        return pd.Series(0.0, index=s.index)
    return (s - s.mean()) / std


def _parse_time(df: pd.DataFrame, column: str = "timestamp") -> pd.Series:
    if column not in df.columns:
        raise ValueError(f"Required column '{column}' is missing.")
    return pd.to_datetime(df[column], errors="coerce")


def _require_columns(df: pd.DataFrame, columns: Sequence[str], name: str) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ValueError(f"{name} is missing required columns: {missing}")


def _json_safe(value: Any) -> Any:
    """Convert numpy/pandas objects into JSON-safe Python values."""
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    if pd.isna(value) if not isinstance(value, (dict, list, tuple)) else False:
        return None
    return value


# ---------------------------------------------------------------------------
# Core engine
# ---------------------------------------------------------------------------

class PatternIntelligenceEngine:
    """
    Main orchestration class.

    Data contracts
    --------------
    communications:
        entity_a, entity_b, timestamp, [case_id], [communication_type]

    transactions:
        sender, receiver, amount, timestamp, [case_id], [transaction_type]

    movements:
        entity_id, location_id, timestamp, [case_id]

    incidents:
        incident_id, timestamp, location_id, [case_id]

    The engine accepts extra columns and ignores them unless a detector uses
    them. This makes the module easy to integrate with an existing backend.
    """

    def __init__(self, config: Optional[EngineConfig] = None):
        self.config = config or EngineConfig()
        self.graph = nx.MultiDiGraph()
        self.alerts: List[IntelligenceAlert] = []

    # -----------------------------------------------------------------------
    # 1. Pattern & anomaly detection
    # -----------------------------------------------------------------------

    def detect_contact_chains(
        self,
        communications: pd.DataFrame,
        max_hops: int = 2,
        common_case_only: bool = True,
    ) -> pd.DataFrame:
        """
        Detect A -> B -> C style contact chains.

        Returns one row per discovered chain with timing and case overlap.
        """
        _require_columns(
            communications,
            ["entity_a", "entity_b", "timestamp"],
            "communications",
        )

        df = communications.copy()
        df["timestamp"] = _parse_time(df)
        df = df.dropna(subset=["entity_a", "entity_b", "timestamp"])
        df = df.sort_values("timestamp")

        graph = nx.DiGraph()
        for _, row in df.iterrows():
            a, b = str(row["entity_a"]), str(row["entity_b"])
            graph.add_edge(a, b)

        records: List[Dict[str, Any]] = []

        for source in graph.nodes:
            paths = nx.single_source_shortest_path(
                graph, source, cutoff=max_hops
            )

            for target, path in paths.items():
                if len(path) != max_hops + 1:
                    continue

                # Match observed events for consecutive edges.
                edge_events = []
                valid = True

                for a, b in zip(path[:-1], path[1:]):
                    events = df[
                        (df["entity_a"].astype(str) == a)
                        & (df["entity_b"].astype(str) == b)
                    ].copy()

                    if events.empty:
                        valid = False
                        break

                    edge_events.append(events)

                if not valid:
                    continue

                start_time = max(e["timestamp"].min() for e in edge_events)
                end_time = min(e["timestamp"].max() for e in edge_events)

                # More useful temporal matching: try to build a forward chain.
                selected = []
                current_time = None

                for events in edge_events:
                    candidates = events
                    if current_time is not None:
                        candidates = candidates[
                            candidates["timestamp"] >= current_time
                        ]
                    if candidates.empty:
                        valid = False
                        break
                    event = candidates.iloc[0]
                    selected.append(event)
                    current_time = event["timestamp"]

                if not valid or len(selected) != len(path) - 1:
                    continue

                start = selected[0]["timestamp"]
                end = selected[-1]["timestamp"]
                duration = (end - start).total_seconds() / 60.0

                if duration > self.config.time_window_minutes:
                    continue

                cases = set()
                if "case_id" in df.columns:
                    for event in selected:
                        if pd.notna(event.get("case_id")):
                            cases.add(str(event["case_id"]))

                if common_case_only and "case_id" in df.columns and not cases:
                    continue

                records.append(
                    {
                        "chain": " -> ".join(path),
                        "entities": path,
                        "hops": max_hops,
                        "start_time": start,
                        "end_time": end,
                        "duration_minutes": round(duration, 2),
                        "case_ids": sorted(cases),
                        "chain_strength": _normalise_score(
                            100 * (1 - duration / max(self.config.time_window_minutes, 1))
                        ),
                    }
                )

        result = pd.DataFrame(records)
        if result.empty:
            return pd.DataFrame(
                columns=[
                    "chain", "entities", "hops", "start_time", "end_time",
                    "duration_minutes", "case_ids", "chain_strength"
                ]
            )

        return result.drop_duplicates(subset=["chain", "start_time"]).reset_index(drop=True)

    def detect_coordinated_sequences(
        self,
        events: pd.DataFrame,
        sequence: Sequence[str] = (
            "communication",
            "communication",
            "transaction",
            "incident",
        ),
    ) -> pd.DataFrame:
        """
        Detect ordered event-type sequences inside a narrow time window.

        Required columns:
            entity_id, event_type, timestamp

        Optional:
            case_id, location_id, related_entity
        """
        _require_columns(events, ["entity_id", "event_type", "timestamp"], "events")

        df = events.copy()
        df["timestamp"] = _parse_time(df)
        df["event_type"] = df["event_type"].astype(str).str.lower()
        df["entity_id"] = df["entity_id"].astype(str)
        df = df.dropna(subset=["timestamp"]).sort_values("timestamp")

        records = []
        window = pd.Timedelta(minutes=self.config.time_window_minutes)

        for entity, group in df.groupby("entity_id"):
            group = group.sort_values("timestamp").reset_index(drop=True)

            for i in range(len(group)):
                if group.loc[i, "event_type"] != sequence[0]:
                    continue

                selected = [group.loc[i]]
                cursor_time = group.loc[i, "timestamp"]
                seq_index = 1

                for j in range(i + 1, len(group)):
                    if group.loc[j, "timestamp"] - cursor_time > window:
                        break

                    if group.loc[j, "event_type"] == sequence[seq_index]:
                        selected.append(group.loc[j])
                        cursor_time = group.loc[j, "timestamp"]
                        seq_index += 1
                        if seq_index == len(sequence):
                            break

                if len(selected) == len(sequence):
                    start = selected[0]["timestamp"]
                    end = selected[-1]["timestamp"]
                    duration = (end - start).total_seconds() / 60.0

                    records.append(
                        {
                            "entity_id": entity,
                            "sequence": " -> ".join(sequence),
                            "start_time": start,
                            "end_time": end,
                            "duration_minutes": round(duration, 2),
                            "event_count": len(selected),
                            "sequence_strength": _normalise_score(
                                100 * (1 - duration / max(self.config.time_window_minutes, 1))
                            ),
                        }
                    )

        return pd.DataFrame(records).drop_duplicates(
            subset=["entity_id", "start_time", "sequence"]
        )

    def detect_location_loops(
        self,
        movements: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Detect repeated A -> B -> A / A -> B -> C -> A style movements.

        Required:
            entity_id, location_id, timestamp
        """
        _require_columns(
            movements,
            ["entity_id", "location_id", "timestamp"],
            "movements",
        )

        df = movements.copy()
        df["timestamp"] = _parse_time(df)
        df["entity_id"] = df["entity_id"].astype(str)
        df["location_id"] = df["location_id"].astype(str)
        df = df.dropna(subset=["timestamp"]).sort_values("timestamp")

        records = []

        for entity, group in df.groupby("entity_id"):
            locs = group["location_id"].tolist()
            times = group["timestamp"].tolist()

            if len(locs) < 3:
                continue

            for i in range(len(locs) - 2):
                for j in range(i + 2, min(i + 8, len(locs))):
                    segment = locs[i:j + 1]
                    if segment[0] == segment[-1] and len(set(segment)) >= 2:
                        duration = (times[j] - times[i]).total_seconds() / 60.0
                        records.append(
                            {
                                "entity_id": entity,
                                "loop": " -> ".join(segment),
                                "start_time": times[i],
                                "end_time": times[j],
                                "duration_minutes": round(duration, 2),
                                "unique_locations": len(set(segment)),
                                "loop_strength": _normalise_score(
                                    50 + 10 * len(set(segment))
                                ),
                            }
                        )

        result = pd.DataFrame(records)
        if result.empty:
            return result

        return result.drop_duplicates(
            subset=["entity_id", "loop", "start_time"]
        ).reset_index(drop=True)

    def detect_financial_anomalies(
        self,
        transactions: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Use Isolation Forest + robust z-scores to flag unusual transaction
        amounts and burst activity.

        Required:
            sender, receiver, amount, timestamp
        """
        _require_columns(
            transactions,
            ["sender", "receiver", "amount", "timestamp"],
            "transactions",
        )

        df = transactions.copy()
        df["timestamp"] = _parse_time(df)
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
        df = df.dropna(subset=["timestamp", "amount"])
        df["sender"] = df["sender"].astype(str)
        df["receiver"] = df["receiver"].astype(str)

        if len(df) < 5:
            df["anomaly_score"] = 0.0
            df["is_anomaly"] = False
            return df

        # Transaction-level features.
        df["log_amount"] = np.log1p(np.maximum(df["amount"], 0))
        df["hour"] = df["timestamp"].dt.hour
        df["weekday"] = df["timestamp"].dt.weekday

        hourly = (
            df.set_index("timestamp")
            .groupby("sender")
            .resample("1h")
            .size()
            .rename("hourly_count")
            .reset_index()
        )

        df["hourly_count"] = 1
        for sender, g in hourly.groupby("sender"):
            mask = df["sender"] == sender
            # Approximate local burst feature using sender-level event density.
            df.loc[mask, "hourly_count"] = max(1, int(g["hourly_count"].max()))

        features = df[["log_amount", "hour", "weekday", "hourly_count"]].fillna(0)
        scaler = StandardScaler()
        X = scaler.fit_transform(features)

        model = IsolationForest(
            n_estimators=200,
            contamination=min(max(self.config.financial_anomaly_contamination, 0.001), 0.5),
            random_state=42,
        )
        model.fit(X)

        raw = -model.decision_function(X)
        raw_min, raw_max = raw.min(), raw.max()
        if raw_max > raw_min:
            anomaly_score = 100 * (raw - raw_min) / (raw_max - raw_min)
        else:
            anomaly_score = np.zeros(len(df))

        df["amount_zscore"] = _zscore(df["amount"]).round(3)
        df["anomaly_score"] = np.round(anomaly_score, 2)
        df["is_anomaly"] = df["anomaly_score"] >= 70.0

        return df.sort_values("anomaly_score", ascending=False).reset_index(drop=True)

    def detect_communication_spikes(
        self,
        communications: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Detect entities whose communication volume is unusually high relative
        to the population baseline.
        """
        _require_columns(
            communications,
            ["entity_a", "entity_b", "timestamp"],
            "communications",
        )

        df = communications.copy()
        df["timestamp"] = _parse_time(df)
        df = df.dropna(subset=["timestamp"])

        a = df[["entity_a", "timestamp"]].rename(columns={"entity_a": "entity"})
        b = df[["entity_b", "timestamp"]].rename(columns={"entity_b": "entity"})
        long = pd.concat([a, b], ignore_index=True)
        long["entity"] = long["entity"].astype(str)
        long["date"] = long["timestamp"].dt.date

        counts = long.groupby(["entity", "date"]).size().reset_index(name="count")
        counts["zscore"] = counts.groupby("entity")["count"].transform(_zscore)
        counts["is_spike"] = counts["zscore"] >= self.config.communication_spike_z

        return counts.sort_values("zscore", ascending=False).reset_index(drop=True)

    def detect_movement_anomalies(
        self,
        movements: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Detect out-of-baseline movement volume for each entity/day.
        """
        _require_columns(
            movements,
            ["entity_id", "location_id", "timestamp"],
            "movements",
        )

        df = movements.copy()
        df["timestamp"] = _parse_time(df)
        df = df.dropna(subset=["timestamp"])
        df["entity_id"] = df["entity_id"].astype(str)
        df["date"] = df["timestamp"].dt.date

        daily = (
            df.groupby(["entity_id", "date"])
            .agg(
                ping_count=("location_id", "size"),
                unique_locations=("location_id", "nunique"),
            )
            .reset_index()
        )

        daily["volume_zscore"] = daily.groupby("entity_id")["ping_count"].transform(_zscore)
        daily["location_diversity_zscore"] = daily.groupby("entity_id")[
            "unique_locations"
        ].transform(_zscore)

        daily["movement_anomaly_score"] = (
            daily["volume_zscore"].clip(lower=0) * 25
            + daily["location_diversity_zscore"].clip(lower=0) * 25
        ).clip(0, 100).round(2)

        return daily.sort_values(
            "movement_anomaly_score", ascending=False
        ).reset_index(drop=True)

    # -----------------------------------------------------------------------
    # 2. Graph intelligence
    # -----------------------------------------------------------------------

    def build_entity_graph(
        self,
        communications: Optional[pd.DataFrame] = None,
        transactions: Optional[pd.DataFrame] = None,
        movements: Optional[pd.DataFrame] = None,
    ) -> nx.MultiDiGraph:
        """
        Build one unified multi-source entity graph.

        Node types:
            entity

        Edge attributes:
            relation, source, timestamp, amount, weight
        """
        self.graph = nx.MultiDiGraph()

        if communications is not None and not communications.empty:
            _require_columns(
                communications,
                ["entity_a", "entity_b", "timestamp"],
                "communications",
            )
            for _, row in communications.iterrows():
                a, b = str(row["entity_a"]), str(row["entity_b"])
                self.graph.add_node(a, node_type="entity")
                self.graph.add_node(b, node_type="entity")
                self.graph.add_edge(
                    a,
                    b,
                    relation="communication",
                    source="communications",
                    timestamp=_json_safe(row["timestamp"]),
                    weight=1.0,
                )

        if transactions is not None and not transactions.empty:
            _require_columns(
                transactions,
                ["sender", "receiver", "amount", "timestamp"],
                "transactions",
            )
            for _, row in transactions.iterrows():
                a, b = str(row["sender"]), str(row["receiver"])
                amount = _safe_float(row["amount"])
                self.graph.add_node(a, node_type="entity")
                self.graph.add_node(b, node_type="entity")
                self.graph.add_edge(
                    a,
                    b,
                    relation="transaction",
                    source="transactions",
                    amount=amount,
                    timestamp=_json_safe(row["timestamp"]),
                    weight=1.0 + np.log1p(max(amount, 0)) / 10.0,
                )

        if movements is not None and not movements.empty:
            _require_columns(
                movements,
                ["entity_id", "location_id", "timestamp"],
                "movements",
            )
            # Locations are represented as nodes, allowing entity-location
            # convergence analysis without changing the entity graph contract.
            for _, row in movements.iterrows():
                entity = str(row["entity_id"])
                location = f"location::{row['location_id']}"
                self.graph.add_node(entity, node_type="entity")
                self.graph.add_node(location, node_type="location")
                self.graph.add_edge(
                    entity,
                    location,
                    relation="movement",
                    source="movements",
                    timestamp=_json_safe(row["timestamp"]),
                    weight=1.0,
                )

        return self.graph

    def graph_risk_scores(self) -> pd.DataFrame:
        """
        Score graph entities using centrality and bridge-like behaviour.

        This is a prioritization score, not a criminality score.
        """
        if self.graph.number_of_nodes() == 0:
            return pd.DataFrame(
                columns=[
                    "entity_id", "degree_centrality", "betweenness_centrality",
                    "pagerank", "bridge_score", "graph_risk_score"
                ]
            )

        G = self.graph.to_undirected()

        degree = nx.degree_centrality(G)
        betweenness = nx.betweenness_centrality(G, normalized=True)

        try:
            pagerank = nx.pagerank(G)
        except nx.NetworkXException:
            pagerank = {n: 0.0 for n in G.nodes}

        rows = []
        for node in G.nodes:
            if self.graph.nodes[node].get("node_type") != "entity":
                continue

            # A bridge-like score combines betweenness and degree.
            bridge = 0.65 * betweenness.get(node, 0.0) + 0.35 * degree.get(node, 0.0)

            raw = (
                40 * degree.get(node, 0.0)
                + 45 * betweenness.get(node, 0.0)
                + 15 * pagerank.get(node, 0.0)
            )

            rows.append(
                {
                    "entity_id": str(node),
                    "degree_centrality": round(degree.get(node, 0.0), 6),
                    "betweenness_centrality": round(betweenness.get(node, 0.0), 6),
                    "pagerank": round(pagerank.get(node, 0.0), 6),
                    "bridge_score": round(bridge, 6),
                    "graph_risk_score": round(
                        _normalise_score(raw * 100), 2
                    ),
                }
            )

        result = pd.DataFrame(rows)
        if result.empty:
            return result

        threshold = np.percentile(
            result["graph_risk_score"],
            self.config.graph_high_risk_percentile,
        )
        result["high_risk_graph_node"] = result["graph_risk_score"] >= threshold

        return result.sort_values(
            "graph_risk_score", ascending=False
        ).reset_index(drop=True)

    def detect_suspect_clusters(
        self,
        min_cluster_size: int = 2,
    ) -> pd.DataFrame:
        """
        Identify dense communities using NetworkX greedy modularity.
        """
        if self.graph.number_of_nodes() == 0:
            return pd.DataFrame(columns=["cluster_id", "entities", "size", "density"])

        G = self.graph.to_undirected()
        communities = nx.community.greedy_modularity_communities(G)

        rows = []
        cluster_id = 1

        for community in communities:
            members = sorted(
                str(n)
                for n in community
                if self.graph.nodes[n].get("node_type") == "entity"
            )
            if len(members) < min_cluster_size:
                continue

            subgraph = G.subgraph(community)
            rows.append(
                {
                    "cluster_id": f"C{cluster_id:03d}",
                    "entities": members,
                    "size": len(members),
                    "density": round(nx.density(subgraph), 4),
                }
            )
            cluster_id += 1

        return pd.DataFrame(rows).sort_values(
            "size", ascending=False
        ).reset_index(drop=True)

    def related_entity_chain(
        self,
        source: str,
        target: str,
        cutoff: int = 4,
    ) -> List[str]:
        """Return the shortest entity path between two nodes."""
        source, target = str(source), str(target)
        if source not in self.graph or target not in self.graph:
            return []

        try:
            path = nx.shortest_path(
                self.graph.to_undirected(),
                source,
                target,
            )
            if len(path) - 1 <= cutoff:
                return [str(x) for x in path]
        except nx.NetworkXNoPath:
            pass

        return []

    # -----------------------------------------------------------------------
    # 3. Alert generation
    # -----------------------------------------------------------------------

    def _severity(self, score: float) -> str:
        if score >= 85:
            return "critical"
        if score >= 70:
            return "high"
        if score >= 55:
            return "medium"
        return "low"

    def _alert(
        self,
        alert_type: str,
        score: float,
        confidence: float,
        summary: str,
        entities: Iterable[str],
        evidence: Dict[str, Any],
        entity_graph: Optional[Dict[str, Any]] = None,
        recommended_review: str = "Review source evidence and corroborating records.",
    ) -> IntelligenceAlert:
        alert_id = f"ALT-{len(self.alerts) + 1:05d}"
        return IntelligenceAlert(
            alert_id=alert_id,
            alert_type=alert_type,
            severity=self._severity(score),
            score=round(_normalise_score(score), 2),
            confidence=round(_normalise_score(confidence), 2),
            summary=summary,
            entities=sorted(set(str(x) for x in entities)),
            evidence=_json_safe(evidence),
            entity_graph=_json_safe(entity_graph or {}),
            recommended_review=recommended_review,
        )

    def generate_alerts(
        self,
        contact_chains: Optional[pd.DataFrame] = None,
        coordinated_sequences: Optional[pd.DataFrame] = None,
        financial_anomalies: Optional[pd.DataFrame] = None,
        communication_spikes: Optional[pd.DataFrame] = None,
        location_loops: Optional[pd.DataFrame] = None,
        graph_scores: Optional[pd.DataFrame] = None,
        clusters: Optional[pd.DataFrame] = None,
    ) -> List[Dict[str, Any]]:
        """
        Convert detector output into dashboard/API-ready alert payloads.
        """
        generated: List[IntelligenceAlert] = []

        if contact_chains is not None and not contact_chains.empty:
            for _, row in contact_chains.iterrows():
                score = _safe_float(row.get("chain_strength"), 0)
                if score < self.config.alert_threshold:
                    continue

                entities = row.get("entities", [])
                generated.append(
                    self._alert(
                        "MULTI_HOP_CONTACT_CHAIN",
                        score,
                        min(95, 55 + score * 0.4),
                        f"Multi-hop contact chain detected: {row.get('chain')}.",
                        entities,
                        {
                            "duration_minutes": row.get("duration_minutes"),
                            "case_ids": row.get("case_ids", []),
                            "hops": row.get("hops"),
                        },
                        {
                            "nodes": list(entities),
                            "edges": [
                                {"source": entities[i], "target": entities[i + 1]}
                                for i in range(len(entities) - 1)
                            ],
                        },
                        "Validate timestamps, case linkage and independent evidence.",
                    )
                )

        if coordinated_sequences is not None and not coordinated_sequences.empty:
            for _, row in coordinated_sequences.iterrows():
                score = _safe_float(row.get("sequence_strength"), 0)
                if score < self.config.alert_threshold:
                    continue

                entity = str(row["entity_id"])
                generated.append(
                    self._alert(
                        "COORDINATED_ACTIVITY",
                        score,
                        min(98, 60 + score * 0.35),
                        f"Rapid event sequence detected for entity {entity}.",
                        [entity],
                        {
                            "sequence": row.get("sequence"),
                            "duration_minutes": row.get("duration_minutes"),
                        },
                        {"nodes": [entity], "edges": []},
                        "Review the individual events and determine whether the sequence has an innocent explanation.",
                    )
                )

        if financial_anomalies is not None and not financial_anomalies.empty:
            anomalies = financial_anomalies[
                financial_anomalies["is_anomaly"] == True  # noqa: E712
            ]
            for _, row in anomalies.head(self.config.max_alerts).iterrows():
                score = _safe_float(row.get("anomaly_score"))
                if score < self.config.alert_threshold:
                    continue

                entities = [str(row["sender"]), str(row["receiver"])]
                generated.append(
                    self._alert(
                        "FINANCIAL_ANOMALY",
                        score,
                        min(97, 50 + score * 0.45),
                        f"Unusual transaction pattern detected between {entities[0]} and {entities[1]}.",
                        entities,
                        {
                            "amount": row.get("amount"),
                            "amount_zscore": row.get("amount_zscore"),
                            "anomaly_score": row.get("anomaly_score"),
                            "timestamp": row.get("timestamp"),
                        },
                        {
                            "nodes": entities,
                            "edges": [
                                {
                                    "source": entities[0],
                                    "target": entities[1],
                                    "relation": "transaction",
                                }
                            ],
                        },
                        "Check transaction context, historical baseline and legitimate business/personal explanations.",
                    )
                )

        if communication_spikes is not None and not communication_spikes.empty:
            spikes = communication_spikes[
                communication_spikes["is_spike"] == True  # noqa: E712
            ]
            for _, row in spikes.head(self.config.max_alerts).iterrows():
                z = _safe_float(row.get("zscore"))
                score = _normalise_score(55 + z * 12)
                if score < self.config.alert_threshold:
                    continue

                entity = str(row["entity"])
                generated.append(
                    self._alert(
                        "COMMUNICATION_SPIKE",
                        score,
                        min(92, 50 + z * 10),
                        f"Communication volume is unusually high for {entity}.",
                        [entity],
                        {
                            "date": row.get("date"),
                            "communication_count": row.get("count"),
                            "zscore": row.get("zscore"),
                        },
                        {"nodes": [entity], "edges": []},
                        "Compare against the entity's normal communication pattern and known operational activity.",
                    )
                )

        if location_loops is not None and not location_loops.empty:
            for _, row in location_loops.iterrows():
                score = _safe_float(row.get("loop_strength"))
                if score < self.config.alert_threshold:
                    continue

                entity = str(row["entity_id"])
                generated.append(
                    self._alert(
                        "RECURRING_LOCATION_LOOP",
                        score,
                        min(90, 50 + score * 0.4),
                        f"Recurring location loop detected for {entity}.",
                        [entity],
                        {
                            "loop": row.get("loop"),
                            "duration_minutes": row.get("duration_minutes"),
                            "unique_locations": row.get("unique_locations"),
                        },
                        {"nodes": [entity], "edges": []},
                        "Verify location-data quality and compare the trajectory with known routine activity.",
                    )
                )

        if graph_scores is not None and not graph_scores.empty:
            for _, row in graph_scores[
                graph_scores["high_risk_graph_node"] == True  # noqa: E712
            ].head(self.config.max_alerts).iterrows():
                score = _safe_float(row.get("graph_risk_score"))
                if score < self.config.alert_threshold:
                    continue

                entity = str(row["entity_id"])
                generated.append(
                    self._alert(
                        "GRAPH_BRIDGE_ENTITY",
                        score,
                        min(94, 55 + score * 0.35),
                        f"Entity {entity} has unusually strong network/bridge characteristics.",
                        [entity],
                        {
                            "degree_centrality": row.get("degree_centrality"),
                            "betweenness_centrality": row.get("betweenness_centrality"),
                            "pagerank": row.get("pagerank"),
                            "bridge_score": row.get("bridge_score"),
                        },
                        {"nodes": [entity], "edges": []},
                        "Inspect the entity's cross-cluster relationships and corroborate the underlying links.",
                    )
                )

        if clusters is not None and not clusters.empty:
            for _, row in clusters.iterrows():
                size = int(row.get("size", 0))
                density = _safe_float(row.get("density"))
                score = _normalise_score(45 + min(size, 10) * 4 + density * 40)

                if score < self.config.alert_threshold:
                    continue

                generated.append(
                    self._alert(
                        "EMERGING_ENTITY_CLUSTER",
                        score,
                        min(90, 50 + density * 40),
                        f"Dense entity cluster {row.get('cluster_id')} detected.",
                        row.get("entities", []),
                        {
                            "cluster_id": row.get("cluster_id"),
                            "size": size,
                            "density": density,
                        },
                        {
                            "nodes": row.get("entities", []),
                            "edges": [],
                        },
                        "Review relationships within the cluster and distinguish routine associations from relevant case links.",
                    )
                )

        generated.sort(key=lambda a: (a.score, a.confidence), reverse=True)
        self.alerts.extend(generated[: self.config.max_alerts])

        return [a.to_dict() for a in self.alerts[-self.config.max_alerts:]]

    # -----------------------------------------------------------------------
    # 4. ML-ready feature extractor
    # -----------------------------------------------------------------------

    def extract_entity_features(
        self,
        communications: Optional[pd.DataFrame] = None,
        transactions: Optional[pd.DataFrame] = None,
        movements: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """
        Produce one row per entity with numerical features suitable for future
        predictive models.

        Features include:
            communication volume/diversity
            transaction count/value/diversity
            movement volume/location diversity
            graph centrality
        """
        entities = set()

        feature_frames = []

        if communications is not None and not communications.empty:
            _require_columns(
                communications,
                ["entity_a", "entity_b", "timestamp"],
                "communications",
            )
            a = communications[["entity_a"]].rename(columns={"entity_a": "entity_id"})
            b = communications[["entity_b"]].rename(columns={"entity_b": "entity_id"})
            entities.update(a["entity_id"].astype(str))
            entities.update(b["entity_id"].astype(str))

            comm_long = pd.concat([a, b], ignore_index=True)
            comm_features = comm_long.groupby(
                comm_long["entity_id"].astype(str)
            ).size().rename("communication_count").to_frame()

            if "communication_type" in communications.columns:
                types_a = communications[["entity_a", "communication_type"]].rename(
                    columns={"entity_a": "entity_id"}
                )
                types_b = communications[["entity_b", "communication_type"]].rename(
                    columns={"entity_b": "entity_id"}
                )
                types = pd.concat([types_a, types_b], ignore_index=True)
                diversity = types.groupby(types["entity_id"].astype(str))[
                    "communication_type"
                ].nunique().rename("communication_type_diversity")
                comm_features = comm_features.join(diversity)

            feature_frames.append(comm_features)

        if transactions is not None and not transactions.empty:
            _require_columns(
                transactions,
                ["sender", "receiver", "amount", "timestamp"],
                "transactions",
            )
            send = transactions[["sender", "amount"]].rename(
                columns={"sender": "entity_id"}
            )
            recv = transactions[["receiver", "amount"]].rename(
                columns={"receiver": "entity_id"}
            )
            tx = pd.concat([send, recv], ignore_index=True)
            tx["entity_id"] = tx["entity_id"].astype(str)
            entities.update(tx["entity_id"])

            tx_features = tx.groupby("entity_id").agg(
                transaction_count=("amount", "size"),
                transaction_total=("amount", "sum"),
                transaction_mean=("amount", "mean"),
                transaction_max=("amount", "max"),
            )
            feature_frames.append(tx_features)

        if movements is not None and not movements.empty:
            _require_columns(
                movements,
                ["entity_id", "location_id", "timestamp"],
                "movements",
            )
            mov = movements.copy()
            mov["entity_id"] = mov["entity_id"].astype(str)
            entities.update(mov["entity_id"])

            mov_features = mov.groupby("entity_id").agg(
                movement_count=("location_id", "size"),
                unique_locations=("location_id", "nunique"),
            )
            feature_frames.append(mov_features)

        result = pd.DataFrame(index=sorted(entities))
        result.index.name = "entity_id"

        for frame in feature_frames:
            result = result.join(frame, how="left")

        # Graph features.
        if self.graph.number_of_nodes() == 0 and any(
            x is not None and not x.empty
            for x in [communications, transactions, movements]
        ):
            self.build_entity_graph(
                communications=communications,
                transactions=transactions,
                movements=movements,
            )

        graph_features = self.graph_risk_scores()
        if not graph_features.empty:
            graph_features = graph_features.set_index("entity_id")[
                [
                    "degree_centrality",
                    "betweenness_centrality",
                    "pagerank",
                    "bridge_score",
                    "graph_risk_score",
                ]
            ]
            result = result.join(graph_features, how="left")

        result = result.fillna(0.0)

        # Stable numeric feature set for ML pipelines.
        for col in result.columns:
            result[col] = pd.to_numeric(result[col], errors="coerce").fillna(0.0)

        return result.reset_index()

    # -----------------------------------------------------------------------
    # 5. One-call pipeline
    # -----------------------------------------------------------------------

    def run(
        self,
        communications: Optional[pd.DataFrame] = None,
        transactions: Optional[pd.DataFrame] = None,
        movements: Optional[pd.DataFrame] = None,
        events: Optional[pd.DataFrame] = None,
    ) -> Dict[str, Any]:
        """
        Run all available detectors and return a single API/dashboard payload.

        Any missing source table is simply skipped.
        """
        contact_chains = (
            self.detect_contact_chains(communications)
            if communications is not None and not communications.empty
            else pd.DataFrame()
        )

        coordinated = (
            self.detect_coordinated_sequences(events)
            if events is not None and not events.empty
            else pd.DataFrame()
        )

        financial = (
            self.detect_financial_anomalies(transactions)
            if transactions is not None and not transactions.empty
            else pd.DataFrame()
        )

        comm_spikes = (
            self.detect_communication_spikes(communications)
            if communications is not None and not communications.empty
            else pd.DataFrame()
        )

        location_loops = (
            self.detect_location_loops(movements)
            if movements is not None and not movements.empty
            else pd.DataFrame()
        )

        movement_anomalies = (
            self.detect_movement_anomalies(movements)
            if movements is not None and not movements.empty
            else pd.DataFrame()
        )

        self.build_entity_graph(
            communications=communications,
            transactions=transactions,
            movements=movements,
        )

        graph_scores = self.graph_risk_scores()
        clusters = self.detect_suspect_clusters()
        features = self.extract_entity_features(
            communications=communications,
            transactions=transactions,
            movements=movements,
        )

        alerts = self.generate_alerts(
            contact_chains=contact_chains,
            coordinated_sequences=coordinated,
            financial_anomalies=financial,
            communication_spikes=comm_spikes,
            location_loops=location_loops,
            graph_scores=graph_scores,
            clusters=clusters,
        )

        return {
            "alerts": alerts,
            "patterns": {
                "contact_chains": contact_chains.to_dict(orient="records"),
                "coordinated_sequences": coordinated.to_dict(orient="records"),
                "location_loops": location_loops.to_dict(orient="records"),
            },
            "anomalies": {
                "financial": financial.to_dict(orient="records"),
                "communication_spikes": comm_spikes.to_dict(orient="records"),
                "movement": movement_anomalies.to_dict(orient="records"),
            },
            "graph": {
                "risk_scores": graph_scores.to_dict(orient="records"),
                "clusters": clusters.to_dict(orient="records"),
            },
            "ml_features": features.to_dict(orient="records"),
            "meta": {
                "nodes": self.graph.number_of_nodes(),
                "edges": self.graph.number_of_edges(),
                "alert_count": len(alerts),
                "engine_version": "1.0.0",
            },
        }


# ---------------------------------------------------------------------------
# Optional convenience function for other modules
# ---------------------------------------------------------------------------

def run_intelligence_engine(
    communications: Optional[pd.DataFrame] = None,
    transactions: Optional[pd.DataFrame] = None,
    movements: Optional[pd.DataFrame] = None,
    events: Optional[pd.DataFrame] = None,
    config: Optional[EngineConfig] = None,
) -> Dict[str, Any]:
    """
    Simple integration point:

        from intelligence_engine import run_intelligence_engine

        result = run_intelligence_engine(
            communications=communications_df,
            transactions=transactions_df,
            movements=movements_df,
            events=events_df,
        )
    """
    engine = PatternIntelligenceEngine(config)
    return engine.run(
        communications=communications,
        transactions=transactions,
        movements=movements,
        events=events,
    )


__all__ = [
    "EngineConfig",
    "IntelligenceAlert",
    "PatternIntelligenceEngine",
    "run_intelligence_engine",
]
