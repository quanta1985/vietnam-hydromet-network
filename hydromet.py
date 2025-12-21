import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster
import geopandas as gpd

# Page setup
st.set_page_config(page_title="Vietnam Hydromet Network", layout="wide")

@st.cache_data
def load_and_optimize_data():
    # 1. Load Data
    met = pd.read_excel('data/meteorology.xlsx').rename(columns={'STATIONS': 'name', 'LON': 'lon', 'LAT': 'lat'})
    water = pd.read_excel('data/water quality.xlsx').rename(columns={'Name': 'name', 'Lon': 'lon', 'Lat': 'lat', 'Province': 'province'})
    hydro = pd.read_excel('data/hydrology station.xlsx').rename(columns={'station_name': 'name', 'lon': 'lon', 'lat': 'lat', 'province_name': 'province'})
    
    # 2. Clean Coordinates [cite: 1, 4, 20]
    for df in [met, water, hydro]:
        df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
        df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
        df.dropna(subset=['lat', 'lon'], inplace=True)

    # 3. Simplify Shapefile (CRITICAL FOR SPEED)
    gdf = gpd.read_file('shapefiles/Vietnam34.shp')
    # Tolerance 0.01 simplifies borders while keeping them looking good
    gdf['geometry'] = gdf['geometry'].simplify(tolerance=0.01, preserve_topology=True)
    
    return met, water, hydro, gdf

# Show a loading spinner during the first run
with st.spinner("Optimizing Map Layers..."):
    met_df, water_df, hydro_df, province_gdf = load_and_optimize_data()

# --- Sidebar ---
st.sidebar.header("Map Layers")
show_met = st.sidebar.toggle("Meteorology", True)
show_water = st.sidebar.toggle("Water Quality", True)
show_hydro = st.sidebar.toggle("Hydrology", True)

# --- Map Construction ---
m = folium.Map(location=[16.0, 106.0], zoom_start=6, tiles="CartoDB positron")

# Add Simplified Borders
folium.GeoJson(
    province_gdf,
    style_function=lambda x: {'fillColor': '#f2f2f2', 'color': '#0078ff', 'weight': 1, 'fillOpacity': 0.1}
).add_to(m)

# Plotting Function using Light CircleMarkers
def add_layer(df, color, group_name):
    cluster = MarkerCluster(name=group_name).add_to(m)
    for _, row in df.iterrows():
        folium.CircleMarker(
            location=[row['lat'], row['lon']],
            radius=5,
            popup=f"<b>{row['name']}</b><br>{group_name}",
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7
        ).add_to(cluster)

if show_met: add_layer(met_df, '#3498db', "Meteorology")
if show_water: add_layer(water_df, '#2ecc71', "Water Quality")
if show_hydro: add_layer(hydro_df, '#e74c3c', "Hydrology")

# Add Layer Control UI
folium.LayerControl().add_to(m)

# Display Map
st_folium(m, width="100%", height=700, key="optimized_map")
