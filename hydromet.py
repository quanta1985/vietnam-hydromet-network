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
        """Finds a file matching a pattern in the root or 'data' folder."""
        # Check root
        matches = glob.glob(pattern)
        if not matches:
            # Check 'data' subfolder
            matches = glob.glob(os.path.join("data", pattern))
        
        if matches:
            return matches[0]
        return None

    # 1. Load your CSV files using patterns to avoid "File Not Found" errors
    # Meteorology
    met_file = find_file("*meteorology*.csv")
    if not met_file: raise FileNotFoundError("Meteorology CSV file not found.")
    met = pd.read_csv(met_file).rename(columns={'STATIONS': 'name', 'LON': 'lon', 'LAT': 'lat', 'ALTITUDE': 'altitude'})

    # Water Quality
    water_file = find_file("*water quality*.csv")
    if not water_file: raise FileNotFoundError("Water Quality CSV file not found.")
    water = pd.read_csv(water_file).rename(columns={'STATIONS': 'name', 'LON': 'lon', 'LAT': 'lat', 'Province': 'province_raw'})

    # Hydrology
    hydro_file = find_file("*hydrology station*.csv")
    if not hydro_file: raise FileNotFoundError("Hydrology CSV file not found.")
    hydro = pd.read_csv(hydro_file).rename(columns={'STATIONS': 'name', 'LON': 'lon', 'LAT': 'lat'})
    
    # 2. Clean station names and coordinates
    for df in [met, water, hydro]:
        df['name'] = df['name'].astype(str).str.replace(r'\n', '', regex=True).str.strip()
        df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
        df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
        df.dropna(subset=['lat', 'lon'], inplace=True)

    # 3. Load Shapefile
    shp_file = find_file("Vietnam34.shp")
    if not shp_file:
        # Fallback to looking inside 'shapefiles' folder
        shp_file = glob.glob(os.path.join("shapefiles", "Vietnam34.shp"))
        shp_file = shp_file[0] if shp_file else None
    
    if not shp_file: raise FileNotFoundError("Vietnam34.shp not found. Check your shapefiles folder.")
    
    gdf_prov = gpd.read_file(shp_file)
    gdf_prov = gdf_prov.to_crs(epsg=4326)
    gdf_prov['geometry'] = gdf_prov['geometry'].simplify(tolerance=0.005)

    # 4. Spatial Join to assign Province to every station
    def assign_province(df):
        points = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.lon, df.lat), crs="EPSG:4326")
        joined = gpd.sjoin(points, gdf_prov, how="left", predicate="within")
        name_cols = [c for c in joined.columns if 'NAME' in c.upper() or 'TINH' in c.upper()]
        prov_col = name_cols[0] if name_cols else joined.columns[0]
        df['province'] = joined[prov_col].fillna("Unknown Area")
        return df

    return assign_province(met), assign_province(water), assign_province(hydro), gdf_prov

# --- APP LAYOUT ---
try:
    with st.spinner("Loading Vietnam Environmental Monitoring Data..."):
        met_df, water_df, hydro_df, province_gdf = load_and_process_data()

    # --- SIDEBAR ---
    st.sidebar.title("📍 Map Controls")
    st.sidebar.subheader("Layer Selection")
    show_met = st.sidebar.toggle("Meteorology Network", value=True)
    show_water = st.sidebar.toggle("Water Quality Network", value=True)
    show_hydro = st.sidebar.toggle("Hydrology Network", value=True)
    
    st.sidebar.divider()
    
    # Province Filter
    name_col = [c for c in province_gdf.columns if 'NAME' in c.upper() or 'TINH' in c.upper()][0]
    all_provs = sorted(list(province_gdf[name_col].unique()))
    selected_prov = st.sidebar.selectbox("Filter by Province", ["All Vietnam"] + all_provs)

    # --- MAIN DASHBOARD ---
    st.title("Vietnam Environmental Monitoring Network")
    st.markdown("Visualizing multi-parameter monitoring stations across Vietnam.")
    
    # Summary Statistics
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("Meteorology", len(met_df))
    with c2: st.metric("Water Quality", len(water_df))
    with c3: st.metric("Hydrology", len(hydro_df))

    # --- INTERACTIVE MAP ---
    m = folium.Map(location=[16.0, 107.0], zoom_start=6, tiles="cartodbpositron")
    Fullscreen().add_to(m)

    # Province Boundaries
    folium.GeoJson(
        province_gdf,
        name="Administrative Boundaries",
        style_function=lambda x: {'fillColor': 'transparent', 'color': '#007bff', 'weight': 1, 'opacity': 0.4}
    ).add_to(m)

    def plot_data(df, color, label):
        data = df.copy()
        if selected_prov != "All Vietnam":
            data = data[data['province'] == selected_prov]
        
        cluster = MarkerCluster(name=label).add_to(m)
        for _, row in data.iterrows():
            popup_content = f"""
            <div style="font-family: Arial; font-size: 12px;">
                <h4 style="margin: 0; color: {color};">{row['name']}</h4>
                <b>Type:</b> {label}<br>
                <b>Province:</b> {row['province']}
            """
            if 'altitude' in row and not pd.isna(row['altitude']):
                popup_content += f"<br><b>Altitude:</b> {row['altitude']}m"
            popup_content += "</div>"
            
            folium.CircleMarker(
                location=[row['lat'], row['lon']],
                radius=6,
                popup=folium.Popup(popup_content, max_width=300),
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.7
            ).add_to(cluster)

    if show_met: plot_data(met_df, "#0033cc", "Meteorology")
    if show_water: plot_data(water_df, "#28a745", "Water Quality")
    if show_hydro: plot_data(hydro_df, "#dc3545", "Hydrology")

    folium.LayerControl().add_to(m)
    st_folium(m, width="100%", height=700, key="vnm_main_map")

except Exception as e:
    st.error(f"Critical System Error: {e}")
    st.info("Check your repository to ensure CSV and Shapefiles are present.")
