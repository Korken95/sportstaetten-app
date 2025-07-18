import streamlit as st
import folium
from folium.plugins import HeatMap
from datetime import datetime, timedelta, time
import streamlit.components.v1 as components
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from db import get_db_connection  # 🔄 zentrale Verbindungsfunktion

# Seiteneinstellungen
st.set_page_config(page_title="Belegungs-Heatmap", layout="wide")
st.title("Belegungsdichte – Heatmap")

# Auswahl des Wochentags
wochentag_anzeige = st.selectbox("Wochentag auswählen", [
    "Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"
])
wochentag_map = {
    "Montag": "Mo", "Dienstag": "Di", "Mittwoch": "Mi",
    "Donnerstag": "Do", "Freitag": "Fr", "Samstag": "Sa", "Sonntag": "So"
}
wochentag_sql = wochentag_map[wochentag_anzeige]

# Zeitslider (zwischen 06:00 und 22:00 Uhr)
slider_value = st.slider(
    "Uhrzeit auswählen",
    min_value=time(6, 0),
    max_value=time(22, 0),
    value=time(16, 0),
    step=timedelta(minutes=15)
)
zeit_str = slider_value.strftime("%H:%M:%S")

# 📥 Belegungsdaten abrufen
def lade_belegungsdichte(wochentag, zeit):
    db = get_db_connection()  # ✅ Verwendung der zentralen Funktion
    cursor = db.cursor(dictionary=True)

    query = """
        SELECT g.breitengrad, g.laengengrad
        FROM belegungsplan b
        JOIN segmente s ON b.segment_id = s.id
        JOIN adressen a ON s.einrichtung_id = a.einrichtung_id
        JOIN geodaten g ON a.id = g.adressen_id
        WHERE b.wochentag = %s
          AND b.start <= %s
          AND b.ende > %s
    """
    cursor.execute(query, (wochentag, zeit, zeit))
    daten = cursor.fetchall()
    cursor.close()
    db.close()
    return daten

# 🗺️ Heatmap anzeigen
def zeige_heatmap_aggregiert(punkte):
    m = folium.Map(location=[51.9607, 7.6261], zoom_start=12)
    heat_data = [[p['breitengrad'], p['laengengrad']] for p in punkte]

    HeatMap(heat_data, radius=20, blur=15, max_zoom=13).add_to(m)
    m.save("heatmap.html")
    components.html(open("heatmap.html", "r", encoding="utf-8").read(), height=600)

# 🚀 Karte anzeigen
daten = lade_belegungsdichte(wochentag_sql, zeit_str)
if daten:
    zeige_heatmap_aggregiert(daten)
else:
    st.info("Keine belegten Einrichtungen zum gewählten Zeitpunkt gefunden.")
