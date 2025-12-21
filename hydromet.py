import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster, Fullscreen, MiniMap, Draw
import os
import glob

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Vietnam Hydromet Monitoring System", layout="wide", page_icon="🌐")

# Professional UI Styling
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

@st.cache_data
def load_and_process_data():
    def find_file(patterns):
        search_dirs = [".", "data"]
        for pattern in patterns:
            for d in search_dirs:
                matches = glob.glob(os.path.join(d, pattern))
                if matches: return matches[0]
        return None

    def read_flexible(pattern, name_label):
        path = find_file([f"*{pattern}*.xlsx", f"*{pattern}*.csv"])
        if not path: return pd.DataFrame()
        return pd.read_csv(path) if path.lower().endswith('.csv') else pd.read_excel(path)

    met = read_flexible("meteorology", "Meteorology").rename(columns={'STATIONS': 'name', 'LON': 'lon', 'LAT': 'lat'})
    water = read_flexible("waterquality", "Water Quality").rename(columns={'STATIONS': 'name', 'LON': 'lon', 'LAT': 'lat'})
    hydro = read_flexible("hydrology", "Hydrology").rename(columns={'STATIONS': 'name', 'LON': 'lon', 'LAT': 'lat'})
    
    for df in [met, water, hydro]:
        if not df.empty:
            df['name'] = df['name'].astype(str).str.replace(r'\n', '', regex=True).str.strip()
            df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
            df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
            df.dropna(subset=['lat', 'lon'], inplace=True)
    return met, water, hydro

try:
    met_df, water_df, hydro_df = load_and_process_data()

    # --- SIDEBAR: SYSTEM CONTROLS ---
    st.sidebar.title("🛠 System Control")
    
    with st.sidebar.expander("🗺️ Map Appearance", expanded=True):
        basemap = st.selectbox("Basemap Style", ["Light (CartoDB)", "Satellite (Google)", "Dark Mode", "Terrain"])
        tiles_map = {
            "Light (CartoDB)": "cartodbpositron",
            "Satellite (Google)": "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
            "Dark Mode": "cartodbdark_matter",
            "Terrain": "https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}"
        }
        attr_map = {"Satellite (Google)": "Google", "Terrain": "Google"}

    with st.sidebar.expander("⚙️ Station Display", expanded=True):
        marker_size = st.slider("Station Marker Size", 4, 12, 7)
        disable_clustering = st.checkbox("View All Stations (Flat View)")
        show_names = st.checkbox("Show Station Labels")
        search_query = st.text_input("🔍 Search Name", "").strip().lower()

    with st.sidebar.expander("📡 Network Layers", expanded=True):
        show_met = st.toggle("Meteorology Network", value=True)
        met_radius_on = False
        if show_met:
            met_radius_on = st.checkbox("Show Coverage Radius")
            if met_radius_on:
                met_rad_km = st.slider("Radius (km)", 5, 100, 30)
                met_rad_color = st.color_picker("Radius Color", "#3498db")
        
        st.divider()
        show_water = st.toggle("Water Quality Network", value=True)
        show_hydro = st.toggle("Hydrology Network", value=True)

    # --- MAIN DASHBOARD ---
    st.title("Vietnam Environmental Monitoring Network")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Meteorology", f"{len(met_df)} Stations")
    col2.metric("Water Quality", f"{len(water_df)} Points")
    col3.metric("Hydrology", f"{len(hydro_df)} Stations")

    # --- MAP RENDERING ---
    m = folium.Map(
        location=[16.0, 107.5], 
        zoom_start=6, 
        tiles=tiles_map[basemap], 
        attr=attr_map.get(basemap, "OpenStreetMap"),
        control_scale=True
    )

    # Plugins
    MiniMap(toggle_display=True, width=180, height=180, position='bottomright').add_to(m)
    Fullscreen().add_to(m)
    Draw(export=True, position='topleft').add_to(m)

    def add_station_layer(df, color, icon, label, is_met=False):
        if df.empty: return
        data = df.copy()
        if search_query:
            data = data[data['name'].str.lower().str.contains(search_query)]
        
        # Use MarkerCluster or direct Map based on toggle
        container = m if disable_clustering else MarkerCluster(name=label, show=True).add_to(m)
            
        for _, row in data.iterrows():
            # Seamless Radius Blending for Met
            if is_met and met_radius_on:
                folium.Circle(
                    location=[row['lat'], row['lon']],
                    radius=met_rad_km * 1000,
                    color=met_rad_color,
                    weight=0,         # No border makes it blend continuously
                    fill=True,
                    fill_color=met_rad_color,
                    fill_opacity=0.2  # Low opacity hides individual ring overlap
                ).add_to(m)

            # High-Performance Circle Marker
            folium.CircleMarker(
                location=[row['lat'], row['lon']],
                radius=marker_size,
                popup=f"<b>{row['name']}</b><br>{label}",
                tooltip=row['name'] if show_names else None,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.8,
                weight=2
            ).add_to(container)

    # Plot layers
    if show_met: add_station_layer(met_df, "#1a73e8", "cloud", "Meteorology", is_met=True)
    if show_water: add_station_layer(water_df, "#34a853", "tint", "Water Quality")
    if show_hydro: add_station_layer(hydro_df, "#ea4335", "water", "Hydrology")

    # Removed folium.LayerControl() from here to keep top-right clean
    
    st_folium(m, width="100%", height=750, key="vn_system_final")

    # COPYRIGHT FOOTER
    st.markdown("""
        <div class="footer">
            © 2024 - Trần Anh Quân - HUMG | Vietnam Environmental Monitoring Information System
        </div>
        """, unsafe_allow_html=True)

except Exception as e:
    st.error(f"System Error: {e}")
