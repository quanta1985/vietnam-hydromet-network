import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.express as px

# Page Config
st.set_page_config(page_title="Vietnam Environmental Monitoring Map", layout="wide", page_icon="🌍")

# Custom CSS for Pro Look
st.markdown("""
    <style>
    .main {
        background-color: #f5f7f9;
    }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)

# --- DATA LOADING ---
@st.cache_data
def load_data():
    # Load your CSVs (adjust file names as needed)
    met = pd.read_csv('data/meteorology.csv') # Columns: STATIONS, LON, LAT, ALTITUDE
    water = pd.read_csv('data/water_quality.csv') # Columns: Name, Lon, Lat, Province
    hydro = pd.read_csv('data/hydrology.csv') # Columns: station_name, lat, lon, province_name
    
    # Standardize column names for mapping
    met = met.rename(columns={'STATIONS': 'name', 'LON': 'lon', 'LAT': 'lat'})
    water = water.rename(columns={'Name': 'name', 'Lon': 'lon', 'Lat': 'lat', 'Province': 'province'})
    hydro = hydro.rename(columns={'station_name': 'name', 'lon': 'lon', 'lat': 'lat', 'province_name': 'province'})
    
    return met, water, hydro

met_df, water_df, hydro_df = load_data()

# --- SIDEBAR FILTERS ---
st.sidebar.title("🛠 Control Panel")
st.sidebar.subheader("Station Visibility")

show_met = st.sidebar.checkbox("Meteorology Stations", value=True)
show_water = st.sidebar.checkbox("Water Quality Stations", value=True)
show_hydro = st.sidebar.checkbox("Hydrology Stations", value=True)

st.sidebar.divider()

# Province Filter
all_provinces = sorted(pd.concat([water_df['province'], hydro_df['province']]).dropna().unique())
selected_province = st.sidebar.selectbox("Focus on Province", ["All Vietnam"] + list(all_provinces))

# --- MAIN DASHBOARD ---
st.title("🌍 Vietnam Environmental Monitoring Network")
st.markdown("Interactive visualization of Meteorology, Water Quality, and Hydrology stations across Vietnam.")

# KPI Row
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Meteorology Stations", len(met_df))
with col2:
    st.metric("Water Quality Stations", len(water_df))
with col3:
    st.metric("Hydrology Stations", len(hydro_df))

st.divider()

# --- MAP LOGIC ---
# Initial center of Vietnam
center_lat, center_lon = 16.047079, 108.206230
zoom_start = 6

m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom_start, control_scale=True)

# Function to add markers
def add_stations(df, color, icon, group_name):
    group = folium.FeatureGroup(name=group_name)
    for idx, row in df.iterrows():
        # Filtering logic for province
        if selected_province != "All Vietnam":
            if 'province' in df.columns and row['province'] != selected_province:
                continue
        
        folium.Marker(
            location=[row['lat'], row['lon']],
            popup=f"Station: {row['name']}<br>Type: {group_name}",
            tooltip=row['name'],
            icon=folium.Icon(color=color, icon=icon, prefix='fa')
        ).add_to(group)
    return group

# Add layers based on checkboxes
if show_met:
    add_stations(met_df, 'blue', 'cloud', 'Meteorology').add_to(m)
if show_water:
    add_stations(water_df, 'green', 'tint', 'Water Quality').add_to(m)
if show_hydro:
    add_stations(hydro_df, 'orange', 'waves', 'Hydrology').add_to(m)

# Display Map
map_data = st_folium(m, width="100%", height=600)

# --- DATA EXPLORER SECTION ---
st.divider()
st.subheader("📊 Data Explorer")

tab1, tab2, tab3 = st.tabs(["Meteorology", "Water Quality", "Hydrology"])

with tab1:
    st.dataframe(met_df, use_container_width=True)
    st.download_button("Download Met Data", met_df.to_csv(), "meteorology.csv", "text/csv")

with tab2:
    st.dataframe(water_df, use_container_width=True)
    st.download_button("Download Water Data", water_df.to_csv(), "water_quality.csv", "text/csv")

with tab3:
    st.dataframe(hydro_df, use_container_width=True)
    st.download_button("Download Hydro Data", hydro_df.to_csv(), "hydrology.csv", "text/csv")

st.sidebar.markdown("---")
st.sidebar.info("Developed for environmental monitoring and data management.")