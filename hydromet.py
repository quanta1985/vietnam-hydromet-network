import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster, Fullscreen
import geopandas as gpd

# Set Page Configuration
st.set_page_config(page_title="Vietnam Hydromet Network", layout="wide", page_icon="📍")

# Professional Styling
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def load_all_data():
    # Load and map Meteorology [cite: 1]
    met = pd.read_excel('data/meteorology.xlsx')
    met = met.rename(columns={'STATIONS': 'name', 'LON': 'lon', 'LAT': 'lat'})
    
    # Load and map Water Quality [cite: 4]
    water = pd.read_excel('data/water quality.xlsx')
    water = water.rename(columns={'Name': 'name', 'Lon': 'lon', 'Lat': 'lat', 'Province': 'province'})
    
    # Load and map Hydrology 
    hydro = pd.read_excel('data/hydrology station.xlsx')
    hydro = hydro.rename(columns={'station_name': 'name', 'lon': 'lon', 'lat': 'lat', 'province_name': 'province'})
    
    # Load Shapefile and Simplify geometry for performance
    gdf = gpd.read_file('shapefiles/Vietnam34.shp')
    gdf['geometry'] = gdf['geometry'].simplify(tolerance=0.01, preserve_topology=True)
    
    # Clean data: Force numeric and drop invalid coordinates
    for df in [met, water, hydro]:
        df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
        df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
        df.dropna(subset=['lat', 'lon'], inplace=True)
        
    return met, water, hydro, gdf

try:
    met_df, water_df, hydro_df, province_gdf = load_all_data()

    # --- SIDEBAR FILTERS ---
    st.sidebar.title("Map Settings")
    show_met = st.sidebar.toggle("Meteorology Network", value=True)
    show_water = st.sidebar.toggle("Water Quality Network", value=True)
    show_hydro = st.sidebar.toggle("Hydrology Network", value=True)
    
    # Combine provinces for filter
    all_provinces = sorted(pd.concat([water_df['province'], hydro_df['province']]).unique())
    selected_prov = st.sidebar.selectbox("Filter by Province", ["All Vietnam"] + list(all_provinces))

    # --- MAIN UI ---
    st.title("Vietnam Environmental Monitoring Network")
    
    # KPI Row
    k1, k2, k3 = st.columns(3)
    k1.metric("Meteorology", len(met_df))
    k2.metric("Water Quality", len(water_df))
    k3.metric("Hydrology", len(hydro_df))

    # --- MAP LOGIC ---
    m = folium.Map(location=[16.0, 106.5], zoom_start=6, tiles="cartodbpositron")
    Fullscreen().add_to(m)

    # Add simplified province borders
    folium.GeoJson(province_gdf, name="Provinces", 
                   style_function=lambda x: {'fillColor': 'transparent', 'color': '#004de6', 'weight': 1}).add_to(m)

    def plot_stations(df, color, label):
        plot_df = df.copy()
        if selected_prov != "All Vietnam" and 'province' in plot_df.columns:
            plot_df = plot_df[plot_df['province'] == selected_prov]
        
        cluster = MarkerCluster(name=label).add_to(m)
        for _, row in plot_df.iterrows():
            folium.CircleMarker(
                location=[row['lat'], row['lon']],
                radius=6,
                popup=f"<b>{row['name']}</b><br>{label}",
                color=color,
                fill=True,
                fill_opacity=0.8
            ).add_to(cluster)

    if show_met: plot_stations(met_df, "#1f77b4", "Meteorology")
    if show_water: plot_stations(water_df, "#2ca02c", "Water Quality")
    if show_hydro: plot_stations(hydro_df, "#d62728", "Hydrology")

    folium.LayerControl().add_to(m)
    
    # Render map
    st_folium(m, width="100%", height=650, key="main_map")

except Exception as e:
    st.error(f"Critical Application Error: {e}")
    st.info("Please ensure all column names in Excel match the source files (LAT, LON, STATIONS, etc.)")
