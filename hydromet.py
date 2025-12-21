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
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    [data-testid="stSidebar"] { background-color: #f8f9fa; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def load_and_process_data():
    # Helper to find files regardless of folder structure
    def get_path(filename):
        # Checks for file in current directory OR in a 'data' subfolder
        if os.path.exists(filename): return filename
        path = os.path.join("data", filename)
        if os.path.exists(path): return path
        raise FileNotFoundError(f"Could not find {filename}")

    # [cite_start]1. Load your revised CSV files using exact names from your upload [cite: 1, 4, 20]
    met = pd.read_csv(get_path('meteorology.xlsx - Sheet1.csv'))
    water = pd.read_csv(get_path('water quality.xlsx - Sheet.csv'))
    hydro = pd.read_csv(get_path('hydrology station.xlsx - Export.csv'))
    
    # [cite_start]2. Standardize Columns and Clean strings [cite: 1, 4, 20]
    met = met.rename(columns={'STATIONS': 'name', 'LON': 'lon', 'LAT': 'lat', 'ALTITUDE': 'altitude'})
    water = water.rename(columns={'STATIONS': 'name', 'LON': 'lon', 'LAT': 'lat', 'Province': 'province_raw'})
    hydro = hydro.rename(columns={'STATIONS': 'name', 'LON': 'lon', 'LAT': 'lat'})
    
    # Clean station names and coordinates
    for df in [met, water, hydro]:
        df['name'] = df['name'].astype(str).str.replace(r'\n', '', regex=True).str.strip()
        df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
        df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
        df.dropna(subset=['lat', 'lon'], inplace=True)

    # 3. Load Shapefile (Look in root or 'shapefiles' folder)
    shp_path = "Vietnam34.shp"
    if not os.path.exists(shp_path):
        shp_path = os.path.join("shapefiles", "Vietnam34.shp")
    
    gdf_prov = gpd.read_file(shp_path)
    gdf_prov = gdf_prov.to_crs(epsg=4326)
    gdf_prov['geometry'] = gdf_prov['geometry'].simplify(tolerance=0.005)

    # 4. Spatial Join to assign Province to every station
    def assign_province(df):
        points = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.lon, df.lat), crs="EPSG:4326")
        joined = gpd.sjoin(points, gdf_prov, how="left", predicate="within")
        # Identify name column (likely NAME_1, TEN_TINH, etc.)
        name_cols = [c for c in joined.columns if 'NAME' in c.upper() or 'TINH' in c.upper()]
        prov_col = name_cols[0] if name_cols else joined.columns[0]
        df['province'] = joined[prov_col].fillna("Unknown Area")
        return df

    return assign_province(met), assign_province(water), assign_province(hydro), gdf_prov

# --- MAIN LOGIC ---
try:
    with st.spinner("Initializing Vietnam Environmental Map..."):
        met_df, water_df, hydro_df, province_gdf = load_and_process_data()

    # --- SIDEBAR ---
    st.sidebar.title("📍 Control Panel")
    st.sidebar.subheader("Layer Visibility")
    show_met = st.sidebar.toggle("Meteorology Network", value=True)
    show_water = st.sidebar.toggle("Water Quality Network", value=True)
    show_hydro = st.sidebar.toggle("Hydrology Network", value=True)
    
    st.sidebar.divider()
    
    # Province Filter based on Shapefile names
    name_col = [c for c in province_gdf.columns if 'NAME' in c.upper() or 'TINH' in c.upper()][0]
    all_provs = sorted(list(province_gdf[name_col].unique()))
    selected_prov = st.sidebar.selectbox("Focus on Province", ["All Vietnam"] + all_provs)

    # --- DASHBOARD UI ---
    st.title("Vietnam Environmental Monitoring Network")
    
    cols = st.columns(3)
    [cite_start]cols[0].metric("Meteorology Stations", len(met_df)) [cite: 1]
    [cite_start]cols[1].metric("Water Quality Stations", len(water_df)) [cite: 4]
    [cite_start]cols[2].metric("Hydrology Stations", len(hydro_df)) [cite: 20]

    # --- MAP ---
    m = folium.Map(location=[16.46, 107.59], zoom_start=6, tiles="cartodbpositron")
    Fullscreen().add_to(m)

    # Province Outlines
    folium.GeoJson(
        province_gdf,
        name="Boundaries",
        style_function=lambda x: {'fillColor': 'transparent', 'color': '#007bff', 'weight': 1, 'opacity': 0.4}
    ).add_to(m)

    def plot_data(df, color, label):
        data = df.copy()
        if selected_prov != "All Vietnam":
            data = data[data['province'] == selected_prov]
        
        cluster = MarkerCluster(name=label).add_to(m)
        for _, row in data.iterrows():
            popup_text = f"<b>{row['name']}</b><br>Type: {label}<br>Province: {row['province']}"
            if 'altitude' in row and not pd.isna(row['altitude']):
                [cite_start]popup_text += f"<br>Altitude: {row['altitude']}m" [cite: 1]
            
            folium.CircleMarker(
                location=[row['lat'], row['lon']],
                radius=6,
                popup=folium.Popup(popup_text, max_width=300),
                color=color,
                fill=True,
                fill_opacity=0.7
            ).add_to(cluster)

    if show_met: plot_data(met_df, "#0033cc", "Meteorology")
    if show_water: plot_data(water_df, "#28a745", "Water Quality")
    if show_hydro: plot_data(hydro_df, "#dc3545", "Hydrology")

    folium.LayerControl().add_to(m)
    st_folium(m, width="100%", height=700, key="vnm_map", returned_objects=[])

except Exception as e:
    st.error(f"Critical Error: {e}")
    st.info("Check that your CSV files and Shapefiles are in the root directory or 'data'/'shapefiles' folders.")
