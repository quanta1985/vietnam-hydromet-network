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
    def find_file(patterns):
        """Finds a file matching any pattern in root, 'data', or 'shapefiles' folder."""
        search_dirs = [".", "data", "shapefiles"]
        for pattern in patterns:
            for d in search_dirs:
                matches = glob.glob(os.path.join(d, pattern))
                if matches: return matches[0]
        return None

    # 1. Load Data Files (Flexible for CSV or XLSX)
    def read_flexible(pattern, name_label):
        path = find_file([f"*{pattern}*.xlsx", f"*{pattern}*.csv"])
        if not path: raise FileNotFoundError(f"Could not find {name_label} file.")
        if path.endswith('.csv'):
            return pd.read_csv(path)
        return pd.read_excel(path)

    met = read_flexible("meteorology", "Meteorology").rename(columns={'STATIONS': 'name', 'LON': 'lon', 'LAT': 'lat', 'ALTITUDE': 'altitude'}) [cite: 27]
    water = read_flexible("water quality", "Water Quality").rename(columns={'STATIONS': 'name', 'LON': 'lon', 'LAT': 'lat', 'Province': 'province_raw'}) [cite: 30]
    hydro = read_flexible("hydrology", "Hydrology").rename(columns={'STATIONS': 'name', 'LON': 'lon', 'LAT': 'lat'}) [cite: 46]
    
    # 2. Clean station names and coordinates
    for df in [met, water, hydro]:
        df['name'] = df['name'].astype(str).str.replace(r'\n', '', regex=True).str.strip()
        df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
        df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
        df.dropna(subset=['lat', 'lon'], inplace=True)

    # 3. Load Shapefile
    shp_file = find_file(["Vietnam34.shp"])
    if not shp_file: raise FileNotFoundError("Vietnam34.shp not found. Check your shapefiles folder.")
    
    gdf_prov = gpd.read_file(shp_file)
    gdf_prov = gdf_prov.to_crs(epsg=4326)
    gdf_prov['geometry'] = gdf_prov['geometry'].simplify(tolerance=0.01)

    # 4. Defensive Province Assignment
    def assign_province(df):
        points = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.lon, df.lat), crs="EPSG:4326")
        joined = gpd.sjoin(points, gdf_prov, how="left", predicate="within")
        
        # Robustly find the province name column
        potential_cols = [c for c in joined.columns if any(x in c.upper() for x in ['NAME', 'TINH', 'PROVINCE'])]
        prov_col = potential_cols[0] if potential_cols else gdf_prov.columns[1] # Fallback to 2nd col
        
        df['province'] = joined[prov_col].fillna("Unknown Area")
        return df, prov_col

    met_df, p_col = assign_province(met)
    water_df, _ = assign_province(water)
    hydro_df, _ = assign_province(hydro)

    return met_df, water_df, hydro_df, gdf_prov, p_col

# --- APP LAYOUT ---
try:
    with st.spinner("Processing network data..."):
        met_df, water_df, hydro_df, province_gdf, prov_name_col = load_and_process_data()

    # Sidebar Controls
    st.sidebar.title("📍 Network Settings")
    show_met = st.sidebar.toggle("Meteorology Network", value=True)
    show_water = st.sidebar.toggle("Water Quality Network", value=True)
    show_hydro = st.sidebar.toggle("Hydrology Network", value=True)
    
    st.sidebar.divider()
    
    # Unified Province Filter
    all_provs = sorted(list(province_gdf[prov_name_col].unique()))
    selected_prov = st.sidebar.selectbox("Focus on Province", ["All Vietnam"] + all_provs)

    st.title("Vietnam Environmental Monitoring Portal")
    
    # Summary Statistics
    c1, c2, c3 = st.columns(3)
    c1.metric("Meteorology", len(met_df)) [cite: 27]
    c2.metric("Water Quality", len(water_df)) [cite: 30]
    c3.metric("Hydrology", len(hydro_df)) [cite: 46]

    # Map Creation
    m = folium.Map(location=[16.0, 107.5], zoom_start=6, tiles="cartodbpositron")
    Fullscreen().add_to(m)

    # Add Province Boundaries
    folium.GeoJson(
        province_gdf,
        name="Borders",
        style_function=lambda x: {'fillColor': 'transparent', 'color': '#007bff', 'weight': 1.5, 'opacity': 0.4}
    ).add_to(m)

    def plot_data(df, color, label):
        data = df.copy()
        if selected_prov != "All Vietnam":
            data = data[data['province'] == selected_prov]
        
        cluster = MarkerCluster(name=label).add_to(m)
        for _, row in data.iterrows():
            popup_html = f"<b>{row['name']}</b><br>Type: {label}<br>Province: {row['province']}"
            if 'altitude' in row and not pd.isna(row['altitude']):
                popup_html += f"<br>Altitude: {row['altitude']} m" [cite: 27]

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
    st_folium(m, width="100%", height=650, key="vn_hydromet_final")

except Exception as e:
    st.error(f"Critical System Error: {e}")
