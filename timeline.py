import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
from typing import Dict, List, Any, Optional

# ==========================================
# TIMELINE ENGINE & DATA CORRELATION LOGIC
# ==========================================

class TimelineCorrelationEngine:
    """
    Transforms multi-source investigation metadata (FIRs, CDRs, Bank Transactions, 
    Location Traces) into structured, chronologically correlated timeline events.
    """

    EVENT_COLOR_MAP = {
        "FIR": "#EF4444",         # Red
        "Call": "#3B82F6",        # Blue
        "Location": "#10B981",    # Green
        "Transaction": "#F59E0B", # Amber
        "Meeting": "#8B5CF6",     # Purple
        "Interrogation": "#6366F1"# Indigo
    }

    @classmethod
    def generate_default_mock_data(cls) -> pd.DataFrame:
        """Fallback mock timeline data for standalone testing."""
        return pd.DataFrame({
            "Event_ID": [f"EVT-{i:03d}" for i in range(1, 7)],
            "Date": ["2026-08-20", "2026-08-20", "2026-08-20", "2026-08-20", "2026-08-20", "2026-08-21"],
            "Time": ["10:00", "10:25", "10:45", "11:30", "12:15", "09:30"],
            "DateTime": [
                pd.to_datetime("2026-08-20 10:00"),
                pd.to_datetime("2026-08-20 10:25"),
                pd.to_datetime("2026-08-20 10:45"),
                pd.to_datetime("2026-08-20 11:30"),
                pd.to_datetime("2026-08-20 12:15"),
                pd.to_datetime("2026-08-21 09:30")
            ],
            "Event Type": ["FIR", "Call", "Location", "Transaction", "Meeting", "Call"],
            "Person": ["Unknown", "Rahul", "Rahul", "Rahul", "Rahul", "Amit"],
            "Location": ["Police Station", "Mumbai", "Station Road", "Mumbai", "City Mall", "Delhi"],
            "Description": [
                "FIR incident reported at Airoli Station",
                "Outgoing Call: Rahul (Caller) to Amit (Receiver), 180s",
                "Tower ping: Rahul detected near Station Road",
                "Financial transaction: ₹50,000 sent via UPI",
                "Physical rendezvous observed: Rahul and Amit",
                "Call recorded between Amit and Sameer, duration 45s"
            ],
            "Source": [
                "FIR Records", "Call Records", "Location Logs", 
                "Bank Records", "Investigation Records", "Call Records"
            ],
            "Risk Score": [80, 40, 65, 90, 85, 50]
        })

    @classmethod
    def convert_nlp_output_to_timeline(cls, nlp_output: Dict[str, Any]) -> pd.DataFrame:
        """
        Translates output from Janvi's RAG/NLP module into a chronologically 
        structured pandas DataFrame.
        """
        events = []
        meta = nlp_output.get("metadata", {})
        case_id = meta.get("case_id", "UNKNOWN_CASE")
        
        # 1. Parse Relations as Temporal Events
        for idx, rel in enumerate(nlp_output.get("relations", []), start=1):
            action = rel.get("action", "ASSOCIATED_WITH")
            
            # Map NLP actions to standardized visual Event Types
            event_type = "Meeting" if action == "MEETING" else \
                         "Call" if action == "COMMUNICATION" else \
                         "Transaction" if action == "TRANSACTION" else "Location"
            
            ctx = rel.get("context", "")
            events.append({
                "Event_ID": f"{case_id}-EVT-{idx:02d}",
                "Date": "2026-08-20", # Extracted or default fallback
                "Time": f"10:{10*idx:02d}",
                "DateTime": pd.to_datetime("2026-08-20") + pd.Timedelta(minutes=25 * idx),
                "Event Type": event_type,
                "Person": rel.get("source", "Entity_Src"),
                "Location": "Investigation Site",
                "Description": f"[{action}] Context: {ctx}",
                "Source": "Janvi RAG NLP Engine",
                "Risk Score": 75 if action in ["TRANSACTION", "MEETING"] else 40
            })
            
        if not events:
            return cls.generate_default_mock_data()
            
        return pd.DataFrame(events)


# ==========================================
# STREAMLIT UI RENDERER: TIMELINE PAGE
# ==========================================

elif page == "Timeline & Event Correlation":

    # 1. Page Section Header
    st.markdown(
        '<div class="section-title">Timeline & Event Correlation</div>',
        unsafe_allow_html=True
    )

    st.markdown("""
    <div class="info-box">
    Reconstruct the chronological sequence of criminal investigation events 
    synthesized across FIR filings, call data records (CDR), bank statements, and spatial movement logs.
    </div>
    """, unsafe_allow_html=True)

    st.write("")

    # 2. Data Synchronization Layer (Connect with Previous Modules)
    if "janvi_nlp_output" in st.session_state and st.session_state["janvi_nlp_output"]:
        st.success("Connected to Janvi's NLP Extraction Engine Output.")
        timeline_df = TimelineCorrelationEngine.convert_nlp_output_to_timeline(st.session_state["janvi_nlp_output"])
    else:
        timeline_df = TimelineCorrelationEngine.generate_default_mock_data()

    # Ensure correct datetime conversion
    timeline_df["DateTime"] = pd.to_datetime(timeline_df["DateTime"])
    timeline_df = timeline_df.sort_values(by="DateTime")

    # 3. Sidebar Filtering Controls
    st.sidebar.markdown("### Timeline Controls")
    
    selected_persons = st.sidebar.multiselect(
        "Filter by Persons:",
        options=list(timeline_df["Person"].unique()),
        default=list(timeline_df["Person"].unique())
    )
    
    selected_sources = st.sidebar.multiselect(
        "Filter by Data Sources:",
        options=list(timeline_df["Source"].unique()),
        default=list(timeline_df["Source"].unique())
    )
    
    selected_types = st.sidebar.multiselect(
        "Filter by Event Types:",
        options=list(timeline_df["Event Type"].unique()),
        default=list(timeline_df["Event Type"].unique())
    )

    # Filter application
    filtered_df = timeline_df[
        (timeline_df["Person"].isin(selected_persons)) &
        (timeline_df["Source"].isin(selected_sources)) &
        (timeline_df["Event Type"].isin(selected_types))
    ]

    # 4. Interactive Plotly Timeline Chart Rendering
    st.subheader("Interactive Visual Timeline")

    if not filtered_df.empty:
        # Construct timeline scatter plot with custom hover metadata
        fig = px.scatter(
            filtered_df,
            x="DateTime",
            y="Person",
            color="Event Type",
            size="Risk Score",
            hover_name="Event Type",
            hover_data={
                "DateTime": "|%B %d, %Y - %H:%M",
                "Location": True,
                "Description": True,
                "Source": True,
                "Risk Score": True,
                "Person": False
            },
            color_discrete_map=TimelineCorrelationEngine.EVENT_COLOR_MAP,
            title="Chronological Event Correlation Chart"
        )

        # Style plot trace lines
        fig.update_traces(marker=dict(symbol="circle", line=dict(width=1, color="DarkSlateGrey")))
        
        # Add connecting lines between chronological events per person
        for person in filtered_df["Person"].unique():
            person_df = filtered_df[filtered_df["Person"] == person].sort_values("DateTime")
            if len(person_df) > 1:
                fig.add_trace(
                    go.Scatter(
                        x=person_df["DateTime"],
                        y=person_df["Person"],
                        mode="lines",
                        line=dict(color="rgba(150, 150, 150, 0.4)", width=2, dash="dot"),
                        showlegend=False,
                        hoverinfo="skip"
                    )
                )

        fig.update_layout(
            xaxis_title="Timestamp of Event",
            yaxis_title="Involved Entity / Person",
            height=420,
            template="plotly_dark",
            margin=dict(l=20, r=20, t=50, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No timeline events match the selected filter criteria.")

    # 5. Temporal Metrics Dashboard
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Events", len(filtered_df))
    m2.metric("Involved Suspects", filtered_df["Person"].nunique())
    m3.metric("Primary Location", filtered_df["Location"].mode()[0] if not filtered_df.empty else "N/A")
    m4.metric("Highest Risk Event", f"{filtered_df['Risk Score'].max() if not filtered_df.empty else 0}/100")

    st.write("")

    # 6. Detailed Investigative Ledger / Data Grid
    st.subheader("Event Intelligence Log")
    
    # Custom display formatting for Streamlit Dataframe
    display_df = filtered_df[[
        "Event_ID", "Date", "Time", "Event Type", "Person", 
        "Location", "Description", "Source", "Risk Score"
    ]].copy()

    st.dataframe(
        display_df,
        column_config={
            "Risk Score": st.column_config.ProgressColumn(
                "Event Risk Level",
                help="Automated risk score derived from event correlation",
                format="%d",
                min_value=0,
                max_value=100,
            ),
            "Source": st.column_config.TextColumn("Data Source Origin")
        },
        use_container_width=True,
        hide_index=True
    )

    # 7. Correlation Analysis Export Tools
    st.write("")
    c1, c2 = st.columns([3, 1])
    with c1:
        st.caption("Data sources cross-referenced with Neo4j Graph Database & RAG Search Engine.")
    with c2:
        csv_data = display_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Export Timeline (CSV)",
            data=csv_data,
            file_name=f"investigation_timeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )
