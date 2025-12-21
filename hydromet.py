import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import geopandas as gpd
import os

# Page Config
st.set_page_config(page_title="Vietnam Monitoring Network", layout="wide", page_icon="🌊")

# --- DATA LOADING ---
@st.cache_data
def load_data():
    # Load Excel files based on your 'ls' output
    # Columns: STATIONS, LON, LAT, ALTITUDE 
    met = pd.read_excel('data/meteorology.xlsx') 
    
    # Columns: No, Name, Lon, Lat, Province, Group 
    water = pd.read_excel('data/water quality.xlsx') 
    
    # Columns: ID, station_name, lat, lon, province_name, etc. 
    hydro = pd.read_excel('data/hydrology station.xlsx') 
    
    # Load Shapefile for province boundaries
    gdf = gpd.read_file('shapefiles/Vietnam34.shp')
    
    # Standardize column names for the app
    met = met.rename(columns={'STATIONS': 'name', 'LON': 'lon', 'LAT': 'lat'})
    water = water.rename(columns={'Name': 'name', 'Lon': 'lon', 'Lat': 'lat', 'Province': 'province'})
    hydro = hydro.rename(columns={'station_name': 'name', 'lon': 'lon', 'lat': 'lat', 'province_name': 'province'})
    
    return met, water, hydro, gdf

try:
    met_df, water_df, hydro_df, province_gdf = load_data()
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

# --- SIDEBAR ---
st.sidebar.title("Network Controls")
show_met = st.sidebar.checkbox("Meteorology", value=True)
show_water = st.sidebar.checkbox("Water Quality", value=True)
show_hydro = st.sidebar.checkbox("Hydrology", value=True)

# Province Selection
# Extracting province names from data sources [cite: 4, 20]
available_provinces = sorted(pd.concat([water_df['province'], hydro_df['province']]).dropna().unique())
selected_province = st.sidebar.selectbox("Filter by Province", ["All Vietnam"] + list(available_provinces))

# --- MAIN APP ---
st.title("Vietnam Environmental Monitoring Dashboard")

# KPI Summary
c1, c2, c3 = st.columns(3)
c1.metric("Met Stations", len(met_df))
c2.metric("Water Stations", len(water_df))
c3.metric("Hydro Stations", len(hydro_df))

# --- MAP ---
# Start map at Vietnam center
m = folium.Map(location=[16.0, 106.0], zoom_start=6, tiles="cartodbpositron")

# Add Province Boundaries (The 'Pro' touch)
folium.GeoJson(
    province_gdf,
    name="Province Boundaries",
    style_function=lambda x: {'fillColor': 'transparent', 'color': 'gray', 'weight': 1}
).add_to(m)

# Filtering logic
def filter_and_plot(df, color, icon, name):
    plot_df = df.copy()
    if selected_province != "All Vietnam":
        # Only filtering if the dataframe has a 'province' column
        if 'province' in plot_df.columns:
            plot_df = plot_df[plot_df['province'] == selected_province]
    
    for _, row in plot_df.iterrows():
        folium.Marker(
            location=[row['lat'], row['lon']],
            popup=f"<b>{row['name']}</b><br>Type: {name}",
            icon=folium.Icon(color=color, icon=icon, prefix='fa')
        ).add_to(m)

if show_met: filter_and_plot(met_df, 'blue', 'cloud', 'Meteorology')
if show_water: filter_and_plot(water_df, 'green', 'tint', 'Water Quality')
if show_hydro: filter_and_plot(hydro_df, 'orange', 'water', 'Hydrology')

st_folium(m, width=1200, height=600)

# --- DATA TABLE ---
with st.expander("View Raw Data"):
    st.dataframe(pd.concat([met_df, water_df, hydro_df], ignore_index=True), use_container_width=True)
