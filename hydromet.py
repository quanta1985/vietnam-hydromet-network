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

# Professional Styling for the Dashboard
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

    # 1. Load Excel files based on your provided structure
    # Meteorology [cite: 1]
    met_file = find_file("*meteorology*.xlsx")
    if not met_file: raise FileNotFoundError("Meteorology Excel file not found.")
    met = pd.read_excel(met_file).rename(columns={'STATIONS': 'name', 'LON': 'lon', 'LAT': 'lat', 'ALTITUDE': 'altitude'})

    # Water Quality [cite: 4]
    water_file = find_file("*water quality*.xlsx")
    if not water_file: raise FileNotFoundError("Water Quality Excel file not found.")
    water = pd.read_excel(water_file).rename(columns={'STATIONS': 'name', 'LON': 'lon', 'LAT': 'lat', 'Province': 'province_raw'})

    # Hydrology [cite: 20]
    hydro_file = find_file("*hydrology station*.xlsx")
    if not hydro_file: raise FileNotFoundError("Hydrology Excel file not found.")
    hydro = pd.read_excel(hydro_file).rename(columns={'STATIONS': 'name', 'LON': 'lon', 'LAT': 'lat'})
    
    # 2. Data Cleaning - Essential for Mapping
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
    
    if not shp_file: raise FileNotFoundError("Vietnam34.shp not found. Ensure all shapefile parts (.shp, .dbf, .shx) are present.")
    
    gdf_prov = gpd.read_file(shp_file)
    gdf_prov = gdf_prov.to_crs(epsg=4326)
    gdf_prov['geometry'] = gdf_prov['geometry'].simplify(tolerance=0.01)

    # 4. Spatial Join to assign Province to every station automatically
    def assign_province(df):
        points = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.lon, df.lat), crs="EPSG:4326")
        joined = gpd.sjoin(points, gdf_prov, how="left", predicate="within")
        name_cols = [c for c in joined.columns if 'NAME' in c.upper() or 'TINH' in c.upper()]
        prov_col = name_cols[0] if name_cols else joined.columns[0]
        df['province'] = joined[prov_col].fillna("Unknown Area")
        return df

    return assign_province(met), assign_province(water), assign_province(hydro), gdf_prov

# --- MAIN APP LOGIC ---
try:
    with st.spinner("Processing network data and spatial layers..."):
        met_df, water_df, hydro_df, province_gdf = load_and_process_data()

    # Sidebar Controls
    st.sidebar.title("📍 Network Settings")
    show_met = st.sidebar.toggle("Meteorology Network", value=True)
    show_water = st.sidebar.toggle("Water Quality Network", value=True)
    show_hydro = st.sidebar.toggle("Hydrology Network", value=True)
    
    st.sidebar.divider()
    
    # Unified Province Filter
    name_col = [c for c in province_gdf.columns if 'NAME' in c.upper() or 'TINH' in c.upper()][0]
    all_provs = sorted(list(province_gdf[name_col].unique()))
    selected_prov = st.sidebar.selectbox("Focus on Province", ["All Vietnam"] + all_provs)

    st.title("Vietnam Environmental Monitoring Portal")
    
    # Professional Metrics Row
    c1, c2, c3 = st.columns(3)
    c1.metric("Meteorology [cite: 1, 2, 3]", len(met_df))
    c2.metric("Water Quality [cite: 4, 10, 15]", len(water_df))
    c3.metric("Hydrology [cite: 20, 22, 26]", len(hydro_df))

    # --- MAP RENDERING ---
    # Center map on Vietnam
    m = folium.Map(location=[16.0, 107.5], zoom_start=6, tiles="cartodbpositron")
    Fullscreen().add_to(m)

    # Add Province Boundaries (The Pro Background)
    folium.GeoJson(
        province_gdf,
        name="Administrative Borders",
        style_function=lambda x: {'fillColor': 'transparent', 'color': '#007bff', 'weight': 1.5, 'opacity': 0.4}
    ).add_to(m)

    # Plotting Function with Light CircleMarkers
    def plot_data(df, color, label):
        data = df.copy()
        if selected_prov != "All Vietnam":
            data = data[data['province'] == selected_prov]
        
        cluster = MarkerCluster(name=label).add_to(m)
        for _, row in data.iterrows():
            popup_html = f"<b>{row['name']}</b><br>Type: {label}<br>Province: {row['province']}"
            if 'altitude' in row and not pd.isna(row['altitude']):
                popup_html += f"<br>Altitude: {row['altitude']} m"

            folium.CircleMarker(
                location=[row['lat'], row['lon']],
                radius=6,
                popup=folium.Popup(popup_html, max_width=250),
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.7
            ).add_to(cluster)

    if show_met: plot_data(met_df, "#0052cc", "Meteorology")
    if show_water: plot_data(water_df, "#228b22", "Water Quality")
    if show_hydro: plot_data(hydro_df, "#d32f2f", "Hydrology")

    folium.LayerControl().add_to(m)
    
    # Display the Map
    st_folium(m, width="100%", height=650, key="vn_network_map", returned_objects=[])

# This is the 'except' block that fixes your specific SyntaxError
except Exception as e:
    st.error(f"Critical System Error: {e}")
    st.info("Check that 'openpyxl' is in requirements.txt and your .xlsx files are in the repository.")
