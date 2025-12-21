import os
import glob
import pandas as pd
import streamlit as st

@st.cache_data
def load_and_process_data():
    # 1. DEBUG: List all files in the current environment to find where they are
    all_files = os.listdir(".")
    st.sidebar.write("Files found in root:", all_files) # Helpful for debugging

    # 2. Define exactly what keywords to look for
    # This helps if the filename has extra spaces or "Sheet1" in it
    targets = {
        "meteorology": ["*meteorology*.csv", "*meteorology*.xlsx"],
        "water_quality": ["*waterquality*.csv", "*water quality*.csv", "*waterquality*.xlsx"],
        "hydrology": ["*hydrology*.csv", "*hydrology*.xlsx"]
    }

    def find_and_read(patterns):
        for pattern in patterns:
            # Check root directory (.) and any 'data' folder
            for folder in [".", "data"]:
                search_path = os.path.join(folder, pattern)
                matches = glob.glob(search_path)
                if matches:
                    file_path = matches[0]
                    if file_path.endswith('.csv'):
                        return pd.read_csv(file_path)
                    else:
                        return pd.read_excel(file_path)
        return pd.DataFrame()

    # Load data with flexible naming
    met = find_and_read(targets["meteorology"])
    water = find_and_read(targets["water_quality"])
    hydro = find_and_read(targets["hydrology"])

    # Standardization and cleaning
    def clean_df(df, label):
        if df.empty:
            st.error(f"⚠️ Could not find file for: {label}. Please check filename.")
            return df
        # Normalize column names to upper case to match logic
        df.columns = [c.strip().upper() for c in df.columns]
        # Map your specific column names to standardized ones
        rename_map = {
            'STATIONS': 'name', 'STATION_NAME': 'name', 'NAME': 'name',
            'LON': 'lon', 'LAT': 'lat'
        }
        df = df.rename(columns=rename_map)
        df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
        df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
        return df.dropna(subset=['lat', 'lon'])

    met_df = clean_df(met, "Meteorology")
    water_df = clean_df(water, "Water Quality")
    hydro_df = clean_df(hydro, "Hydrology")
    
    return met_df, water_df, hydro_df
