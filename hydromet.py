import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster
import geopandas as gpd

st.set_page_config(page_title="Vietnam Monitoring Network", layout="wide")

@st.cache_data
def load_and_clean_data():
    # Loading exactly as per your file structure
    met = pd.read_excel('data/meteorology.xlsx').rename(columns={'STATIONS': 'name', 'LON': 'lon', 'LAT': 'lat'})
    water = pd.read_excel('data/water quality.xlsx').rename(columns={'Name': 'name', 'Lon': 'lon', 'Lat': 'lat', 'Province': 'province'})
    hydro = pd.read_excel('data/hydrology station.xlsx').rename(columns={'station_name': 'name', 'lon': 'lon', 'lat': 'lat', 'province_name': 'province'})
    gdf = gpd.read_file('shapefiles/Vietnam34.shp')

    # Data Cleaning: Essential to prevent grey-out
    for df in [met, water, hydro]:
        df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
        df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
        df.dropna(subset=['lat', 'lon'], inplace=True)
        
    return met, water, hydro, gdf

met_df, water_df, hydro_df, province_gdf = load_and_clean_data()

# Sidebar
st.sidebar.header("Filter Map Layers")
show_met = st.sidebar.checkbox("Meteorology Stations", True)
show_water = st.sidebar.checkbox("Water Quality Stations", True)
show_hydro = st.sidebar.checkbox("Hydrology Stations", True)

# Map Initialization
m = folium.Map(location=[16.0, 106.0], zoom_start=6, tiles="CartoDB positron")

# Add Shapefile Layer
folium.GeoJson(province_gdf, style_function=lambda x: {'fillColor': '#ffffff00', 'color': '#3388ff', 'weight': 1}).add_to(m)

# Plotting with Clusters
if show_met:
    mc = MarkerCluster(name="Met").add_to(m)
    for _, r in met_df.iterrows():
        folium.Marker([r['lat'], r['lon']], popup=r['name'], icon=folium.Icon(color='blue', icon='info-sign')).add_to(mc)

if show_water:
    wc = MarkerCluster(name="Water").add_to(m)
    for _, r in water_df.iterrows():
        folium.Marker([r['lat'], r['lon']], popup=r['name'], icon=folium.Icon(color='green', icon='leaf')).add_to(wc)

if show_hydro:
    hc = MarkerCluster(name="Hydro").add_to(m)
    for _, r in hydro_df.iterrows():
        folium.Marker([r['lat'], r['lon']], popup=r['name'], icon=folium.Icon(color='red', icon='tint')).add_to(hc)

# Final Map Display - use a unique key to prevent reset freezing
st_folium(m, width=1400, height=700, key="main_map")
