import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster, Fullscreen
import geopandas as gpd
import os
import glob

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Vietnam Hydromet Network", layout="wide", page_icon="🌍")

# Professional Styling
st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border: 1px solid #e1e4e8; }
    [data-testid="stSidebar"] { background-color: #f8f9fa; border-right: 1px solid #e1e4e8; }
    .main { background-color: #f0f2f6; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def load_and_process_data():
    def find_file(pattern):
        """Finds an .xlsx file matching a pattern in the root or 'data' folder."""
        matches = glob.glob(pattern)
        if not matches:
            matches = glob.glob(os.path.join("data", pattern))
        return matches[0] if matches else None

    # 1. Load Excel files based on your provided data structure
    # Meteorology data contains STATIONS, LON, LAT, and ALTITUDE
    met_file = find_file("*meteorology*.xlsx")
    if not met_file: raise FileNotFoundError("Meteorology Excel file not found.")
    met = pd.read_excel(met_file).rename(columns={'STATIONS': 'name', 'LON': 'lon', 'LAT': 'lat', 'ALTITUDE': 'altitude'})

    # Water Quality data contains STATIONS, LON, LAT, Province, and Group
    water_file = find_file("*water quality*.xlsx")
    if not water_file: raise FileNotFoundError("Water Quality Excel file not found.")
    water = pd.read_excel(water_file).rename(columns={'STATIONS': 'name', 'LON': 'lon', 'LAT': 'lat', 'Province': 'province_raw'})

    # Hydrology data contains STATIONS, LAT, and LON
    hydro_file = find_file("*hydrology station*.xlsx")
    if not hydro_file: raise FileNotFoundError("Hydrology Excel file not found.")
    hydro = pd.read_excel(hydro_file).rename(columns={'STATIONS': 'name', 'LON': 'lon', 'LAT': 'lat'})
    
    # 2. Data Cleaning
    for df in [met, water, hydro]:
        df['name'] = df['name'].astype(str).str.replace(r'\n', '', regex=True).str.strip()
        df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
        df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
        df.dropna(subset=['lat', 'lon'], inplace=True)

    # 3. Load Shapefile for Administrative Boundaries
    shp_file = find_file("Vietnam34.shp")
    if not shp_file:
        shp_file = glob.glob(os.path.join("shapefiles", "Vietnam34.shp"))
        shp_file = shp_file[0] if shp_file else None
    
    if not shp_file: raise FileNotFoundError("Vietnam34.shp not found.")
    
    gdf_prov = gpd.read_file(shp_file)
    gdf_prov = gdf_prov.to_crs(epsg=4326)
    gdf_prov['geometry'] = gdf_prov['geometry'].simplify(tolerance=0.01)

    # 4. Spatial Join to assign Province to every station
    def assign_province(df):
        points = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.lon, df.lat), crs="EPSG:4326")
        joined = gpd.sjoin(points, gdf_prov, how="left", predicate="within")
        name_cols = [c for c in joined.columns if 'NAME' in c.upper() or 'TINH' in c.upper()]
        prov_col = name_cols[0] if name_cols else joined.columns[0]
        df['province'] = joined[prov_col].fillna("Unknown Area")
        return df

    return assign_province(met), assign_province(water), assign_province(hydro), gdf_prov

# --- MAIN APP INTERFACE ---
try:
    with st.spinner("Loading Network Data..."):
        met_df, water_df, hydro_df, province_gdf = load_and_process_data()

    # Sidebar Controls
    st.sidebar.title("📍 Network Settings")
    show_met = st.sidebar.toggle("Meteorology Network", value=True)
    show_water = st.sidebar.toggle("Water Quality Network", value=True)
    show_hydro = st.sidebar.toggle("Hydrology Network", value=True)
    
    st.sidebar.divider()
    
    # Filter by Province
    name_col = [c for c in province_gdf.columns if 'NAME' in c.upper() or 'TINH' in c.upper()][0]
    all_prov
