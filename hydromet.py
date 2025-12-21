import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster, Fullscreen, MiniMap, Draw
import os
import glob

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Vietnam Hydromet Monitoring System", layout="wide", page_icon="🌐")

# Custom CSS for a professional Dashboard look
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

    met = read_flexible("meteorology", "Meteorology").rename(columns={'STATIONS': 'name', 'LON': 'lon', 'LAT': 'lat', 'ALTITUDE': 'altitude'})
    water = read_flexible("water quality", "Water Quality").rename(columns={'STATIONS': 'name', 'LON': 'lon', 'LAT': 'lat', 'Province': 'province'})
    hydro = read_flexible("hydrology", "Hydrology").rename(columns={'STATIONS': 'name', 'LON': 'lon', 'LAT': 'lat'})
    
    for df in [met, water, hydro]:
        if not df.empty:
            df['name'] = df['name'].astype(str).str.replace(r'\n', '', regex=True).str.strip()
            df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
            df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
            df.dropna(subset=['lat', 'lon'], inplace=True)
        
    return met, water, hydro

# --- MAIN APP LOGIC ---
try:
    met_df, water_df, hydro_df = load_and_process_data()

    # --- SIDEBAR: SYSTEM CONTROLS ---
    st.sidebar.title("🛠 System Control")
    
    with st.sidebar.expander("🗺️ Map Customization", expanded=True):
        basemap = st.selectbox("Basemap Style", ["Light (CartoDB)", "Satellite (Google)", "Dark Mode", "Terrain"])
        tiles_map = {
            "Light (CartoDB)": "cartodbpositron",
            "Satellite (Google)": "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
            "Dark Mode": "cartodbdark_matter",
            "Terrain": "https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}"
        }
        attr_map = {"Satellite (Google)": "Google", "Terrain": "Google"}

    with st.sidebar.expander("⚙️ Display Settings", expanded=True):
        disable_clustering = st.checkbox("Disable Cluster Stacking", help="View all stations individually without numbers.")
        show_names = st.checkbox("Always Show Station Labels", value=False)
        search_query = st.text_input("🔍 Filter by Name", "").strip().lower()

    with st.sidebar.expander("📡 Network Layers", expanded=True):
        show_met = st.toggle("Meteorology Network", value=True)
        # Radius Feature (Meteorology Only)
        met_radius_on = False
        if show_met:
            met_radius_on = st.checkbox("Enable Coverage Radius (Met Only)")
            if met_radius_on:
                met_rad_km = st.slider("Radius (km)", 5, 150, 30)
                met_rad_color = st.color_picker("Radius Blending Color", "#3498db")
        
        st.divider()
        show_water = st.toggle("Water Quality Network", value=True)
        show_hydro = st.toggle("Hydrology Network", value=True)

    # --- MAIN DASHBOARD ---
    st.title("Vietnam Environmental Monitoring Portal")
    
    # Summary Metrics Row
    col1, col2, col3 = st.columns(3)
    col1.metric("Meteorology Network", f"{len(met_df)} Stations")
    col2.metric("Water Quality", f"{len(water_df)} Points")
    col3.metric("Hydrology Network", f"{len(hydro_df)} Stations")

    # --- MAP RENDERING ---
    m = folium.Map(
        location=[16.46, 107.59], 
        zoom_start=6, 
        tiles=tiles_map[basemap], 
        attr=attr_map.get(basemap, "OpenStreetMap")
    )

    # MiniMap (Bigger)
    MiniMap(toggle_display=True, width=180, height=180, position='bottomright').add_to(m)
    Fullscreen().add_to(m)
    Draw(export=True, position='topleft').add_to(m)

    def add_layer(df, color, icon, label, is_met=False):
        if df.empty: return
        data = df.copy()
        if search_query:
            data = data[data['name'].str.lower().str.contains(search_query)]
        
        # Decide container based on User preference
        if disable_clustering:
            container = m
        else:
            container = MarkerCluster(name=label, control=True).add_to(m)
            
        for _, row in data.iterrows():
            tooltip = row['name'] if show_names else None
            
            # Blending Radius Circle (Meteorology Only)
            if is_met and met_radius_on:
                folium.Circle(
                    location=[row['lat'], row['lon']],
                    radius=met_rad_km * 1000,
                    color=met_rad_color,
                    weight=0, # Remove outline for blending effect
                    fill=True,
                    fill_color=met_rad_color,
                    fill_opacity=0.15, # Low opacity allows overlaps to darken
                ).add_to(m)

            # Station Marker
            folium.Marker(
                location=[row['lat'], row['lon']],
                popup=f"<b>Station:</b> {row['name']}<br><b>Network:</b> {label}",
                tooltip=tooltip,
                icon=folium.Icon(color=color, icon=icon, prefix='fa')
            ).add_to(container)

    # Plot layers
    if show_met: add_layer(met_df, "blue", "cloud", "Meteorology", is_met=True)
    if show_water: add_layer(water_df, "green", "tint", "Water Quality")
    if show_hydro: add_layer(hydro_df, "red", "water", "Hydrology")

    folium.LayerControl(position='topright', collapsed=False).add_to(m)
    
    # Map Display
    st_folium(m, width="100%", height=700, key="vn_system_pro", returned_objects=[])

    # Copyright Footer
    st.markdown("""
        <div class="footer">
            © 2024 Vietnam Hydromet Monitoring Network System. All rights reserved. 
            | Unauthorized reproduction of spatial data is prohibited.
        </div>
        """, unsafe_allow_html=True)

except Exception as e:
    st.error(f"System Error: {e}")
