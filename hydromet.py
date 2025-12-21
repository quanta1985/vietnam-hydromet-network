import streamlit as st
import pandas as pd
import leafmap.foliumap as leafmap  # Professional mapping backend
import os
import glob
from folium.plugins import MarkerCluster, Fullscreen, MiniMap, Draw
from streamlit_folium import st_folium

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Vietnam Hydromet Monitoring System", layout="wide", page_icon="🌐")

# --- CSS (Keep as is) ---
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
    left: 0;
    bottom: 0;
    width: 100%;
    background-color: #f8f9fa;
    color: #6c757d;
    text-align: center;
    padding: 8px;
    font-size: 11px;
    border-top: 1px solid #e1e8ed;
    z-index: 1000;
}
</style>
""", unsafe_allow_html=True)

# --- SESSION STATE FOR MAP VIEW ---
if "map_center" not in st.session_state:
    st.session_state.map_center = [16.46, 107.59]
if "map_zoom" not in st.session_state:
    st.session_state.map_zoom = 6

# --- DATA ---
@st.cache_data
def load_and_process_data():
    def find_file(patterns):
        for pattern in patterns:
            for d in [".", "data"]:
                matches = glob.glob(os.path.join(d, pattern))
                if matches:
                    return matches[0]
        return None

    def read_flexible(pattern):
        path = find_file([f"*{pattern}*.xlsx", f"*{pattern}*.csv"])
        if not path:
            return pd.DataFrame()
        return pd.read_csv(path) if path.lower().endswith(".csv") else pd.read_excel(path)

    met = read_flexible("meteorology").rename(columns={'STATIONS':'name','LON':'lon','LAT':'lat','ALTITUDE':'altitude'})
    water = read_flexible("water quality").rename(columns={'STATIONS':'name','LON':'lon','LAT':'lat','Province':'province'})
    hydro = read_flexible("hydrology").rename(columns={'STATIONS':'name','LON':'lon','LAT':'lat'})

    for df in [met, water, hydro]:
        if not df.empty:
            df['name'] = df['name'].astype(str).str.strip()
            df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
            df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
            df.dropna(subset=['lat','lon'], inplace=True)

    return met, water, hydro

met_df, water_df, hydro_df = load_and_process_data()

# --- SIDEBAR ---
st.sidebar.title("🛠 System Control")

with st.sidebar.expander("🗺️ Map Customization", expanded=True):
    basemap_selection = st.selectbox(
        "Basemap Style",
        ["OpenStreetMap", "ROADMAP", "SATELLITE", "TERRAIN", "HYBRID", "Dark Mode"]
    )
    leafmap_basemaps = {
        "OpenStreetMap": "OpenStreetMap",
        "ROADMAP": "ROADMAP",
        "SATELLITE": "SATELLITE",
        "TERRAIN": "TERRAIN",
        "HYBRID": "HYBRID",
        "Dark Mode": "CartoDB.DarkMatter"
    }

with st.sidebar.expander("⚙️ Display Settings", expanded=True):
    # REFINEMENT: Default set to True
    disable_clustering = st.checkbox("Disable Cluster Stacking", value=True)
    # REFINEMENT: Default set to True 
    show_names = st.checkbox("Always Show Station Labels", value=True)
    search_query = st.text_input("🔍 Filter by Name", "").strip().lower()

    marker_size = st.slider("Marker Size", 6, 16, 10)
    marker_style = st.selectbox(
        "Marker Style",
        ["Classic (FontAwesome)", "Circle (Clean)", "Circle (Filled)", "Minimal Dot"]
    )

with st.sidebar.expander("📡 Network Layers", expanded=True):
    show_met = st.toggle("Meteorology Network", value=True)
    met_radius_on = False
    if show_met:
        met_radius_on = st.checkbox("Enable Coverage Radius (Met Only)")
        if met_radius_on:
            met_rad_km = st.slider("Radius (km)", 5, 150, 30)
            met_rad_color = st.color_picker("Radius Color", "#3498db")

    st.divider()
    show_water = st.toggle("Water Quality Network", value=True)
    show_hydro = st.toggle("Hydrology Network", value=True)

# --- MAIN ---
st.title("Vietnam Hydromet Monitoring Portal (BETA)")

c1, c2, c3 = st.columns(3)
c1.metric("Meteorology Network", f"{len(met_df)} Stations")
c2.metric("Water Quality", f"{len(water_df)} Points")
c3.metric("Hydrology Network", f"{len(hydro_df)} Stations")

# --- MAP ---
m = leafmap.Map(
    center=st.session_state.map_center,
    zoom=st.session_state.map_zoom,
    draw_control=False,
    measure_control=False,
    fullscreen_control=False
)

m.add_basemap(leafmap_basemaps[basemap_selection])

# REFINEMENT: MiniMap explicitly set to a lightmap tile (CartoDB Positron)
MiniMap(tile_layer="CartoDB.Positron", toggle_display=True, width=180, height=180).add_to(m)
Fullscreen().add_to(m)
Draw(export=True).add_to(m)

def add_layer(df, color, icon, label, is_met=False):
    if df.empty:
        return

    data = df.copy()
    if search_query:
        data = data[data['name'].str.lower().str.contains(search_query)]

    if disable_clustering:
        container = m
    else:
        container = MarkerCluster(name=label).add_to(m)

    for _, row in data.iterrows():
        tooltip = row['name'] if show_names else None
        popup = f"<b>Station:</b> {row['name']}<br><b>Network:</b> {label}"

        if is_met and met_radius_on:
            leafmap.folium.Circle(
                location=[row['lat'], row['lon']],
                radius=met_rad_km * 1000,
                fill=True,
                fill_color=met_rad_color,
                fill_opacity=0.08,
                stroke=False,
            ).add_to(m)

        if marker_style == "Classic (FontAwesome)":
            leafmap.folium.Marker(
                [row['lat'], row['lon']],
                popup=popup,
                tooltip=tooltip,
                icon=leafmap.folium.Icon(color=color, icon=icon, prefix='fa')
            ).add_to(container)
        elif marker_style == "Circle (Clean)":
            leafmap.folium.CircleMarker(
                [row['lat'], row['lon']],
                radius=marker_size,
                popup=popup,
                tooltip=tooltip,
                color=color,
                fill=False,
                weight=2
            ).add_to(container)
        elif marker_style == "Circle (Filled)":
            leafmap.folium.CircleMarker(
                [row['lat'], row['lon']],
                radius=marker_size,
                popup=popup,
                tooltip=tooltip,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.8
            ).add_to(container)
        else:
            leafmap.folium.CircleMarker(
                [row['lat'], row['lon']],
                radius=max(3, marker_size // 2),
                popup=popup,
                tooltip=tooltip,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=1,
                weight=0
            ).add_to(container)

if show_met:
    add_layer(met_df, "blue", "cloud", "Meteorology", True)
if show_water:
    add_layer(water_df, "green", "tint", "Water Quality")
if show_hydro:
    add_layer(hydro_df, "red", "water", "Hydrology")

map_data = st_folium(
    m,
    width="100%",
    height=700,
    key="vn_system_pro",
    returned_objects=["center", "zoom"]
)

if map_data.get("center"):
    st.session_state.map_center = [
        map_data["center"]["lat"],
        map_data["center"]["lng"]
    ]
if map_data.get("zoom"):
    st.session_state.map_zoom = map_data["zoom"]

st.markdown("""
<div class="footer">
© 2024 Trần Anh Quân – Hanoi University of Mining and Geology (HUMG)
</div>
""", unsafe_allow_html=True)

