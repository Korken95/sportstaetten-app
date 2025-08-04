import streamlit as st
import mysql.connector
import folium
import geopandas as gpd
import pandas as pd
import re
from streamlit_folium import st_folium
from shapely import wkt

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from db import get_db_connection

st.set_page_config(page_title="🏙️ Auslastungs-Heatmap", layout="wide")
st.title("🏙️ Auslastung pro Stadtteil (pro 1000 Einwohner)")

# 📅 Jahr auswählen
jahr = st.selectbox("Jahr für Einwohnerdaten auswählen", [2023, 2022, 2021, 2020, 2019])

# 📥 Stadtteil-Geodaten laden
def lade_stadtteile():
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT name, geom_wkt FROM stadtteile2")
    daten = cursor.fetchall()
    cursor.close()
    db.close()
    gdf = pd.DataFrame(daten)
    gdf["geometry"] = gdf["geom_wkt"].apply(wkt.loads)
    return gdf

# 📥 Belegte Minuten pro Stadtteil aus DB holen
def lade_auslastung():
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    query = """
        SELECT stadtteil, SUM(TIMESTAMPDIFF(MINUTE, start, ende)) AS belegte_minuten
        FROM belegungsplan b
        JOIN adressen a ON b.segment_id = a.id
        JOIN geodaten g ON g.adressen_id = a.id
        GROUP BY stadtteil
    """
    cursor.execute(query)
    daten = cursor.fetchall()
    cursor.close()
    db.close()
    return pd.DataFrame(daten)

# 📥 Einwohner laden
def lade_einwohner(jahr):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT stadtteil, bevoelkerung FROM einwohner WHERE jahr = %s", (jahr,))
    daten = cursor.fetchall()
    cursor.close()
    db.close()
    return pd.DataFrame(daten)

# 📊 Daten laden
gdf = lade_stadtteile()
df_auslastung = lade_auslastung()
df_einwohner = lade_einwohner(jahr)

# 🔄 Namen normalisieren
def clean_name(name):
    return re.sub(r"^\d+\s*", "", name).strip()

gdf["stadtteil_clean"] = gdf["name"].apply(clean_name)
df_auslastung["stadtteil_clean"] = df_auslastung["stadtteil"].apply(clean_name)
df_einwohner["stadtteil_clean"] = df_einwohner["stadtteil"].apply(clean_name)

# 🔗 Join
df = gdf.merge(df_auslastung, on="stadtteil_clean", how="left").merge(df_einwohner, on="stadtteil_clean", how="left")

# 📏 Verhältnis berechnen
df["minuten_pro_1000"] = df["belegte_minuten"] / (df["bevoelkerung"] / 1000)

# 🐛 Debug-Ausgaben
st.subheader("🛠️ Debug-Daten")
st.write("🔹 Stadtteile (Geo):", gdf.head())
st.write("🔹 Auslastung:", df_auslastung.head())
st.write("🔹 Einwohner:", df_einwohner.head())
st.write("🔹 Kombiniert:", df[["stadtteil_clean", "belegte_minuten", "bevoelkerung", "minuten_pro_1000"]].head(15))

# 🗺️ Heatmap zeichnen
m = folium.Map(location=[51.96, 7.63], zoom_start=12)

for _, row in df.iterrows():
    if pd.notnull(row["geometry"]):
        color = "#cccccc"
        if pd.notnull(row["minuten_pro_1000"]):
            # 🔥 Farbe nach Auslastung
            value = row["minuten_pro_1000"]
            if value < 50:
                color = "#2ECC71"
            elif value < 150:
                color = "#F1C40F"
            else:
                color = "#E74C3C"
        folium.GeoJson(
            row["geometry"],
            tooltip=f"{row['stadtteil_clean']}<br>Belegte Minuten: {row['belegte_minuten']}<br>Einwohner: {row['bevoelkerung']}<br>Minuten pro 1000: {row['minuten_pro_1000']:.2f}" if pd.notnull(row["minuten_pro_1000"]) else f"{row['stadtteil_clean']}<br>Keine Daten",
            style_function=lambda feature, col=color: {
                "fillColor": col,
                "color": "black",
                "weight": 1,
                "fillOpacity": 0.6
            }
        ).add_to(m)

st_folium(m, width=1200, height=700)
