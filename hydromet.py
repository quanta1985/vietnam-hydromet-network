import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster, Fullscreen, MiniMap, Draw
import os
import glob

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Vietnam Hydromet Network", layout="wide", page_icon="🌍")

# Professional Styling
st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border: 1px solid #e1e4e8; }
    [data-testid="stSidebar"] { background-color: #f8f9fa; border-right: 1px solid #e1e4e8; }
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
        if not path: raise FileNotFoundError(f"Could not find {name_label} file.")
        return pd.read_csv(path) if path.lower().endswith('.csv') else pd.read_excel(path)

    met = read_flexible("meteorology", "Meteorology").rename(columns={'STATIONS': 'name', 'LON': 'lon', 'LAT': 'lat', 'ALTITUDE': 'altitude'})
    water = read_flexible("water quality", "Water Quality").rename(columns={'STATIONS': 'name', 'LON': 'lon', 'LAT': 'lat', 'Province': 'province'})
    hydro = read_flexible("hydrology", "Hydrology").rename(columns={'STATIONS': 'name', 'LON': 'lon', 'LAT': 'lat'})
    
    for df in [met, water, hydro]:
        df['name'] = df['name'].astype(str).str.replace(r'\n', '', regex=True).str.strip()
        df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
        df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
        df.dropna(subset=['lat', 'lon'], inplace=True)
        
    return met, water, hydro

# --- MAIN APP LOGIC ---
try:
    met_df, water_df, hydro_df = load_and_process_data()

    # --- SIDEBAR CONTROLS ---
    st.sidebar.title("🛠 Map Toolbox")
    
    # 1. Basemap Selection
    basemap = st.sidebar.selectbox("Change Basemap", ["Light (Default)", "Satellite", "Dark", "Terrain"])
    tiles_map = {
        "Light (Default)": "cartodbpositron",
        "Satellite": "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
        "Dark": "cartodbdark_matter",
        "Terrain": "https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}"
    }
    attr_map = {
        "Satellite": "Google",
        "Terrain": "Google"
    }

    st.sidebar.divider()

    # 2. Search & Visibility
    search_query = st.sidebar.text_input("🔍 Search Station Name", "").strip().lower()
    show_names = st.sidebar.toggle("🏷 Always Show Station Names", value=False)
    
    st.sidebar.divider()

    # 3. Layer Visibility & Service Radius
    st.sidebar.subheader("Layer Settings")
    
    # Meteorology Settings
    show_met = st.sidebar.toggle("Meteorology Network", value=True)
    rad_met = 0
    if show_met and st.sidebar.checkbox("Add Met Radius"):
        rad_met = st.sidebar.slider("Met Radius (km)", 1, 50, 10) * 1000

    # Water Quality Settings
    show_water = st.sidebar.toggle("Water Quality Network", value=True)
    rad_water = 0
    if show_water and st.sidebar.checkbox("Add Water Radius"):
        rad_water = st.sidebar.slider("Water Radius (km)", 1, 50, 5) * 1000

    # Hydrology Settings
    show_hydro = st.sidebar.toggle("Hydrology Network", value=True)
    rad_hydro = 0
    if show_hydro and st.sidebar.checkbox("Add Hydro Radius"):
        rad_hydro = st.sidebar.slider("Hydro Radius (km)", 1, 50, 20) * 1000

    # --- DASHBOARD HEADER ---
    st.title("Vietnam Environmental Monitoring Portal")
    c1, c2, c3 = st.columns(3)
    c1.metric("Met Stations", len(met_df))
    c2.metric("Water Stations", len(water_df))
    c3.metric("Hydro Stations", len(hydro_df))

    # --- MAP RENDERING ---
    m = folium.Map(
        location=[16.0, 107.5], 
        zoom_start=6, 
        tiles=tiles_map[basemap], 
        attr=attr_map.get(basemap, "OpenStreetMap")
    )

    # Pro Feature: MiniMap (Bigger)
    MiniMap(toggle_display=True, width=150, height=150, position='bottomright').add_to(m)
    
    # Pro Feature: Fullscreen & Draw Toolbox
    Fullscreen().add_to(m)
    Draw(export=True, position='topleft', draw_options={'polyline':False, 'circlemarker':False}).add_to(m)

    def plot_data(df, color, icon_name, label, radius_m):
        data = df.copy()
        if search_query:
            data = data[data['name'].str.lower().str.contains(search_query)]
        
        cluster = MarkerCluster(name=label).add_to(m)
        for _, row in data.iterrows():
            # Tooltip logic for "Auto appear names"
            tooltip_txt = row['name'] if show_names else None
            
            # Marker with Beautiful Icon
            folium.Marker(
                location=[row['lat'], row['lon']],
                popup=f"<b>{row['name']}</b><br>Type: {label}",
                tooltip=tooltip_txt,
                icon=folium.Icon(color=color, icon=icon_name, prefix='fa')
            ).add_to(cluster)
            
            # Service Radius Circle
            if radius_m > 0:
                folium.Circle(
                    location=[row['lat'], row['lon']],
                    radius=radius_m,
                    color=color,
                    fill=True,
                    fill_opacity=0.1,
                    weight=1
                ).add_to(m)

    if show_met: plot_data(met_df, "blue", "cloud", "Meteorology", rad_met)
    if show_water: plot_data(water_df, "green", "tint", "Water Quality", rad_water)
    if show_hydro: plot_data(hydro_df, "red", "water", "Hydrology", rad_hydro)

    folium.LayerControl().add_to(m)
    st_folium(m, width="100%", height=750, key="vn_pro_map", returned_objects=[])

except Exception as e:
    st.error(f"Error: {e}")
