elif page == "Timeline & Event Correlation":

    st.markdown(
        '<div class="section-title">Timeline & Event Correlation</div>',
        unsafe_allow_html=True
    )

    st.markdown("""
    <div class="info-box">
    Reconstruct the chronological sequence of investigation events
    from FIR records, calls, transactions, locations and meetings.
    </div>
    """, unsafe_allow_html=True)

    st.write("")

    # Investigation events
    timeline_data = pd.DataFrame({
        "Date": [
            "2026-08-20",
            "2026-08-20",
            "2026-08-20",
            "2026-08-20",
            "2026-08-20",
            "2026-08-21"
        ],
        "Time": [
            "10:00",
            "10:25",
            "10:45",
            "11:30",
            "12:15",
            "09:30"
        ],
        "Event Type": [
            "FIR",
            "Call",
            "Location",
            "Transaction",
            "Meeting",
            "Call"
        ],
        "Person": [
            "Unknown",
            "Rahul",
            "Rahul",
            "Rahul",
            "Rahul",
            "Amit"
        ],
        "Location": [
            "Police Station",
            "Mumbai",
            "Station Road",
            "Mumbai",
            "City Mall",
            "Delhi"
        ],
        "Description": [
            "FIR incident reported",
            "Call between Rahul and Amit",
            "Rahul detected at Station Road",
            "Financial transaction of ₹50,000",
            "Meeting between Rahul and Amit",
            "Call recorded between Amit and Sameer"
        ],
        "Source": [
            "FIR Records",
            "Call Records",
            "Location Logs",
            "Bank Records",
            "Investigation Records",
            "Call Records"
        ]
    })
