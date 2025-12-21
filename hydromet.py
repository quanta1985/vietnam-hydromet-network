import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster, Fullscreen, MiniMap, Draw
import os
import glob

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Vietnam Monitoring System", layout="wide", page_icon="🌐")

# Giao diện CSS chuyên nghiệp
st.markdown("""
    <style>
    .main { background-color: #f4f7f9; }
    .stMetric {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #e1e8ed;
    }
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: white;
        color: #555;
        text-align: center;
        padding: 10px;
        font-size: 12px;
        border-top: 1px solid #ddd;
        z-index: 1000;
    }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def load_data():
    def find_and_read(keyword):
        # Tìm file có chứa từ khóa (không phân biệt hoa thường)
        files = glob.glob(f"*{keyword}*.csv")
        if not files:
            return pd.DataFrame()
        df = pd.read_csv(files[0])
        # Chuẩn hóa tên cột
        df.columns = [c.strip().upper() for c in df.columns]
        # Đổi tên về chuẩn chung để code bên dưới chạy được
        rename_map = {'STATIONS': 'name', 'STATION_NAME': 'name', 'LAT': 'lat', 'LON': 'lon'}
        df = df.rename(columns=rename_map)
        # Làm sạch dữ liệu tọa độ
        df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
        df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
        return df.dropna(subset=['lat', 'lon'])

    met = find_and_read("meteorology")
    water = find_and_read("water quality")
    hydro = find_and_read("hydrology")
    
    return met, water, hydro

try:
    met_df, water_df, hydro_df = load_data()

    # --- THANH ĐIỀU KHIỂN (SIDEBAR) ---
    st.sidebar.title("🛠 System Control")
    
    with st.sidebar.expander("🗺️ Map Appearance", expanded=True):
        basemap_opt = st.selectbox("Basemap Style", ["Light (Default)", "Satellite", "Dark", "Terrain"])
        tiles = {
            "Light (Default)": "cartodbpositron",
            "Satellite": "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
            "Dark": "cartodbdark_matter",
            "Terrain": "https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}"
        }
        attr = "Google" if basemap_opt in ["Satellite", "Terrain"] else "OpenStreetMap"

    with st.sidebar.expander("⚙️ Display Options", expanded=True):
        disable_clustering = st.checkbox("Show Individual Stations (No Grouping)", value=False)
        show_names = st.checkbox("Always Display Names", value=False)
        search = st.text_input("🔍 Search Station Name", "").strip().lower()

    with st.sidebar.expander("📡 Network Layers", expanded=True):
        show_met = st.toggle("Meteorology Network", value=True)
        # Chỉ hỗ trợ radius cho trạm khí tượng
        met_radius_on = False
        if show_met:
            met_radius_on = st.checkbox("Show Met Coverage Radius")
            if met_radius_on:
                met_km = st.slider("Radius (km)", 5, 100, 20)
                met_color = st.color_picker("Radius Color", "#3498db")
        
        st.divider()
        show_water = st.toggle("Water Quality Network", value=True)
        show_hydro = st.toggle("Hydrology Network", value=True)

    # --- GIAO DIỆN CHÍNH ---
    st.title("Vietnam Environmental Monitoring Network")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Meteorology", len(met_df))
    col2.metric("Water Quality", len(water_df))
    col3.metric("Hydrology", len(hydro_df))

    # Khởi tạo bản đồ
    m = folium.Map(location=[16.0, 107.5], zoom_start=6, tiles=tiles[basemap_opt], attr=attr)

    # Thêm công cụ Pro
    MiniMap(toggle_display=True, width=180, height=180, position='bottomright').add_to(m)
    Fullscreen().add_to(m)
    Draw(export=True, position='topleft').add_to(m)

    def plot_layer(df, color, icon, label, is_met=False):
        if df.empty: return
        data = df.copy()
        if search:
            data = data[data['NAME'].astype(str).str.lower().str.contains(search)]
        
        # Quyết định dùng Cluster hay hiện rời rạc
        container = m if disable_clustering else MarkerCluster(name=label).add_to(m)
            
        for _, row in data.iterrows():
            # Thêm bán kính cho khí tượng (hiệu ứng hòa quyện - blending)
            if is_met and met_radius_on:
                folium.Circle(
                    location=[row['lat'], row['lon']],
                    radius=met_km * 1000,
                    color=met_color,
                    fill=True,
                    fill_color=met_color,
                    fill_opacity=0.15, # Độ mờ thấp để khi chồng lên nhau sẽ đậm hơn
                    stroke=False      # Không viền để hòa quyện mượt mà
                ).add_to(m)

            # Thêm Marker
