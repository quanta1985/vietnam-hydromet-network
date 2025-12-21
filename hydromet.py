import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster, Fullscreen, MiniMap, Draw
import os
import glob

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(
    page_title="Vietnam Hydromet Monitoring System",
    layout="wide",
    page_icon="🌐"
)

# --------------------------------------------------
# STYLE
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
.footer {
    position: fixed;
    bottom: 0;
    width: 100%;
    background-color: #f8f9fa;
    font-size: 11px;
    text-align: center;
    border-top: 1px solid #e1e8ed;
}
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# DATA
# --------------------------------------------------
@st.cache_data
def load_data():

    def find(patterns):
        for p in patterns:
            for d in [".", "data"]:
                m = glob.glob(os.path.join(d, p))
                if m:
                    return m[0]
        return None

    def read(p):
        f = find([f"*{p}*.xlsx", f"*{p}*.csv"])
        if not f:
            return pd.DataFrame()
        return pd.read_csv(f) if f.endswith(".csv") else pd.read_excel(f)

    met = read("meteorology").rename(columns={"STATIONS":"name","LAT":"lat","LON":"lon"})
    water = read("water quality").rename(columns={"STATIONS":"name","LAT":"lat","LON":"lon"})
    hydro = read("hydrology").rename(columns={"STATIONS":"name","LAT":"lat","LON":"lon"})

    for df in [met, water, hydro]:
        if not df.empty:
            df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
            df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
            df.dropna(subset=["lat","lon"], inplace=True)

    return met, water, hydro

met_df, water_df, hydro_df = load_data()

# --------------------------------------------------
# SESSION STATE (CRITICAL FIX)
# --------------------------------------------------
if "map_center" not in st.session_state:
    st.session_state.map_center = [16.46, 107.59]
if "map_zoom" not in st.session_state:
    st.session_state.map_zoom = 6

# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------
st.sidebar.title("🛠 System Control")

basemap = st.sidebar.selectbox(
    "Basemap",
    ["Light", "Dark", "Satellite", "Terrain"]
)

tiles = {
    "Light": "cartodbpositron",
    "Dark": "cartodbdark_matter",
    "Satellite": "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
    "Terrain": "https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}",
}

disable_cluster = st.sidebar.checkbox("Disable clustering")
show_names = st.sidebar.checkbox("Show station names")

marker_size = st.sidebar.slider("Marker size", 6, 16, 10)
marker_style = st.sidebar.selectbox(
    "Marker style",
    ["Circle filled", "Circle outline", "Minimal dot"]
)

st.sidebar.divider()
show_met = st.sidebar.toggle("Meteorology", True)
show_water = st.sidebar.toggle("Water quality", True)
show_hydro = st.sidebar.toggle("Hydrology", True)

radius_on = False
if show_met:
    radius_on = st.sidebar.checkbox("Show coverage radius")
    if radius_on:
        radius_km = st.sidebar.slider("Radius (km)", 10, 150, 30)
        radius_color = st.sidebar.color_picker("Radius color", "#5dade2")

# --------------------------------------------------
# MAP (PERSISTENT VIEW)
# --------------------------------------------------
m = folium.Map(
    location=st.session_state.map_center,
    zoom_start=st.session_state.map_zoom,
    tiles=tiles[basemap],
    attr="Google" if basemap in ["Satellite","Terrain"] else None
)

MiniMap(toggle_display=True).add_to(m)
Fullscreen().add_to(m)
Draw(export=True).add_to(m)

def plot(df, color, label):
    if df.empty:
        return

    container = m if disable_cluster else MarkerCluster(name=label).add_to(m)

    for _, r in df.iterrows():

        if radius_on and label == "Meteorology":
            folium.Circle(
                [r.lat, r.lon],
                radius=radius_km * 1000,
                fill=True,
                fill_color=radius_color,
                fill_opacity=0.07,   # VERY LOW → no visible overlap
                color=None,          # NO BORDER
                stroke=False
            ).add_to(m)

        if marker_style == "Circle filled":
            folium.CircleMarker(
                [r.lat, r.lon],
                radius=marker_size,
                fill=True,
                fill_color=color,
                fill_opacity=0.85,
                color=None,
                popup=r.name,
                tooltip=r.name if show_names else None
            ).add_to(container)

        elif marker_style == "Circle outline":
            folium.CircleMarker(
                [r.lat, r.lon],
                radius=marker_size,
                fill=False,
                color=color,
                weight=2,
                popup=r.name,
                tooltip=r.name if show_names else None
            ).add_to(container)

        else:
            folium.CircleMarker(
                [r.lat, r.lon],
                radius=marker_size // 2,
                fill=True,
                fill_color=color,
                fill_opacity=1,
                color=None,
                popup=r.name
            ).add_to(container)

if show_met:
    plot(met_df, "blue", "Meteorology")
if show_water:
    plot(water_df, "green", "Water Quality")
if show_hydro:
    plot(hydro_df, "red", "Hydrology")

# --------------------------------------------------
# RENDER + CAPTURE VIEW STATE
# --------------------------------------------------
map_data = st_folium(
    m,
    width="100%",
    height=700,
    key="main_map",
    returned_objects=["center", "zoom"]
)

if map_data.get("center"):
    st.session_state.map_center = [
        map_data["center"]["lat"],
        map_data["center"]["lng"],
    ]

if map_data.get("zoom"):
    st.session_state.map_zoom = map_data["zoom"]

# --------------------------------------------------
# FOOTER
# --------------------------------------------------
st.markdown("""
<div class="footer">
© 2024 Trần Anh Quân – Hanoi University of Mining and Geology (HUMG)
</div>
""", unsafe_allow_html=True)
