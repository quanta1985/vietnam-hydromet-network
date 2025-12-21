import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster, Fullscreen, MiniMap, Draw
import os
import glob

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Vietnam Hydromet Monitoring System", layout="wide", page_icon="🌐")

# --- CSS (Professional & Clean) ---
st.markdown("""
<style>
.main { background-color: #f4f7f9; }
.stMetric {
    background-color: #ffffff;
    padding: 20px;
    border-radius: 12px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    border: 1px solid #e1e8ed;
}
.stSidebar { background-color: #ffffff; border-right: 1px solid #dee2e6; }
.footer {
    position: fixed;
    left: 0; bottom: 0; width: 100%;
    background-color: #ffffff;
    color: #495057;
    text-align: center;
    padding: 10px;
    font-size: 12px;
    border-top: 1px solid #dee2e6;
    z-index: 1000;
    font-weight: 500;
}
</style>
""", unsafe_allow_html=True)

# --- SESSION STATE FOR PERSISTENCE ---
if "map_center" not in st.session_state:
    st.session_state.map_center = [16.46, 107.59]
if "map_zoom" not in st.session_state:
    st.session_state.map_zoom = 6

# --- DATA LOADING ---
@st.cache_data
def load_and_process_data():
    def find_file(patterns):
        for pattern in patterns:
            for d in [".", "data"]:
                matches = glob.glob(os.path.join(d, pattern))
                if matches: return matches[0]
        return None

    def read_flexible(pattern):
        path = find_file([f"*{pattern}*.xlsx", f"*{pattern}*.csv"])
        if not path: return pd.DataFrame()
        return pd.read_csv(path) if path.lower().endswith(".csv") else pd.read_excel(path)

    met = read_flexible("meteorology").rename(columns={'STATIONS':'name','LON':'lon','LAT':'lat','ALTITUDE':'altitude'})
    water = read_flexible("waterquality").rename(columns={'STATIONS':'name','LON':'lon','LAT':'lat','Province':'province'})
    hydro = read_flexible("hydrology").rename(columns={'STATIONS':'name','LON':'lon','LAT':'lat'})

    for df in [met, water, hydro]:
        if not df.empty:
            df['name'] = df['name'].astype(str).str.replace(r'\n', '', regex=True).str.strip()
            df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
            df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
            df.dropna(subset=['lat', 'lon'], inplace=True)
    return met, water, hydro

met_df, water_df, hydro_df = load_and_process_data()

# --- SIDEBAR ---
st.sidebar.title("🛠 System Control")

with st.sidebar.expander("🗺️ Map Aesthetics", expanded=True):
    basemap = st.selectbox("Basemap Style", ["Light (CartoDB)", "Satellite (Google)", "Dark Mode", "Terrain"])
    tiles_map = {
        "Light (CartoDB)": "cartodbpositron",
        "Satellite (Google)": "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
        "Dark Mode": "cartodbdark_matter",
        "Terrain": "https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}"
    }
    attr_map = {"Satellite (Google)": "Google", "Terrain": "Google"}

with st.sidebar.expander("⚙️ Station Display", expanded=True):
    # REQUEST: Defaults to True
    disable_clustering = st.checkbox("View All Stations (Disable Clustering)", value=True)
    show_names = st.checkbox("Always Show Station Labels", value=True)
    
    st.divider()
    # RESTORED: Marker customizations
    marker_size = st.slider("Marker Size", 4, 16, 8)
    marker_style = st.selectbox(
        "Marker Type",
        ["Circle (Filled)", "Circle (Clean)", "Minimal Dot", "Classic (Icon)"]
    )
    search_query = st.text_input("🔍 Search Name", "").strip().lower()

with st.sidebar.expander("📡 Network Layers", expanded=True):
    show_met = st.toggle("Meteorology Network", value=True)
    met_radius_on = False
    if show_met:
        met_radius_on = st.checkbox("Show Coverage Radius (Met Only)")
        if met_radius_on:
            met_rad_km = st.slider("Radius (km)", 5, 150, 30)
            # REQUEST: High saturation default color
            met_rad_color = st.color_picker("Radius Color", "#1a73e8")
    
    st.divider()
    show_water = st.toggle("Water Quality Network", value=True)
    show_hydro = st.toggle("Hydrology Network", value=True)

# --- MAIN DASHBOARD ---
st.title("Vietnam Environmental Monitoring Portal")
col1, col2, col3 = st.columns(3)
col1.metric("Meteorology", len(met_df))
col2.metric("Water Quality", len(water_df))
col3.metric("Hydrology", len(hydro_df))

# --- MAP INITIALIZATION ---
m = folium.Map(
    location=st.session_state.map_center,
    zoom_start=st.session_state.map_zoom,
    tiles=tiles_map[basemap],
    attr=attr_map.get(basemap, "OpenStreetMap")
)

# REQUEST: Minimap is always lightmap
MiniMap(
    tile_layer="cartodbpositron", 
    toggle_display=True, 
    width=180, height=180, 
    position='bottomright'
).add_to(m)

Fullscreen().add_to(m)
Draw(export=True, position='topleft').add_to(m)

def add_layer(df, color, icon, label, is_met=False):
    if df.empty: return
    data = df.copy()
    if search_query:
        data = data[data['name'].str.lower().str.contains(search_query)]

    container = m if disable_clustering else MarkerCluster(name=label).add_to(m)
            
    for _, row in data.iterrows():
        # REQUEST: High saturation blending (Opacity 0.35)
        if is_met and met_radius_on:
            folium.Circle(
                location=[row['lat'], row['lon']],
                radius=met_rad_km * 1000,
                color=met_rad_color,
                weight=0,
                fill=True,
                fill_color=met_rad_color,
                fill_opacity=0.35
            ).add_to(m)

        popup_html = f"<b>{row['name']}</b><br>Network: {label}"
        tooltip = row['name'] if show_names else None

        # Handle Marker Styles
        if marker_style == "Circle (Filled)":
            folium.CircleMarker(
                [row['lat'], row['lon']],
                radius=marker_size,
                popup=popup_html,
                tooltip=tooltip,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.8,
                weight=2
            ).add_to(container)
        elif marker_style == "Circle (Clean)":
            folium.CircleMarker(
                [row['lat'], row['lon']],
                radius=marker_size,
                popup=popup_html,
                tooltip=tooltip,
                color=color,
                fill=False,
                weight=2
            ).add_to(container)
        elif marker_style == "Minimal Dot":
            folium.CircleMarker(
                [row['lat'], row['lon']],
                radius=max(3, marker_size // 2),
                popup=popup_html,
                tooltip=tooltip,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=1,
                weight=0
            ).add_to(container)
        else: # Classic Icon
            folium.Marker(
                [row['lat'], row['lon']],
                popup=popup_html,
                tooltip=tooltip,
                icon=folium.Icon(color=color, icon=icon, prefix='fa')
            ).add_to(container)

if show_met: add_layer(met_df, "blue", "cloud", "Meteorology", True)
if show_water: add_layer(water_df, "green", "tint", "Water Quality")
if show_hydro: add_layer(hydro_df, "red", "water", "Hydrology")

# RENDER & CAPTURE VIEW
map_data = st_folium(
    m, width="100%", height=750, key="vn_system_final",
    returned_objects=["center", "zoom"]
)

# Persistent view logic
if map_data.get("center"):
    st.session_state.map_center = [map_data["center"]["lat"], map_data["center"]["lng"]]
if map_data.get("zoom"):
    st.session_state.map_zoom = map_data["zoom"]

# REQUEST: Copyright Update
st.markdown("""
    <div class="footer">
        © 2024 - Trần Anh Quân - HUMG | Vietnam Environmental Monitoring System
    </div>
    """, unsafe_allow_html=True)
