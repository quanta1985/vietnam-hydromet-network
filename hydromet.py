import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster, Fullscreen, MiniMap, Draw
import os

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Vietnam Hydromet Monitoring System", 
    layout="wide", 
    page_icon="🌐"
)

# Professional CSS for a clean Dashboard look
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
    # File paths based on your provided data
    met = pd.read_csv("meteorology.xlsx - Sheet1.csv").rename(columns={'STATIONS': 'name', 'LON': 'lon', 'LAT': 'lat'})
    water = pd.read_csv("water quality.xlsx - Sheet.csv").rename(columns={'STATIONS': 'name', 'LON': 'lon', 'LAT': 'lat'})
    hydro = pd.read_csv("hydrology station.xlsx - Export.csv").rename(columns={'STATIONS': 'name', 'LON': 'lon', 'LAT': 'lat'})
    
    for df in [met, water, hydro]:
        df['name'] = df['name'].astype(str).str.replace(r'\n', '', regex=True).str.strip()
        df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
        df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
        df.dropna(subset=['lat', 'lon'], inplace=True)
        
    return met, water, hydro

# --- APP LOGIC ---
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
        disable_clustering = st.checkbox("Disable Cluster Stacking", help="Show every station individually without numbers.")
        show_names = st.checkbox("Always Show Station Labels", value=False)
        search_query = st.text_input("🔍 Filter by Name", "").strip().lower()

    with st.sidebar.expander("📡 Network Layers", expanded=True):
        show_met = st.toggle("Meteorology Network", value=True)
        # Radius Feature (Meteorology Only)
        met_radius_on = False
        if show_met:
            met_radius_on = st.checkbox("Enable Coverage Radius")
            if met_radius_on:
                met_rad_km = st.slider("Radius (km)", 5, 150, 30)
                met_rad_color = st.color_picker("Radius Blending Color", "#3498db")
        
        st.divider()
        show_water = st.toggle("Water Quality Network", value=True)
        show_hydro = st.toggle("Hydrology Network", value=True)

    # --- MAIN DASHBOARD ---
    st.title("Vietnam Environmental Monitoring Network")
    
    # KPIs for Network Health
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

    # Professional Plugins
    MiniMap(toggle_display=True, width=220, height=220, position='bottomright').add_to(m)
    Fullscreen().add_to(m)
    Draw(export=True, position='topleft').add_to(m)

    def add_layer(df, color, icon, label, is_met=False):
        data = df.copy()
        if search_query:
            data = data[data['name'].str.lower().str.contains(search_query)]
        
        # Determine if we add directly to map or a cluster
        if disable_clustering:
            container = m
        else:
            container = MarkerCluster(name=label, control=True).add_to(m)
            
        for _, row in data.iterrows():
            tooltip = row['name'] if show_names else None
            
            # Specialized Circle for "Blending" effect
            if is_met and met_radius_on:
                folium.Circle(
                    location=[row['lat'], row['lon']],
                    radius=met_rad_km * 1000,
                    color=met_rad_color,
                    weight=0.5,
                    fill=True,
                    fill_color=met_rad_color,
                    fill_opacity=0.15,
                    stroke=False # Removes edge to allow smooth blending
                ).add_to(m)

            # Station Marker
            folium.Marker(
                location=[row['lat'], row['lon']],
                popup=f"<b>Station:</b> {row['name']}<br><b>Network:</b> {label}",
                tooltip=tooltip,
                icon=folium.Icon(color=color, icon=icon, prefix='fa')
            ).add_to(container)

    if show_met: add_layer(met_df, "blue", "cloud", "Meteorology", is_met=True)
    if show_water: add_layer(water_df, "green", "tint", "Water Quality")
    if show_hydro: add_layer(hydro_df, "red", "water", "Hydrology")

    folium.LayerControl(position='topright', collapsed=False).add_to(m)
    
    # Map Display
    st_folium(m, width="100%", height=750, key="vn_system_pro")

    # Copyright Footer
    st.markdown("""
        <div class="footer">
            © 2024 Vietnam Environmental Monitoring Network System. All rights reserved. 
            | Unauthorized reproduction of spatial data is prohibited.
        </div>
        """, unsafe_allow_html=True)

except Exception as e:
    st.error(f"System Error: {e}")
    st.info("Please ensure the CSV files are in the root directory of your GitHub repository.")
