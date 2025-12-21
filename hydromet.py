import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster, Fullscreen
import geopandas as gpd
import os

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Vietnam Hydromet Network", layout="wide", page_icon="🌍")

# Professional Styling
st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def load_and_process_data():
    # 1. Load your revised CSV files
    # Note: Using your exact filenames. If they are in a 'data' folder, update the path.
    met = pd.read_csv('data/meteorology.xlsx - Sheet1.csv')
    water = pd.read_csv('data/water quality.xlsx - Sheet.csv')
    hydro = pd.read_csv('data/hydrology station.xlsx - Export.csv')
    
    # 2. Standardize Columns and Clean strings
    met = met.rename(columns={'STATIONS': 'name', 'LON': 'lon', 'LAT': 'lat'})
    water = water.rename(columns={'STATIONS': 'name', 'LON': 'lon', 'LAT': 'lat', 'Province': 'province_raw'})
    hydro = hydro.rename(columns={'STATIONS': 'name', 'LON': 'lon', 'LAT': 'lat'})
    
    # Clean station names (remove \n and extra spaces)
    for df in [met, water, hydro]:
        df['name'] = df['name'].astype(str).str.replace(r'\n', '', regex=True).str.strip()
        df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
        df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
        df.dropna(subset=['lat', 'lon'], inplace=True)

    # 3. Load and Simplify Shapefile
    gdf_prov = gpd.read_file('shapefiles/Vietnam34.shp')
    gdf_prov = gdf_prov.to_crs(epsg=4326) # Ensure standard coordinate system
    gdf_prov['geometry'] = gdf_prov['geometry'].simplify(tolerance=0.005) # Speed up rendering

    # 4. Pro Feature: Spatial Join (Assign Province to all points)
    def assign_province(df):
        points = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.lon, df.lat), crs="EPSG:4326")
        joined = gpd.sjoin(points, gdf_prov, how="left", predicate="within")
        # Try to find common province name column in shapefile (e.g., 'TEN_TINH' or 'NAME_1')
        prov_col = [c for c in joined.columns if 'NAME' in c.upper() or 'TINH' in c.upper()][0]
        df['province'] = joined[prov_col].fillna("Unknown")
        return df

    met = assign_province(met)
    hydro = assign_province(hydro)
    # For water quality, we can use either assigned or raw
    water = assign_province(water)

    return met, water, hydro, gdf_prov

# --- MAIN LOGIC ---
try:
    with st.spinner("Processing stations and geographic boundaries..."):
        met_df, water_df, hydro_df, province_gdf = load_and_process_data()

    # --- SIDEBAR ---
    st.sidebar.title("📍 Network Settings")
    
    st.sidebar.subheader("Layer Visibility")
    show_met = st.sidebar.toggle("Meteorology", value=True)
    show_water = st.sidebar.toggle("Water Quality", value=True)
    show_hydro = st.sidebar.toggle("Hydrology", value=True)
    
    st.sidebar.divider()
    
    # Unified Province Filter
    all_provs = sorted(list(set(province_gdf.iloc[:, 1].dropna()))) # Dynamically get province list
    selected_prov = st.sidebar.selectbox("Filter by Province", ["All Vietnam"] + all_provs)

    # --- DASHBOARD UI ---
    st.title("Vietnam Environmental Monitoring Portal")
    
    cols = st.columns(3)
    cols[0].metric("Met Stations", len(met_df))
    cols[1].metric("Water Quality", len(water_df))
    cols[2].metric("Hydro Stations", len(hydro_df))

    # --- MAP ---
    m = folium.Map(location=[16.0, 107.0], zoom_start=6, tiles="cartodbpositron")
    Fullscreen().add_to(m)

    # Display Province Boundaries
    folium.GeoJson(
        province_gdf,
        name="Provinces",
        style_function=lambda x: {'fillColor': 'transparent', 'color': '#3388ff', 'weight': 1, 'opacity': 0.5}
    ).add_to(m)

    def plot_data(df, color, label):
        data = df.copy()
        if selected_prov != "All Vietnam":
            data = data[data['province'] == selected_prov]
        
        cluster = MarkerCluster(name=label).add_to(m)
        for _, row in data.iterrows():
            folium.CircleMarker(
                location=[row['lat'], row['lon']],
                radius=6,
                popup=f"<b>{row['name']}</b><br>Type: {label}<br>Province: {row['province']}",
                color=color,
                fill=True,
                fill_opacity=0.8
            ).add_to(cluster)

    if show_met: plot_data(met_df, "#1f77b4", "Meteorology")
    if show_water: plot_data(water_df, "#2ca02c", "Water Quality")
    if show_hydro: plot_data(hydro_df, "#d62728", "Hydrology")

    folium.LayerControl().add_to(m)
    st_folium(m, width="100%", height=650, key="vn_map")

    # --- DATA EXPLORER ---
    with st.expander("📂 Explore Raw Station Data"):
        tab1, tab2, tab3 = st.tabs(["Meteorology", "Water Quality", "Hydrology"])
        tab1.dataframe(met_df, use_container_width=True)
        tab2.dataframe(water_df, use_container_width=True)
        tab3.dataframe(hydro_df, use_container_width=True)

except Exception as e:
    st.error(f"Application Error: {e}")
    st.info("Check your file paths and ensure your Shapefile folder contains all .shp, .shx, and .dbf files.")
