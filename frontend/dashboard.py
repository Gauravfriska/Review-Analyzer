import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime, timedelta, date

# --- SETUP ---
st.set_page_config(layout="wide", page_title="Review Trend Agent")
API_URL = "http://localhost:8000"

# --- CUSTOM CSS ---
st.markdown("""
<style>
    .metric-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        text-align: center;
        border-top: 4px solid #FF4B4B;
    }
    .metric-value {
        font-size: 28px;
        font-weight: bold;
        color: #333;
    }
    .metric-label {
        font-size: 14px;
        color: #666;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
    }
    /* New Style for the App Link in Sidebar */
    .app-link {
        display: block;
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 8px;
        text-align: center;
        color: #333 !important;
        text-decoration: none;
        border: 1px solid #dcdcdc;
        margin-top: 10px;
        transition: all 0.3s ease;
    }
    .app-link:hover {
        background-color: #e0e2e6;
        border-color: #bbb;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# --- HELPER FUNCTIONS ---
def get_source_date_limits():
    """Fetch the min and max available dates from the raw source file via API"""
    try:
        resp = requests.get(f"{API_URL}/raw-date-range")
        if resp.status_code == 200:
            data = resp.json()
            if data["min_date"] and data["max_date"]:
                return (
                    datetime.strptime(data["min_date"], "%Y-%m-%d").date(),
                    datetime.strptime(data["max_date"], "%Y-%m-%d").date()
                )
    except Exception as e:
        st.error(f"Could not connect to backend to fetch dates: {e}")
    # Fallback default
    return date.today(), date.today()

# --- SIDEBAR ---
with st.sidebar:
    st.header("💬 Agent Chat")
    
    # 1. Chat Interface
    user_query = st.text_area("Ask the agent about trends:", height=100)
    if st.button("Ask Agent"):
        if user_query:
            with st.spinner("Thinking..."):
                try:
                    res = requests.post(f"{API_URL}/chat", json={"message": user_query})
                    if res.status_code == 200:
                        st.success(res.json()["response"])
                    else:
                        st.error("Error from agent.")
                except:
                    st.error("Connection failed.")

    st.markdown("---")
    st.header("📅 Simulation Controls")
    
    # 2. Dynamic Date Picker
    min_avail_date, max_avail_date = get_source_date_limits()
    
    if min_avail_date == max_avail_date:
        selected_date = st.date_input("Pick a Date to Process", value=min_avail_date)
    else:
        selected_date = st.date_input(
            "Pick a Date to Process",
            value=min_avail_date, 
            min_value=min_avail_date,
            max_value=max_avail_date
        )

    if st.button("Process this Date"):
        with st.spinner(f"Simulating incoming reviews for {selected_date}..."):
            try:
                date_str = selected_date.strftime("%Y-%m-%d")
                res = requests.get(f"{API_URL}/simulate-day", params={"date": date_str})
                
                if res.status_code == 200:
                    data = res.json()
                    if data["status"] == "success":
                        st.toast(f"✅ Processed {data['reviews_processed_in_batch']} reviews!", icon="🚀")
                    elif data["status"] == "empty":
                        st.warning(data["message"])
                else:
                    st.error("Failed to process day.")
            except Exception as e:
                st.error(f"Connection Error: {e}")

    # --- NEW APP LINK SECTION ---
    st.markdown("---")
    st.header("🔗 Resources")
    
    st.markdown(
        """
        <a href="https://play.google.com/store/apps/details?id=in.swiggy.android" target="_blank" class="app-link">
            <div style="font-size: 1.2em;">📲 <strong>Open Swiggy App</strong></div>
            <div style="font-size: 0.8em; margin-top: 4px;">Google Play Store</div>
        </a>
        """, 
        unsafe_allow_html=True
    )

# --- MAIN DASHBOARD ---
st.title("📈 AI Customer Review Intelligence")

# Fetch Trend Data
try:
    resp = requests.get(f"{API_URL}/trends")
    if resp.status_code == 200:
        trends_data = resp.json()
        df_trends = pd.DataFrame(trends_data)
        if not df_trends.empty:
            df_trends = df_trends.set_index("Topic")
    else:
        df_trends = pd.DataFrame()
except:
    df_trends = pd.DataFrame()

# Main Layout
if not df_trends.empty:
    
    # Top Metrics
    total_reviews = df_trends.sum().sum()
    active_topics = len(df_trends.index)
    latest_date = df_trends.columns[-1]

    col1, col2, col3 = st.columns(3)
    col1.markdown(f"""<div class="metric-card"><div class="metric-value">{total_reviews}</div><div class="metric-label">Total Processed Reviews</div></div>""", unsafe_allow_html=True)
    col2.markdown(f"""<div class="metric-card"><div class="metric-value">{active_topics}</div><div class="metric-label">Active Issue Topics</div></div>""", unsafe_allow_html=True)
    col3.markdown(f"""<div class="metric-card"><div class="metric-value">{latest_date}</div><div class="metric-label">Latest Data Point</div></div>""", unsafe_allow_html=True)

    st.markdown("### Trend Visualization")
    
    tab1, tab2 = st.tabs(["📊 Charts", "📋 Raw Data Matrix"])
    
    with tab1:
        graph_type = st.radio("Select View:", ["📈 Line Chart", "📊 Bar Chart", "🔥 Heatmap"], horizontal=True)
        
        filtered_trends = df_trends
        
        if graph_type == "📈 Line Chart":
            st.markdown("**Topic Trends Over Time**")
            st.line_chart(filtered_trends.T, height=400)
            
        elif graph_type == "📊 Bar Chart":
            st.markdown("**Total Issues Distribution**")
            totals = filtered_trends.sum(axis=1).sort_values(ascending=True)
            st.bar_chart(totals, height=400)
            
        elif graph_type == "🔥 Heatmap":
            st.markdown("**Intensity Heatmap (Topic vs Date)**")
            try:
                fig = px.imshow(filtered_trends, 
                                labels=dict(x="Date", y="Topic", color="Count"),
                                x=filtered_trends.columns,
                                y=filtered_trends.index,
                                aspect="auto",
                                color_continuous_scale="Reds")
                st.plotly_chart(fig, use_container_width=True)
            except ImportError:
                st.warning("Plotly is required for Heatmaps.")
                st.dataframe(filtered_trends.style.background_gradient(cmap="Reds", axis=1))

    with tab2:
        st.dataframe(filtered_trends, use_container_width=True)

else:
    st.info("No history data available yet. Use the sidebar to simulate (process) a date from your batch file.")