import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster, Fullscreen
import os
import glob

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Vietnam Monitoring Network", layout="wide", page_icon="🌍")

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
    def find_file(patterns):
        """Finds a file matching any pattern in root or 'data' folder."""
        search_dirs = [".", "data"]
        for pattern in patterns:
            for d in search_dirs:
                matches = glob.glob(os.path.join(d, pattern))
                if matches: return matches[0]
        return None

    # 1. Load Data Files (Flexible for CSV or XLSX)
    def read_flexible(pattern, name_label):
        path = find_file([f"*{pattern}*.xlsx", f"*{pattern}*.csv"])
        if not path: raise FileNotFoundError(f"Could not find {name_label} file.")
        # Handle Excel vs CSV
        if path.lower().endswith('.csv'):
            return pd.read_csv(path)
        return pd.read_excel(path)

    # Standardize column names during load
    met = read_flexible("meteorology", "Meteorology").rename(columns={'STATIONS': 'name', 'LON': 'lon', 'LAT': 'lat', 'ALTITUDE': 'altitude'})
    water = read_flexible("water quality", "Water Quality").rename(columns={'STATIONS': 'name', 'LON': 'lon', 'LAT': 'lat', 'Province': 'province'})
    hydro = read_flexible("hydrology", "Hydrology").rename(columns={'STATIONS': 'name', 'LON': 'lon', 'LAT': 'lat'})
    
    # 2. Data Cleaning - Essential for Mapping
    for df in [met, water, hydro]:
        df['name'] = df['name'].astype(str).str.replace(r'\n', '', regex=True).str.strip()
        df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
        df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
        df.dropna(subset=['lat', 'lon'], inplace=True)
        
    return met, water, hydro

# --- MAIN APP LOGIC ---
try:
    with st.spinner("Loading station data..."):
        met_df, water_df, hydro_df = load_and_process_data()

    # Sidebar Controls
    st.sidebar.title("📍 Network Settings")
    
    # Station Search Feature
    st.sidebar.subheader("🔍 Station Search")
    search_query = st.sidebar.text_input("Enter Station Name", "").strip().lower()

    st.sidebar.divider()
    
    st.sidebar.subheader("Layer Visibility")
    show_met = st.sidebar.toggle("Meteorology Network", value=True)
    show_water = st.sidebar.toggle("Water Quality Network", value=True)
    show_hydro = st.sidebar.toggle("Hydrology Network", value=True)

    st.title("Vietnam Environmental Monitoring Portal")
    
    # Summary Metrics Row
    c1, c2, c3 = st.columns(3)
    c1.metric("Meteorology Stations", len(met_df))
    c2.metric("Water Quality Stations", len(water_df))
    c3.metric("Hydrology Stations", len(hydro_df))

    # --- MAP RENDERING ---
    # Center map on Vietnam
    m = folium.Map(location=[16.0, 107.5], zoom_start=6, tiles="cartodbpositron")
    Fullscreen().add_to(m)

    # Plotting Function with Marker Clustering for Performance
    def plot_data(df, color, label):
        data = df.copy()
        
        # Apply Search Filter if query is provided
        if search_query:
            data = data[data['name'].str.lower().str.contains(search_query)]
        
        # Use MarkerCluster to handle large numbers of markers (especially Hydrology)
        cluster = MarkerCluster(name=label).add_to(m)
        for _, row in data.iterrows():
            popup_html = f"<b>{row['name']}</b><br>Type: {label}"
            # Add dynamic fields if they exist
            if 'province' in row and not pd.isna(row['province']):
                popup_html += f"<br>Province: {row['province']}"
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

    # Add Layers based on Toggle state
    if show_met: 
        plot_data(met_df, "#0052cc", "Meteorology")
    if show_water: 
        plot_data(water_df, "#228b22", "Water Quality")
    if show_hydro: 
        plot_data(hydro_df, "#d32f2f", "Hydrology")

    folium.LayerControl().add_to(m)
    
    # Display the Map
    st_folium(m, width="100%", height=650, key="vn_station_map", returned_objects=[])

except Exception as e:
    st.error(f"Critical System Error: {e}")
    st.info("Check that 'openpyxl' is in requirements.txt and your Excel/CSV files are in the repository.")
