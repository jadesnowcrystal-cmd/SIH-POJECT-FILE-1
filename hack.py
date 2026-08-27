import streamlit as st
import pandas as pd
import networkx as nx
import plotly.graph_objects as go
from datetime import datetime, date, time

st.set_page_config(
    page_title="CNIS Intelligence",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

* {
    font-family: 'Inter', sans-serif;
}

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background: #f7f8fc;
}

.block-container {
    padding-top: 1.5rem;
    padding-bottom: 2rem;
    max-width: 1500px;
}

[data-testid="stSidebar"] {
    background: #ffffff !important;
    border-right: 1px solid #e7e8f0;
}

[data-testid="stSidebar"] > div:first-child {
    padding: 25px 18px;
}

.brand {
    font-size: 18px;
    font-weight: 700;
    color: #30335a;
    padding: 5px 10px 25px 10px;
}

.brand span {
    color: #6254d9;
}

.nav-title {
    font-size: 10px;
    font-weight: 700;
    color: #9b9db0;
    letter-spacing: 1.5px;
    padding: 15px 10px 8px 10px;
}

[data-testid="stSidebar"] [data-testid="stRadio"] > div {
    gap: 4px;
}

[data-testid="stSidebar"] [data-testid="stRadio"] label {
    background: transparent !important;
    border-radius: 9px;
    padding: 8px 10px !important;
    margin: 2px 0;
    color: #4c4f69 !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    transition: 0.2s;
}

[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
    background: #f2f0ff !important;
}

[data-testid="stSidebar"] [data-testid="stRadio"] label p {
    color: #4c4f69 !important;
}

[data-testid="stSidebar"] [data-testid="stRadio"] input {
    accent-color: #6b5ce7;
}

[data-testid="stSidebar"] .stSuccess {
    background: #eefaf3;
    border: 1px solid #d8f1e1;
    color: #32965c;
    border-radius: 8px;
    font-size: 12px;
    padding: 8px 10px;
}

.header {
    background: #ffffff;
    border: 1px solid #e9eaf1;
    border-radius: 18px;
    padding: 28px 32px;
    margin-bottom: 25px;
    box-shadow: 0 5px 20px rgba(45, 48, 80, 0.04);
}

.header h1 {
    color: #292c4a;
    font-size: 29px;
    font-weight: 700;
    margin: 0;
}

.header p {
    color: #8b8da0;
    font-size: 13px;
    margin-top: 7px;
    margin-bottom: 0;
}

.section-title {
    color: #30334f;
    font-size: 21px;
    font-weight: 700;
    margin: 10px 0 18px 0;
}

.filter-card {
    background: #ffffff;
    border: 1px solid #e9eaf1;
    border-radius: 14px;
    padding: 12px;
    margin-bottom: 20px;
    box-shadow: 0 4px 15px rgba(45, 48, 80, 0.03);
}

.metric-card {
    background: #ffffff;
    border: 1px solid #e9eaf1;
    border-radius: 14px;
    padding: 17px 19px;
    min-height: 108px;
    box-shadow: 0 4px 15px rgba(45, 48, 80, 0.035);
}

.metric-title {
    font-size: 11px;
    color: #9294a5;
    font-weight: 500;
    margin-bottom: 9px;
}

.metric-value {
    font-size: 27px;
    font-weight: 700;
    color: #30334d;
}

.metric-sub {
    font-size: 10px;
    color: #a0a2b0;
    margin-top: 5px;
}

.panel {
    background: #ffffff;
    border: 1px solid #e9eaf1;
    border-radius: 15px;
    padding: 20px;
    box-shadow: 0 4px 15px rgba(45, 48, 80, 0.035);
}

.panel-title {
    color: #353750;
    font-size: 15px;
    font-weight: 600;
    margin-bottom: 10px;
}

.alert-high {
    background: #fff1f2;
    border-left: 4px solid #e45b69;
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 10px;
}

.alert-medium {
    background: #fff8eb;
    border-left: 4px solid #e7a840;
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 10px;
}

.alert-info {
    background: #f1f4ff;
    border-left: 4px solid #7568df;
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 10px;
}

.alert-title {
    font-size: 12px;
    font-weight: 600;
    color: #3d4058;
}

.alert-text {
    font-size: 10px;
    color: #7d8092;
    margin-top: 4px;
}

.info-box {
    background: #f3f4ff;
    border-left: 4px solid #6b5ce7;
    border-radius: 8px;
    padding: 13px;
    color: #5a5c75;
    font-size: 12px;
}

.warning-box {
    background: #fff8ec;
    border-left: 4px solid #e6a63b;
    border-radius: 8px;
    padding: 13px;
    color: #756044;
    font-size: 12px;
}

.stButton > button {
    border-radius: 9px;
    font-weight: 600;
    border: none;
    min-height: 42px;
}

.stButton > button[kind="primary"] {
    background: linear-gradient(90deg, #6656d9, #836be8);
}

[data-baseweb="select"] > div {
    background-color: #ffffff !important;
    border: 1px solid #e2e3eb !important;
    border-radius: 9px !important;
    min-height: 40px !important;
    color: #33364e !important;
}

[data-baseweb="select"] span {
    color: #33364e !important;
}

.stTextInput input,
.stTextArea textarea,
.stNumberInput input,
.stDateInput input,
.stTimeInput input {
    background: #ffffff !important;
    border: 1px solid #e2e3eb !important;
    border-radius: 9px !important;
    color: #33364e !important;
}

.stTextInput input:focus,
.stTextArea textarea:focus,
.stNumberInput input:focus {
    border-color: #7768df !important;
    box-shadow: 0 0 0 1px #7768df !important;
}

label {
    color: #555870 !important;
    font-size: 12px !important;
    font-weight: 500 !important;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
}

.stTabs [data-baseweb="tab"] {
    background: #ffffff;
    border-radius: 8px;
    padding: 8px 16px;
    color: #696b7e;
}

.stTabs [aria-selected="true"] {
    color: #6254d9 !important;
}

footer {
    visibility: hidden;
}
</style>
""", unsafe_allow_html=True)

data = {
    "Person": [
        "Rahul", "Rahul", "Amit", "Amit",
        "Sameer", "Sameer", "Priya", "Priya"
    ],
    "Connected_To": [
        "Amit", "Sameer", "Sameer", "Priya",
        "Priya", "Rahul", "Rahul", "Amit"
    ],
    "Location": [
        "Mumbai", "Pune", "Mumbai", "Delhi",
        "Pune", "Mumbai", "Delhi", "Pune"
    ]
}

df = pd.DataFrame(data)

G = nx.Graph()

for _, row in df.iterrows():
    G.add_edge(row["Person"], row["Connected_To"])

centrality = nx.degree_centrality(G)

people = len(G.nodes())
connections = len(G.edges())
locations = df["Location"].nunique()

alerts = sum(
    1 for value in centrality.values()
    if value >= 0.6
)

fir_records = 24

st.sidebar.markdown(
    '<div class="brand"><span>CNIS</span> Intelligence</div>',
    unsafe_allow_html=True
)

st.sidebar.markdown(
    '<div class="nav-title">INVESTIGATION</div>',
    unsafe_allow_html=True
)

pages = [
    "Dashboard",
    "FIR Registration",
    "Network Analysis",
    "Suspicious Activity",
    "Persons and Witnesses",
    "Analytics"
]

page = st.sidebar.radio(
    "Navigation",
    pages,
    label_visibility="collapsed"
)

st.markdown("""
<div class="header">
    <h1>Criminal Network Intelligence System</h1>
    <p>FIR Management, Network Analysis and Suspicious Activity Intelligence</p>
</div>
""", unsafe_allow_html=True)

if page == "Dashboard":

    st.markdown(
        '<div class="section-title">Investigation Dashboard</div>',
        unsafe_allow_html=True
    )

    st.markdown('<div class="filter-card">', unsafe_allow_html=True)

    f1, f2, f3, f4 = st.columns(4)

    with f1:
        selected_state = st.selectbox(
            "State",
            ["All States", "Maharashtra", "Delhi", "Karnataka"]
        )

    with f2:
        selected_district = st.selectbox(
            "District",
            ["All Districts", "Mumbai", "Pune", "Delhi"]
        )

    with f3:
        selected_case = st.selectbox(
            "Case Status",
            ["All Cases", "Open", "Under Investigation", "Closed"]
        )

    with f4:
        selected_level = st.selectbox(
            "Risk Level",
            ["All Levels", "High", "Medium", "Low"]
        )

    st.markdown('</div>', unsafe_allow_html=True)

    m1, m2, m3, m4, m5 = st.columns(5)

    with m1:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-title">FIR RECORDS</div>
            <div class="metric-value">24</div>
            <div class="metric-sub">Registered cases</div>
        </div>
        """, unsafe_allow_html=True)

    with m2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">PERSONS</div>
            <div class="metric-value">{people}</div>
            <div class="metric-sub">Identified entities</div>
        </div>
        """, unsafe_allow_html=True)

    with m3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">CONNECTIONS</div>
            <div class="metric-value">{connections}</div>
            <div class="metric-sub">Observed relationships</div>
        </div>
        """, unsafe_allow_html=True)

    with m4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">LOCATIONS</div>
            <div class="metric-value">{locations}</div>
            <div class="metric-sub">Associated locations</div>
        </div>
        """, unsafe_allow_html=True)

    with m5:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">ALERTS</div>
            <div class="metric-value">{alerts}</div>
            <div class="metric-sub">Requires verification</div>
        </div>
        """, unsafe_allow_html=True)

    st.write("")

    left, middle, right = st.columns([1.55, 1, 1])

    with left:

        st.markdown(
            '<div class="panel-title">Network Overview</div>',
            unsafe_allow_html=True
        )

        pos = nx.spring_layout(G, seed=42)

        edge_x = []
        edge_y = []

        for edge in G.edges():

            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]

            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

        edge_trace = go.Scatter(
            x=edge_x,
            y=edge_y,
            mode="lines",
            hoverinfo="none",
            line=dict(
                width=1.5,
                color="#d6d7e3"
            )
        )

        node_x = []
        node_y = []
        node_text = []

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
                color="#7568df",
                line=dict(
                    width=3,
                    color="#ffffff"
                )
            ),
            textfont=dict(
                size=11,
                color="#44465e"
            )
        )

        fig = go.Figure(
            data=[edge_trace, node_trace]
        )

        fig.update_layout(
            height=390,
            margin=dict(l=10, r=10, t=10, b=10),
            showlegend=False,
            paper_bgcolor="white",
            plot_bgcolor="white",
            xaxis=dict(
                showgrid=False,
                zeroline=False,
                showticklabels=False
            ),
            yaxis=dict(
                showgrid=False,
                zeroline=False,
                showticklabels=False
            )
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            config={"displayModeBar": False}
        )

    with middle:

        st.markdown(
            '<div class="panel-title">Risk Distribution</div>',
            unsafe_allow_html=True
        )

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
                    textfont=dict(size=11),
                    marker=dict(
                        colors=[
                            "#6656d9",
                            "#9b8de8",
                            "#d7d3f5"
                        ]
                    )
                )
            ]
        )

        risk_fig.update_layout(
            height=350,
            margin=dict(l=10, r=10, t=10, b=10),
            showlegend=True,
            paper_bgcolor="white",
            legend=dict(
                orientation="h",
                y=-0.05
            )
        )

        st.plotly_chart(
            risk_fig,
            use_container_width=True,
            config={"displayModeBar": False}
        )

    with right:

        st.markdown(
            '<div class="panel-title">Case Status</div>',
            unsafe_allow_html=True
        )

        case_df = pd.DataFrame({
            "Status": [
                "Open",
                "Investigation",
                "Closed"
            ],
            "Cases": [
                8,
                10,
                6
            ]
        })

        case_fig = go.Figure(
            data=[
                go.Bar(
                    x=case_df["Status"],
                    y=case_df["Cases"],
                    marker=dict(
                        color="#7465df",
                        line=dict(width=0)
                    )
                )
            ]
        )

        case_fig.update_layout(
            height=350,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="white",
            plot_bgcolor="white",
            yaxis=dict(
                showgrid=True,
                gridcolor="#eeeeF4",
                title=""
            ),
            xaxis=dict(
                title=""
            )
        )

        st.plotly_chart(
            case_fig,
            use_container_width=True,
            config={"displayModeBar": False}
        )

    st.write("")

    bottom_left, bottom_right = st.columns([1.5, 1])

    with bottom_left:

        st.markdown(
            '<div class="panel-title">Key Individuals</div>',
            unsafe_allow_html=True
        )

        ranking = sorted(
            centrality.items(),
            key=lambda x: x[1],
            reverse=True
        )

        result = pd.DataFrame(
            ranking,
            columns=[
                "Entity",
                "Centrality Score"
            ]
        )

        result["Connections"] = result["Entity"].apply(
            lambda x: G.degree(x)
        )

        result["Network Role"] = result["Centrality Score"].apply(
            lambda x:
            "High Connectivity"
            if x >= 0.6
            else "Moderate Connectivity"
        )

        st.dataframe(
            result,
            use_container_width=True,
            hide_index=True
        )

    with bottom_right:

        st.markdown(
            '<div class="panel-title">Recent Alerts</div>',
            unsafe_allow_html=True
        )

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


elif page == "FIR Registration":

    st.markdown(
        '<div class="section-title">FIR / Case Registration</div>',
        unsafe_allow_html=True
    )

    st.markdown("""
    <div class="info-box">
    Enter case information below. For academic demonstrations, use fictional or sample identity information.
    </div>
    """, unsafe_allow_html=True)

    st.write("")

    st.subheader("1. Primary Details")

    c1, c2, c3 = st.columns(3)

    with c1:
        district = st.text_input(
            "District *",
            placeholder="Example: Mumbai"
        )

    with c2:
        police_station = st.text_input(
            "Police Station *",
            placeholder="Example: Andheri Police Station"
        )

    with c3:
        state = st.text_input(
            "State *",
            placeholder="Example: Maharashtra"
        )

    c1, c2 = st.columns(2)

    with c1:
        fir_number = st.text_input(
            "FIR Number *",
            placeholder="Example: FIR No. 0123/2026"
        )

    with c2:
        reporting_datetime = st.datetime_input(
            "Date and Time of Reporting",
            value=datetime.now()
        )

    gd_reference = st.text_input(
        "GD Entry Reference",
        placeholder="GD Entry Number / Date / Time"
    )

    st.divider()

    st.subheader("2. Details of the Incident")

    c1, c2 = st.columns(2)

    with c1:
        occurrence_date = st.date_input(
            "Date of Occurrence",
            value=date.today()
        )

    with c2:
        occurrence_time = st.time_input(
            "Time of Occurrence",
            value=time(12, 0)
        )

    occurrence_place = st.text_area(
        "Place of Occurrence",
        placeholder="Enter exact location, distance and direction from the police station"
    )

    delay_reporting = st.radio(
        "Was there a delay in reporting?",
        ["No", "Yes"],
        horizontal=True
    )

    delay_reason = ""

    if delay_reporting == "Yes":
        delay_reason = st.text_area(
            "Reason for Delay",
            placeholder="Explain the reason for delayed reporting"
        )

    st.divider()

    st.subheader("3. Complainant / Informant")

    c1, c2, c3 = st.columns(3)

    with c1:
        complainant_name = st.text_input(
            "Name *"
        )

    with c2:
        complainant_age = st.number_input(
            "Age",
            min_value=0,
            max_value=120,
            value=18
        )

    with c3:
        complainant_gender = st.selectbox(
            "Gender",
            ["Select", "Male", "Female", "Other"]
        )

    c1, c2 = st.columns(2)

    with c1:
        father_husband_name = st.text_input(
            "Father's / Husband's Name"
        )

    with c2:
        occupation = st.text_input(
            "Occupation"
        )

    permanent_address = st.text_area(
        "Permanent Address"
    )

    temporary_address = st.text_area(
        "Temporary Address"
    )

    contact = st.text_input(
        "Contact Number"
    )

    identity_number = st.text_input(
        "Aadhaar / Passport Number (Optional)",
        type="password",
        help="Use fictional information for demonstrations."
    )

    st.divider()

    st.subheader("4. Accused Details")

    accused_known = st.radio(
        "Is the accused known?",
        ["Known", "Unknown"],
        horizontal=True
    )

    accused_name = ""
    accused_description = ""
    accused_address = ""

    if accused_known == "Known":

        accused_name = st.text_input(
            "Accused Name"
        )

        accused_description = st.text_area(
            "Physical Description / Identifying Marks"
        )

        accused_address = st.text_area(
            "Accused Address"
        )

    else:

        st.info(
            'The accused will be recorded as "Unknown Person(s)".'
        )

        accused_description = st.text_area(
            "Available Description of Unknown Person(s)"
        )

    st.divider()

    st.subheader("5. Witness Information")

    witness_count = st.number_input(
        "Number of Witnesses",
        min_value=0,
        max_value=20,
        value=0
    )

    witnesses = []

    for i in range(int(witness_count)):

        st.markdown(
            f"**Witness {i + 1}**"
        )

        c1, c2 = st.columns(2)

        with c1:
            witness_name = st.text_input(
                f"Witness {i + 1} Name",
                key=f"witness_name_{i}"
            )

        with c2:
            witness_address = st.text_input(
                f"Witness {i + 1} Address",
                key=f"witness_address_{i}"
            )

        witnesses.append({
            "name": witness_name,
            "address": witness_address
        })

    st.divider()

    st.subheader("6. Description of the Crime")

    narrative = st.text_area(
        "Narrative / Statement",
        height=250,
        placeholder="Enter a detailed chronological description of the incident."
    )

    st.markdown("""
    <div class="info-box">
    The AI engine can analyze this narrative using NLP to identify people, locations, vehicles, organizations, dates and relationships.
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    st.subheader("7. Property / Stolen Goods")

    property_applicable = st.checkbox(
        "Does this case involve stolen or damaged property?"
    )

    property_name = ""
    property_description = ""
    property_value = 0.0
    imei = ""

    if property_applicable:

        c1, c2 = st.columns(2)

        with c1:
            property_name = st.text_input(
                "Property / Item Name"
            )

        with c2:
            property_value = st.number_input(
                "Estimated Value (₹)",
                min_value=0.0,
                value=0.0
            )

        property_description = st.text_area(
            "Property Description"
        )

        imei = st.text_input(
            "IMEI / Serial Number"
        )

    st.divider()

    st.subheader("8. Particulars of Offense")

    offense_sections = st.text_input(
        "Applicable BNS Section(s)",
        placeholder="Example: BNS Section 303"
    )

    offense_description = st.text_area(
        "Offense Description"
    )

    st.divider()

    st.subheader("9. Investigating Officer")

    c1, c2, c3 = st.columns(3)

    with c1:
        io_name = st.text_input(
            "IO Name"
        )

    with c2:
        io_rank = st.text_input(
            "IO Rank"
        )

    with c3:
        io_id = st.text_input(
            "Officer ID"
        )

    st.divider()

    st.subheader("10. Verification and Closing Details")

    complainant_signature = st.checkbox(
        "Complainant / Informant Signature or Thumb Impression Received"
    )

    officer_signature = st.checkbox(
        "Officer-in-Charge Signature / Verification Completed"
    )

    st.write("")

    if st.button(
        "Register FIR",
        type="primary",
        use_container_width=True
    ):

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

            st.success(
                f"FIR {fir_number} registered successfully."
            )

            st.info(
                "The case is ready for AI-assisted entity extraction and network analysis."
            )


elif page == "Network Analysis":

    st.markdown(
        '<div class="section-title">Criminal Network Analysis</div>',
        unsafe_allow_html=True
    )

    st.markdown("""
    <div class="info-box">
    Explore relationships between people and entities identified from case records.
    </div>
    """, unsafe_allow_html=True)

    st.write("")

    selected_person = st.selectbox(
        "Select Entity",
        list(G.nodes())
    )

    neighbors = list(G.neighbors(selected_person))

    st.markdown(
        f'<div class="panel-title">Connections of {selected_person}</div>',
        unsafe_allow_html=True
    )

    if neighbors:

        connection_df = pd.DataFrame({
            "Connected Entity": neighbors,
            "Relationship Type": [
                "Observed association"
                for _ in neighbors
            ],
            "Location": [
                df[
                    (
                        (df["Person"] == selected_person) &
                        (df["Connected_To"] == person)
                    ) |
                    (
                        (df["Connected_To"] == selected_person) &
                        (df["Person"] == person)
                    )
                ]["Location"].iloc[0]
                if not df[
                    (
                        (df["Person"] == selected_person) &
                        (df["Connected_To"] == person)
                    ) |
                    (
                        (df["Connected_To"] == selected_person) &
                        (df["Person"] == person)
                    )
                ].empty else "Unknown"
                for person in neighbors
            ]
        })

        st.dataframe(
            connection_df,
            use_container_width=True,
            hide_index=True
        )

    else:
        st.info("No direct connections found.")

    st.write("")

    pos = nx.spring_layout(G, seed=42)

    edge_x = []
    edge_y = []

    for edge in G.edges():

        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]

        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        mode="lines",
        hoverinfo="none",
        line=dict(
            width=2,
            color="#d1d2df"
        )
    )

    node_x = []
    node_y = []

    for node in G.nodes():

        x, y = pos[node]

        node_x.append(x)
        node_y.append(y)

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=list(G.nodes()),
        textposition="top center",
        marker=dict(
            size=30,
            color="#7061dc",
            line=dict(
                width=3,
                color="#ffffff"
            )
        )
    )

    fig = go.Figure(
        data=[edge_trace, node_trace]
    )

    fig.update_layout(
        height=600,
        showlegend=False,
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False
        ),
        yaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False
        )
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={"displayModeBar": False}
    )


elif page == "Suspicious Activity":

    st.markdown(
        '<div class="section-title">Suspicious Activity Detection</div>',
        unsafe_allow_html=True
    )

    st.markdown("""
    <div class="info-box">
    AI-assisted identification of unusual patterns and network indicators.
    </div>
    """, unsafe_allow_html=True)

    st.write("")

    alerts_data = pd.DataFrame({
        "Alert ID": [
            "ALT-001",
            "ALT-002",
            "ALT-003",
            "ALT-004"
        ],
        "Entity": [
            "Amit",
            "Rahul",
            "Sameer",
            "Phone-9876"
        ],
        "Pattern": [
            "High network connectivity",
            "Multiple locations",
            "Potential intermediary",
            "Multiple person association"
        ],
        "Risk Level": [
            "High",
            "Medium",
            "Medium",
            "High"
        ],
        "Status": [
            "Requires Review",
            "Requires Review",
            "Under Analysis",
            "Requires Review"
        ]
    })

    st.dataframe(
        alerts_data,
        use_container_width=True,
        hide_index=True
    )

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


elif page == "Persons and Witnesses":

    st.markdown(
        '<div class="section-title">Persons and Witnesses</div>',
        unsafe_allow_html=True
    )

    tabs = st.tabs([
        "Persons",
        "Witnesses",
        "Entities"
    ])

    with tabs[0]:

        persons_data = pd.DataFrame({
            "Name": [
                "Rahul",
                "Amit",
                "Sameer",
                "Priya"
            ],
            "Role": [
                "Person of Interest",
                "Person of Interest",
                "Person of Interest",
                "Witness"
            ],
            "Connections": [
                2,
                3,
                3,
                2
            ],
            "Locations": [
                "Mumbai, Pune",
                "Mumbai, Delhi",
                "Pune, Mumbai",
                "Delhi"
            ]
        })

        st.dataframe(
            persons_data,
            use_container_width=True,
            hide_index=True
        )

    with tabs[1]:

        witness_data = pd.DataFrame({
            "Witness": [
                "Witness A",
                "Witness B",
                "Witness C"
            ],
            "Location": [
                "Mumbai",
                "Pune",
                "Delhi"
            ],
            "Statement Status": [
                "Recorded",
                "Pending",
                "Recorded"
            ]
        })

        st.dataframe(
            witness_data,
            use_container_width=True,
            hide_index=True
        )

    with tabs[2]:

        entities = pd.DataFrame({
            "Entity Type": [
                "Person",
                "Phone",
                "Vehicle",
                "Location",
                "Organization"
            ],
            "Count": [
                24,
                15,
                8,
                12,
                5
            ]
        })

        st.dataframe(
            entities,
            use_container_width=True,
            hide_index=True
        )


elif page == "Analytics":

    st.markdown(
        '<div class="section-title">Network Analytics</div>',
        unsafe_allow_html=True
    )

    c1, c2 = st.columns(2)

    with c1:

        st.markdown(
            '<div class="panel-title">Degree Centrality</div>',
            unsafe_allow_html=True
        )

        centrality_df = pd.DataFrame(
            centrality.items(),
            columns=[
                "Person",
                "Centrality"
            ]
        )

        centrality_df = centrality_df.sort_values(
            "Centrality",
            ascending=False
        )

        fig = go.Figure(
            data=[
                go.Bar(
                    x=centrality_df["Person"],
                    y=centrality_df["Centrality"],
                    marker=dict(
                        color="#7465df"
                    )
                )
            ]
        )

        fig.update_layout(
            height=400,
            paper_bgcolor="white",
            plot_bgcolor="white",
            yaxis_title="Centrality Score",
            xaxis_title="Person",
            margin=dict(l=30, r=20, t=20, b=30)
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            config={"displayModeBar": False}
        )

    with c2:

        st.markdown(
            '<div class="panel-title">Location Distribution</div>',
            unsafe_allow_html=True
        )

        location_count = (
            df["Location"]
            .value_counts()
            .reset_index()
        )

        location_count.columns = [
            "Location",
            "Count"
        ]

        fig2 = go.Figure(
            data=[
                go.Pie(
                    labels=location_count["Location"],
                    values=location_count["Count"],
                    hole=0.55,
                    marker=dict(
                        colors=[
                            "#6656d9",
                            "#9185e4",
                            "#bbb5ed"
                        ]
                    )
                )
            ]
        )

        fig2.update_layout(
            height=400,
            paper_bgcolor="white",
            margin=dict(l=20, r=20, t=20, b=20)
        )

        st.plotly_chart(
            fig2,
            use_container_width=True,
            config={"displayModeBar": False}
        )

    st.write("")

    st.markdown(
        '<div class="panel-title">Source Data</div>',
        unsafe_allow_html=True
    )

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )

st.divider()

st.caption(
    "Prototype for academic and hackathon purposes. AI-generated insights are decision-support information and do not establish criminal guilt."
)
