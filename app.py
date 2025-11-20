import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import random
import io
from streamlit_autorefresh import st_autorefresh


PRIMARY = "#00897B"
ACCENT = "#004D40"
BG = "#F4F6F6"
CARD_BG = "#FFFFFF"


st.set_page_config(page_title="Simple Stream Dashboard", page_icon="📡", layout="wide")


st.markdown(f"""
<style>
   :root {{ --primary: {PRIMARY}; --accent: {ACCENT}; --bg: {BG}; --card: {CARD_BG}; }}
   body {{ background-color: var(--bg); }}
   .stApp {{ background-color: var(--bg); }}
   .block-container {{ padding-top: 1rem; }}
   .stSidebar {{ background-color: var(--card); box-shadow: 0 2px 6px rgba(0,0,0,0.06); border-radius: 8px; }}
   .stButton>button {{ background-color: var(--primary); color: white; border-radius: 6px; }}
   .stMetricValue {{ color: var(--accent) !important; }}
   .stHeader {{ color: var(--primary); }}
</style>
""", unsafe_allow_html=True)




def generate_live_rows(n=20, start_time=None):
   if start_time is None:
       start_time = datetime.now()
   rows = []
   base = 100.0
   for i in range(n):
       t = start_time - timedelta(seconds=(n - i) * 2)
       rows.append({
           "timestamp": t,
           "sensor_id": f"sensor_{random.randint(1,4)}",
           "metric_type": random.choice(["temperature", "humidity"]),
           "value": round(base + random.uniform(-5, 5) + i * 0.1, 2)
       })
   return pd.DataFrame(rows)




def parse_uploaded_csv(uploaded_file):
   try:
       df = pd.read_csv(uploaded_file)
       if "timestamp" in df.columns:
           df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
       return df
   except Exception:
       return None




def format_df_for_plot(df):
   df2 = df.copy()
   if "timestamp" in df2.columns:
       df2 = df2.sort_values("timestamp")
   return df2




st.sidebar.title("Controls")
mode = st.sidebar.selectbox("Mode", ["Live (simulated)", "Upload CSV", "Sample data"])
auto_refresh = st.sidebar.checkbox("Auto-refresh (Live)", value=True)
refresh_interval = st.sidebar.slider("Refresh interval (seconds)", 2, 30, 5)
refresh_trigger = st_autorefresh(interval=refresh_interval * 1000, key="auto_refresh_counter")
show_table = st.sidebar.checkbox("Show raw table", value=False)
download_btn = st.sidebar.button("Download current data (CSV)")


st.sidebar.markdown("---")
st.sidebar.subheader("Filters")
metric_filter = st.sidebar.multiselect("Metric Type", ["temperature", "humidity"], default=["temperature","humidity"])
sensor_filter = st.sidebar.multiselect("Sensor ID", ["sensor_1","sensor_2","sensor_3","sensor_4"], default=[])


data_df = pd.DataFrame()


if mode == "Sample data":
   data_df = generate_live_rows(200, start_time=datetime.now())


elif mode == "Upload CSV":
   uploaded = st.sidebar.file_uploader("Upload CSV with at least 'timestamp' and 'value' columns", type=["csv"])
   if uploaded is not None:
       parsed = parse_uploaded_csv(uploaded)
       if parsed is None:
           st.sidebar.error("Failed to parse CSV.")
       else:
           data_df = parsed
   else:
       st.sidebar.info("No file uploaded.")


elif mode == "Live (simulated)":
   if "live_buffer" not in st.session_state:
       st.session_state.live_buffer = generate_live_rows(60)
       st.session_state.last_live_time = datetime.now()
   if auto_refresh:
       new_rows = generate_live_rows(5, start_time=datetime.now())
       st.session_state.live_buffer = pd.concat([st.session_state.live_buffer, new_rows], ignore_index=True)
       st.session_state.live_buffer = st.session_state.live_buffer.tail(500).reset_index(drop=True)
   data_df = st.session_state.live_buffer.copy()


if not data_df.empty:
   if "metric_type" in data_df.columns and metric_filter:
       data_df = data_df[data_df["metric_type"].isin(metric_filter)]
   if sensor_filter:
       if "sensor_id" in data_df.columns:
           data_df = data_df[data_df["sensor_id"].isin(sensor_filter)]


st.title("📡 Simple Streaming Dashboard")
col1, col2 = st.columns([3,1])


with col1:
   st.subheader("Trend")
   if data_df.empty:
       st.info("No data available.")
   else:
       chart_container = st.empty()


       df_plot = format_df_for_plot(data_df)


       if "metric_type" in df_plot.columns:
           df_plot["metric_type"] = df_plot["metric_type"].fillna("unknown")
       else:
           df_plot["metric_type"] = "unknown"


       if "timestamp" in df_plot.columns:
           fig = px.line(
               df_plot,
               x="timestamp",
               y="value",
               color="metric_type",
               color_discrete_sequence=[PRIMARY, ACCENT]
           )
       else:
           fig = px.line(
               df_plot.reset_index(),
               x="index",
               y="value",
               color="metric_type",
               color_discrete_sequence=[PRIMARY, ACCENT]
           )


       fig.update_layout(margin=dict(t=30, l=10, r=10, b=10))
       chart_container.plotly_chart(fig, use_container_width=True)


   with st.expander("Quick stats"):
       if data_df.empty:
           st.write("-")
       else:
           avg = data_df["value"].mean()
           mn = data_df["value"].min()
           mx = data_df["value"].max()
           st.metric("Average value", f"{avg:.2f}")
           st.metric("Min value", f"{mn:.2f}")
           st.metric("Max value", f"{mx:.2f}")


with col2:
   st.subheader("Controls & Info")
   st.markdown(f"- Mode: **{mode}**")
   st.markdown(f"- Rows: **{len(data_df)}**")
   if "timestamp" in data_df.columns:
       last_ts = data_df["timestamp"].max()
       if pd.isna(last_ts):
           st.markdown("- Last timestamp: N/A")
       else:
           clean_ts = pd.to_datetime(last_ts).strftime("%Y-%m-%d %H:%M:%S")
           st.markdown(f"- Last timestamp: **{clean_ts}**")
   st.markdown("---")


if show_table and not data_df.empty:
   st.subheader("Raw data (latest first)")
   display_df = data_df.sort_values("timestamp", ascending=False) if "timestamp" in data_df.columns else data_df
   if "timestamp" in display_df.columns:
       display_df = display_df.assign(timestamp=display_df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S"))
   st.dataframe(display_df.reset_index(drop=True), height=350)


if download_btn and not data_df.empty:
   to_download = data_df.copy()
   if "timestamp" in to_download.columns:
       to_download["timestamp"] = to_download["timestamp"].astype(str)
   csv_buf = to_download.to_csv(index=False).encode("utf-8")
   st.download_button("Download CSV", data=csv_buf, file_name="export.csv", mime="text/csv")





