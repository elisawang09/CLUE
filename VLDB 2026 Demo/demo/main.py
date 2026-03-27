import streamlit as st

st.set_page_config(layout="wide")

st.markdown(
    """
    <style>
    div.stButton > button[kind="primary"] {
        background-color: #2C3770;
        color: #ffffff;
        border: 1px solid #2C3770;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #2C3770;
        color: #ffffff;
        border: 1px solid #2C3770;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Inline row
with st.container():
    col_title, col_serach, col_button = st.columns([0.1, 0.3, 0.1])  # tiny first column to hug the title

    with col_title:
        st.title("CLUE")

    with col_serach:
        if "search_query" not in st.session_state:
            st.session_state.search_query = None

        # TODO : add more suggestions
        metric_suggestions = [
            "Page Views",
            "Paying Users",
            "Retention Rate",
            "Total Revenue",
            "Profit",
            "Purchase Frequency",
            "Product Sales",
            "PLTV",
        ]

        st.selectbox(
            "",
            options=metric_suggestions,
            index=None,
            key="search_query",
            placeholder="Search a metric (e.g., total revenue)",
        )
        
    with col_button:
        st.button("Launch Metric Simulator", key="search_btn", use_container_width=True, type="primary")
        
# Create main columns
col1, col2 = st.columns([1.0, 3])

# -------------------------
# Preview Section
# -------------------------
with col1:
    search_metric = (st.session_state.search_query or "").strip().lower()

    with st.container(border=True, height=300):
        st.subheader("Metric Overview")
        if search_metric == "pltv":
            st.write("Showing PLTV-specific controls and summary.")
            st.metric("Current PLTV", "$1,240")

    with st.container(border=True, height=300):
        st.subheader("AI-Generated Explanation")
        if search_metric == "pltv":
            st.write("Predicted Lifetime Value (PLTV) estimates how much revenue a typical customer is expected to generate over their lifetime.\
                    It is calculated using three factors: \
                    how likely a customer segment is to be active\
                    how many orders active customers usually place\
                    and the average value of each order. \
                    For example, if more customers remain active, place orders more often, or spend more per order, the PLTV increases.")

# -------------------------
# Lineage Graphs Section
# -------------------------
with col2:
    with st.container(border=True, height=300):
        st.subheader("Provenance of Metric:")
        if search_metric == "pltv":
            st.subheader("PLTV")
            st.write("Showing PLTV-specific lineage graphs.")
            
    with st.container(border=True, height=300):
        if search_metric == "pltv":
            st.subheader("Transformation")
            st.write("Showing PLTV-specific data quality issues.")