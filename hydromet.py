import streamlit as st
import pandas as pd
import leafmap
import glob
import os

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(
    page_title="Vietnam Hydromet Monitoring System",
    layout="wide",
    page_icon="🌐"
)

# --------------------------------------------------
# CSS (KEEP LOOK & FEEL)
# --------------------------------------------------
st.markdown("""
<style>
.main { background-color: #f4f7f9; }
.stMetric {
    background-color: #ffffff;
    padding: 20px;
    border-radius: 12px;
    border: 1px solid #e1e8ed;
}
.stSidebar {
    background-color: #ffffff;
    border-right: 1px solid #dee2e6;
}
.footer {
    position: fixed;
    left: 0;
    bottom: 0;
    width: 100%;
    background-color: #f8f9fa;
    color: #6c757d;
    text-align: center;
    padding: 8px;
    font-size: 11px;
    border-top: 1px solid #e1e8ed;
}
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# DATA LOADING
# --------------------------------------------------
@st.cache_data
def load_data():

    def find_file(patterns):
        for p in patterns:
            for d in [".", "data"]:
                m = glob.glob(os.path.join(d, p))
                if m:
                    return m[0]
        return None

    def read(pattern):
        f = find_file([f"*{pattern}*.xlsx", f"*{pattern}*.csv"])
        if not f:
            return pd.DataFrame()
        return pd.read_csv(f) if f.lower().endswith(".csv") else pd.read_excel(f)

    met = read("meteorology").rename(columns={"STATIONS": "name", "LAT": "lat", "LON": "lon"})
    water = read("water quality").rename(columns={"STATIONS": "name", "LAT": "lat", "LON": "lon"})
    hydro = read("hydrology").rename(columns={"STATIONS": "name", "LAT": "lat", "LON": "lon"})

    for df in [met, water, hydro]:
        if not df.empty:
            df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
            df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
            df.dropna(subset=["lat", "lon"], inplace=True)

    return met, water, hydro


met_df, water_df, hydro_df = load_data()

# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------
st.sidebar.title("🛠 System Control")

basemap = st.sidebar.selectbox(
    "Basemap Style",
    ["Light (CartoDB)", "Dark Mode", "Satellite (Google)", "Terrain"]
)

basemap_dict = {
    "Light (CartoDB)": "CartoDB.Positron",
    "Dark Mode": "CartoDB.DarkMatter",
    "Satellite (Google)": "Google.Satellite",
    "Terrain": "Google.Terrain"
}

with st.sidebar.expander("⚙️ Display Settings", expanded=True):
    show_names = st.checkbox("Always Show Station Labels", value=False)
    marker_size = st.slider("Marker Size", 6, 16, 10)

with st.sidebar.expander("📡 Network Layers", expanded=True):
    show_met = st.toggle("Meteorology Network", value=True)
    show_water = st.toggle("Water Quality Network", value=True)
    show_hydro = st.toggle("Hydrology Network", value=True)

    met_radius_on = False
    if show_met:
        met_radius_on = st.checkbox("Enable Coverage Radius (Met Only)")
        if met_radius_on:
            met_rad_km = st.slider("Radius (km)", 5, 150, 30)

# --------------------------------------------------
# DASHBOARD
# --------------------------------------------------
st.title("Vietnam Environmental Monitoring Portal")

c1, c2, c3 = st.columns(3)
c1.metric("Meteorology Network", f"{len(met_df)} Stations")
c2.metric("Water Quality", f"{len(water_df)} Points")
c3.metric("Hydrology Network", f"{len(hydro_df)} Stations")

# --------------------------------------------------
# MAP (LEAFMAP – FAST & STABLE)
# --------------------------------------------------
m = leafmap.Map(
    center=[16.46, 107.59],
    zoom=6,
    basemap=basemap_dict[basemap],
    draw_control=True,
    fullscreen_control=True,
    minimap_control=True
)

def add_layer(df, color, name, is_met=False):
    if df.empty:
        return

    m.add_points_from_xy(
        df,
        x="lon",
        y="lat",
        popup="name",
        tooltip="name" if show_names else None,
        layer_name=name,
        color=color,
        radius=marker_size,
        fill=True
    )

    if is_met and met_radius_on:
        for _, r in df.iterrows():
            m.add_circle(
                location=(r.lat, r.lon),
                radius=met_rad_km * 1000,
                stroke=False,
                color=None,
                fill_color=color,
                fill_opacity=0.05   # shaded, no border, no harsh overlap
            )

if show_met:
    add_layer(met_df, "blue", "Meteorology", is_met=True)
if show_water:
    add_layer(water_df, "green", "Water Quality")
if show_hydro:
    add_layer(hydro_df, "red", "Hydrology")

m.add_layer_control()

# --------------------------------------------------
# DISPLAY MAP
# --------------------------------------------------
m.to_streamlit(height=700)

# --------------------------------------------------
# FOOTER
# --------------------------------------------------
st.markdown("""
<div class="footer">
© 2024 Trần Anh Quân – Hanoi University of Mining and Geology (HUMG)
</div>
""", unsafe_allow_html=True)
