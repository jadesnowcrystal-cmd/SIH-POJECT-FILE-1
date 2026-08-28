import streamlit as st
import pandas as pd
import networkx as nx
import plotly.graph_objects as go
from datetime import datetime, date, time

# Set Page Configuration
st.set_page_config(
    page_title="AI Intelligence Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Dark Theme Styling matching UI design reference
st.markdown("""
<style>
    /* Dark Theme Core */
    .stApp {
        background-color: #0b0d17;
        color: #e2e8f0;
    }
    
    /* Card Container Styling */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }
    
    div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column;"] {
        background-color: #131728;
        border-radius: 12px;
        padding: 16px;
        border: 1px solid #1e243b;
    }

    /* Panel Headers */
    .panel-title {
        font-size: 16px;
        font-weight: 600;
        color: #f1f5f9;
        margin-bottom: 12px;
        letter-spacing: 0.5px;
    }
    
    .section-title {
        font-size: 22px;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 15px;
    }

    /* Information / Warning Boxes */
    .info-box {
        background-color: #1a1f36;
        border-left: 4px solid #6366f1;
        padding: 12px;
        border-radius: 6px;
        color: #cbd5e1;
        font-size: 14px;
    }
    
    .warning-box {
        background-color: #2a1b24;
        border-left: 4px solid #f43f5e;
        padding: 12px;
        border-radius: 6px;
        color: #fecdd3;
        font-size: 14px;
    }

    /* Custom Alerts Styling */
    .alert-high {
        background-color: #2c1527;
        border-left: 4px solid #ec4899;
        padding: 10px;
        margin-bottom: 8px;
        border-radius: 4px;
    }
    .alert-medium {
        background-color: #272115;
        border-left: 4px solid #f59e0b;
        padding: 10px;
        margin-bottom: 8px;
        border-radius: 4px;
    }
    .alert-info {
        background-color: #162032;
        border-left: 4px solid #3b82f6;
        padding: 10px;
        margin-bottom: 8px;
        border-radius: 4px;
    }
    .alert-title {
        font-weight: 600;
        color: #f8fafc;
        font-size: 13px;
    }
    .alert-text {
        font-size: 12px;
        color: #94a3b8;
    }
</style>
""", unsafe_allow_html=True)

# Shared Mock Network Setup
@st.cache_data
def load_network_data():
    data = [
        {"Person": "Amit", "Connected_To": "Rahul", "Location": "Mumbai"},
        {"Person": "Amit", "Connected_To": "Sameer", "Location": "Delhi"},
        {"Person": "Amit", "Connected_To": "Priya", "Location": "Mumbai"},
        {"Person": "Rahul", "Connected_To": "Sameer", "Location": "Pune"},
        {"Person": "Sameer", "Connected_To": "Priya", "Location": "Pune"},
    ]
    df = pd.DataFrame(data)
    G = nx.Graph()
    for _, row in df.iterrows():
        G.add_edge(row["Person"], row["Connected_To"], location=row["Location"])
    
    centrality = nx.degree_centrality(G)
    return df, G, centrality

df, G, centrality = load_network_data()

# Navigation Sidebar
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Select View",
    ["Overview Dashboard", "FIR Registration", "Network Analysis", "Suspicious Activity", "Persons and Witnesses", "Analytics"]
)

# -----------------------------------------------------------------------------
# PAGE 1: OVERVIEW DASHBOARD
# -----------------------------------------------------------------------------
if page == "Overview Dashboard":
    st.markdown('<div class="section-title">Case Intelligence & Network Overview</div>', unsafe_allow_html=True)

    # Top Metric Blocks
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Total Entities", "24", "+3 this week")
    with m2:
        st.metric("Active Investigations", "10", "2 Pending")
    with m3:
        st.metric("Network Centrality Max", "0.75", "Entity: Amit")
    with m4:
        st.metric("High Risk Alerts", "4", "Requires Action")

    st.write("")
    left, middle, right = st.columns([1.5, 1, 1])

    with left:
        st.markdown('<div class="panel-title">Interactive Network Topology</div>', unsafe_allow_html=True)
        pos = nx.spring_layout(G, seed=42)
        
        edge_x, edge_y = [], []
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            mode="lines",
            hoverinfo="none",
            line=dict(width=2, color="#334155")
        )

        node_x, node_y, node_text = [], [], []
        for node in G.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            node_text.append(
                f"<b>{node}</b><br>"
                f"Centrality: {centrality[node]:.2f}<br>"
                f"Connections: {G.degree(node)}"
            )

        node_trace = go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers+text",
            text=list(G.nodes()),
            hovertext=node_text,
            hoverinfo="text",
            textposition="top center",
            marker=dict(
                size=25,
                color="#818cf8",
                line=dict(width=3, color="#1e1b4b")
            ),
            textfont=dict(size=11, color="#cbd5e1")
        )

        fig = go.Figure(data=[edge_trace, node_trace])
        fig.update_layout(
            height=390,
            margin=dict(l=10, r=10, t=10, b=10),
            showlegend=False,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with middle:
        st.markdown('<div class="panel-title">Risk Distribution</div>', unsafe_allow_html=True)
        risk_df = pd.DataFrame({
            "Risk": ["High", "Medium", "Low"],
            "Count": [4, 11, 9]
        })

        risk_fig = go.Figure(
            data=[
                go.Pie(
                    labels=risk_df["Risk"],
                    values=risk_df["Count"],
                    hole=0.68,
                    textinfo="percent",
                    textfont=dict(size=11, color="#ffffff"),
                    marker=dict(colors=["#6366f1", "#a855f7", "#38bdf8"])
                )
            ]
        )
        risk_fig.update_layout(
            height=350,
            margin=dict(l=10, r=10, t=10, b=10),
            showlegend=True,
            paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", y=-0.05, font=dict(color="#94a3b8"))
        )
        st.plotly_chart(risk_fig, use_container_width=True, config={"displayModeBar": False})

    with right:
        st.markdown('<div class="panel-title">Case Status Breakdown</div>', unsafe_allow_html=True)
        case_df = pd.DataFrame({
            "Status": ["Open", "Investigation", "Closed"],
            "Cases": [8, 10, 6]
        })

        case_fig = go.Figure(
            data=[
                go.Bar(
                    x=case_df["Status"],
                    y=case_df["Cases"],
                    marker=dict(color="#818cf8", line=dict(width=0))
                )
            ]
        )
        case_fig.update_layout(
            height=350,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#94a3b8"),
            yaxis=dict(showgrid=True, gridcolor="#1e293b", title=""),
            xaxis=dict(title="")
        )
        st.plotly_chart(case_fig, use_container_width=True, config={"displayModeBar": False})

    st.write("")
    bottom_left, bottom_right = st.columns([1.5, 1])

    with bottom_left:
        st.markdown('<div class="panel-title">Key Suspects & Centrality Rankings</div>', unsafe_allow_html=True)
        ranking = sorted(centrality.items(), key=lambda x: x[1], reverse=True)
        result = pd.DataFrame(ranking, columns=["Entity", "Centrality Score"])
        result["Connections"] = result["Entity"].apply(lambda x: G.degree(x))
        result["Network Role"] = result["Centrality Score"].apply(
            lambda x: "High Connectivity" if x >= 0.6 else "Moderate Connectivity"
        )
        st.dataframe(result, use_container_width=True, hide_index=True)

        # Interactive Expansion View
        with st.expander("🔍 Click to Expand: Suspect Relationship Details & Investigation Timeline"):
            st.markdown("### Extended Entity Relationship Sheet")
            st.write("Detailed Breakdown of Suspect Target Identifiers:")
            st.json({
                "Target": "Amit",
                "Primary Case": "FIR-2026-088",
                "Status": "High-Value Suspect",
                "Linked Phone Nodes": ["+91-9876500000", "+91-9876511111"],
                "Known Intermediaries": ["Sameer", "Rahul"]
            })
            
            st.markdown("### Investigation Visual Timeline")
            timeline_df = pd.DataFrame({
                "Event": ["Initial FIR Filed", "First Node Identified", "Intermediary Contacted", "High Activity Flag"],
                "Date": ["2026-08-01", "2026-08-05", "2026-08-12", "2026-08-20"]
            })
            st.table(timeline_df)

    with bottom_right:
        st.markdown('<div class="panel-title">Recent Alerts</div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="alert-high">
            <div class="alert-title">High connectivity detected</div>
            <div class="alert-text">Entity: Amit · Connections: 3</div>
        </div>
        <div class="alert-medium">
            <div class="alert-title">Multiple-location activity</div>
            <div class="alert-text">Entity: Rahul · Mumbai, Pune</div>
        </div>
        <div class="alert-medium">
            <div class="alert-title">Potential intermediary</div>
            <div class="alert-text">Entity: Sameer</div>
        </div>
        <div class="alert-info">
            <div class="alert-title">Analytical reminder</div>
            <div class="alert-text">AI indicators require verification against source records.</div>
        </div>
        """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# PAGE 2: FIR REGISTRATION
# -----------------------------------------------------------------------------
elif page == "FIR Registration":
    st.markdown('<div class="section-title">FIR / Case Registration</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-box">Enter case information below. For academic demonstrations, use fictional or sample identity information.</div>', unsafe_allow_html=True)
    st.write("")

    st.subheader("1. Primary Details")
    c1, c2, c3 = st.columns(3)
    with c1:
        district = st.text_input("District *", placeholder="Example: Mumbai")
    with c2:
        police_station = st.text_input("Police Station *", placeholder="Example: Andheri Police Station")
    with c3:
        state = st.text_input("State *", placeholder="Example: Maharashtra")

    c1, c2 = st.columns(2)
    with c1:
        fir_number = st.text_input("FIR Number *", placeholder="Example: FIR No. 0123/2026")
    with c2:
        reporting_datetime = st.datetime_input("Date and Time of Reporting", value=datetime.now())

    gd_reference = st.text_input("GD Entry Reference", placeholder="GD Entry Number / Date / Time")
    st.divider()

    st.subheader("2. Details of the Incident")
    c1, c2 = st.columns(2)
    with c1:
        occurrence_date = st.date_input("Date of Occurrence", value=date.today())
    with c2:
        occurrence_time = st.time_input("Time of Occurrence", value=time(12, 0))

    occurrence_place = st.text_area("Place of Occurrence", placeholder="Enter exact location, distance and direction from the police station")
    delay_reporting = st.radio("Was there a delay in reporting?", ["No", "Yes"], horizontal=True)
    delay_reason = ""
    if delay_reporting == "Yes":
        delay_reason = st.text_area("Reason for Delay", placeholder="Explain the reason for delayed reporting")

    st.divider()
    st.subheader("3. Complainant / Informant")
    c1, c2, c3 = st.columns(3)
    with c1:
        complainant_name = st.text_input("Name *")
    with c2:
        complainant_age = st.number_input("Age", min_value=0, max_value=120, value=18)
    with c3:
        complainant_gender = st.selectbox("Gender", ["Select", "Male", "Female", "Other"])

    c1, c2 = st.columns(2)
    with c1:
        father_husband_name = st.text_input("Father's / Husband's Name")
    with c2:
        occupation = st.text_input("Occupation")

    permanent_address = st.text_area("Permanent Address")
    temporary_address = st.text_area("Temporary Address")
    contact = st.text_input("Contact Number")
    identity_number = st.text_input("Identity Reference Number (Optional)", type="password", help="Use fictional information for demonstrations.")

    st.divider()
    st.subheader("4. Accused Details")
    accused_known = st.radio("Is the accused known?", ["Known", "Unknown"], horizontal=True)
    accused_name = ""
    accused_description = ""
    accused_address = ""

    if accused_known == "Known":
        accused_name = st.text_input("Accused Name")
        accused_description = st.text_area("Physical Description / Identifying Marks")
        accused_address = st.text_area("Accused Address")
    else:
        st.info('The accused will be recorded as "Unknown Person(s)".')
        accused_description = st.text_area("Available Description of Unknown Person(s)")

    st.divider()
    st.subheader("5. Witness Information")
    witness_count = st.number_input("Number of Witnesses", min_value=0, max_value=20, value=0)
    witnesses = []

    for i in range(int(witness_count)):
        st.markdown(f"**Witness {i + 1}**")
        w1, w2 = st.columns(2)
        with w1:
            witness_name = st.text_input(f"Witness {i + 1} Name", key=f"witness_name_{i}")
        with w2:
            witness_address = st.text_input(f"Witness {i + 1} Address", key=f"witness_address_{i}")
        witnesses.append({"name": witness_name, "address": witness_address})

    st.divider()
    st.subheader("6. Description of the Crime")
    narrative = st.text_area("Narrative / Statement", height=250, placeholder="Enter a detailed chronological description of the incident.")
    st.markdown('<div class="info-box">The AI engine can analyze this narrative using NLP to identify people, locations, vehicles, organizations, dates and relationships.</div>', unsafe_allow_html=True)

    st.divider()
    st.subheader("7. Property / Stolen Goods")
    property_applicable = st.checkbox("Does this case involve stolen or damaged property?")
    property_name = ""
    property_description = ""
    property_value = 0.0
    imei = ""

    if property_applicable:
        c1, c2 = st.columns(2)
        with c1:
            property_name = st.text_input("Property / Item Name")
        with c2:
            property_value = st.number_input("Estimated Value (₹)", min_value=0.0, value=0.0)
        property_description = st.text_area("Property Description")
        imei = st.text_input("IMEI / Serial Number")

    st.divider()
    st.subheader("8. Particulars of Offense")
    offense_sections = st.text_input("Applicable BNS Section(s)", placeholder="Example: BNS Section 303")
    offense_description = st.text_area("Offense Description")

    st.divider()
    st.subheader("9. Investigating Officer")
    c1, c2, c3 = st.columns(3)
    with c1:
        io_name = st.text_input("IO Name")
    with c2:
        io_rank = st.text_input("IO Rank")
    with c3:
        io_id = st.text_input("Officer ID")

    st.divider()
    st.subheader("10. Verification and Closing Details")
    complainant_signature = st.checkbox("Complainant / Informant Signature or Thumb Impression Received")
    officer_signature = st.checkbox("Officer-in-Charge Signature / Verification Completed")

    st.write("")
    if st.button("Register FIR", type="primary", use_container_width=True):
        if not fir_number:
            st.error("Please enter the FIR Number.")
        elif not complainant_name:
            st.error("Please enter the Complainant Name.")
        elif not district:
            st.error("Please enter the District.")
        elif not police_station:
            st.error("Please enter the Police Station.")
        elif not state:
            st.error("Please enter the State.")
        else:
            st.session_state["fir_registered"] = True
            st.success(f"FIR {fir_number} registered successfully.")
            st.info("The case is ready for AI-assisted entity extraction and network analysis.")

# -----------------------------------------------------------------------------
# PAGE 3: NETWORK ANALYSIS
# -----------------------------------------------------------------------------
elif page == "Network Analysis":
    st.markdown('<div class="section-title">Criminal Network Analysis</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-box">Explore relationships between people and entities identified from case records.</div>', unsafe_allow_html=True)
    st.write("")

    selected_person = st.selectbox("Select Entity", list(G.nodes()))
    neighbors = list(G.neighbors(selected_person))

    st.markdown(f'<div class="panel-title">Connections of {selected_person}</div>', unsafe_allow_html=True)

    if neighbors:
        connection_df = pd.DataFrame({
            "Connected Entity": neighbors,
            "Relationship Type": ["Observed association" for _ in neighbors],
            "Location": [
                df[
                    ((df["Person"] == selected_person) & (df["Connected_To"] == person)) |
                    ((df["Connected_To"] == selected_person) & (df["Person"] == person))
                ]["Location"].iloc[0]
                if not df[
                    ((df["Person"] == selected_person) & (df["Connected_To"] == person)) |
                    ((df["Connected_To"] == selected_person) & (df["Person"] == person))
                ].empty else "Unknown"
                for person in neighbors
            ]
        })
        st.dataframe(connection_df, use_container_width=True, hide_index=True)
    else:
        st.info("No direct connections found.")

    st.write("")
    pos = nx.spring_layout(G, seed=42)
    edge_x, edge_y = [], []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        mode="lines",
        hoverinfo="none",
        line=dict(width=2, color="#475569")
    )

    node_x, node_y = [], []
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode="markers+text",
        text=list(G.nodes()),
        textposition="top center",
        marker=dict(
            size=30,
            color="#818cf8",
            line=dict(width=3, color="#1e1b4b")
        ),
        textfont=dict(color="#f8fafc")
    )

    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(
        height=600,
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# -----------------------------------------------------------------------------
# PAGE 4: SUSPICIOUS ACTIVITY
# -----------------------------------------------------------------------------
elif page == "Suspicious Activity":
    st.markdown('<div class="section-title">Suspicious Activity Detection</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-box">AI-assisted identification of unusual patterns and network indicators.</div>', unsafe_allow_html=True)
    st.write("")

    alerts_data = pd.DataFrame({
        "Alert ID": ["ALT-001", "ALT-002", "ALT-003", "ALT-004"],
        "Entity": ["Amit", "Rahul", "Sameer", "Phone-9876"],
        "Pattern": [
            "High network connectivity",
            "Multiple locations",
            "Potential intermediary",
            "Multiple person association"
        ],
        "Risk Level": ["High", "Medium", "Medium", "High"],
        "Status": [
            "Requires Review",
            "Requires Review",
            "Under Analysis",
            "Requires Review"
        ]
    })

    st.dataframe(alerts_data, use_container_width=True, hide_index=True)
    st.write("")
    st.subheader("AI Investigation Insight")
    st.markdown("""
    <div class="warning-box">
    The system has identified entities with unusually high connectivity,
    multiple location associations or intermediary-like network positions.
    These are analytical indicators only and should be verified against
    original records by authorized investigators.
    </div>
    """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# PAGE 5: PERSONS AND WITNESSES
# -----------------------------------------------------------------------------
elif page == "Persons and Witnesses":
    st.markdown('<div class="section-title">Persons and Witnesses</div>', unsafe_allow_html=True)
    tabs = st.tabs(["Persons", "Witnesses", "Entities"])

    with tabs[0]:
        persons_data = pd.DataFrame({
            "Name": ["Rahul", "Amit", "Sameer", "Priya"],
            "Role": ["Person of Interest", "Person of Interest", "Person of Interest", "Witness"],
            "Connections": [2, 3, 3, 2],
            "Locations": ["Mumbai, Pune", "Mumbai, Delhi", "Pune, Mumbai", "Delhi"]
        })
        st.dataframe(persons_data, use_container_width=True, hide_index=True)

    with tabs[1]:
        witness_data = pd.DataFrame({
            "Witness": ["Witness A", "Witness B", "Witness C"],
            "Location": ["Mumbai", "Pune", "Delhi"],
            "Statement Status": ["Recorded", "Pending", "Recorded"]
        })
        st.dataframe(witness_data, use_container_width=True, hide_index=True)

    with tabs[2]:
        entities = pd.DataFrame({
            "Entity Type": ["Person", "Phone", "Vehicle", "Location", "Organization"],
            "Count": [24, 15, 8, 12, 5]
        })
        st.dataframe(entities, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# PAGE 6: ANALYTICS
# -----------------------------------------------------------------------------
elif page == "Analytics":
    st.markdown('<div class="section-title">Network Analytics</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)

    with c1:
        st.markdown('<div class="panel-title">Degree Centrality</div>', unsafe_allow_html=True)
        centrality_df = pd.DataFrame(centrality.items(), columns=["Person", "Centrality"])
        centrality_df = centrality_df.sort_values("Centrality", ascending=False)

        fig = go.Figure(
            data=[
                go.Bar(
                    x=centrality_df["Person"],
                    y=centrality_df["Centrality"],
                    marker=dict(color="#818cf8")
                )
            ]
        )
        fig.update_layout(
            height=400,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#94a3b8"),
            yaxis_title="Centrality Score",
            xaxis_title="Person",
            margin=dict(l=30, r=20, t=20, b=30),
            yaxis=dict(gridcolor="#1e293b")
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with c2:
        st.markdown('<div class="panel-title">Location Distribution</div>', unsafe_allow_html=True)
        location_count = df["Location"].value_counts().reset_index()
        location_count.columns = ["Location", "Count"]

        fig2 = go.Figure(
            data=[
                go.Pie(
                    labels=location_count["Location"],
                    values=location_count["Count"],
                    hole=0.55,
                    marker=dict(colors=["#6366f1", "#a855f7", "#38bdf8"])
                )
            ]
        )
        fig2.update_layout(
            height=400,
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=20, r=20, t=20, b=20),
            font=dict(color="#94a3b8")
        )
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

    st.write("")
    st.markdown('<div class="panel-title">Source Data</div>', unsafe_allow_html=True)
    st.dataframe(df, use_container_width=True, hide_index=True)

st.divider()
st.caption(
    "Prototype for academic and hackathon purposes. AI-generated insights are decision-support information and do not establish criminal guilt."
)
