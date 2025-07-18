import streamlit as st
import folium
from folium import Map, CircleMarker
from datetime import time, timedelta
import streamlit.components.v1 as components
import sys, os

# 🔄 Pfad zur zentralen DB-Verbindung aus db.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from db import get_db_connection  # zentrale Verbindung

# Farben pro Nutzergruppe
nutzergruppen_farben = {
    "Schulsport": "blue",
    "Wettkampfsport": "red",
    "Lehrgänge": "orange",
    "Breitensport": "green",
    "Gesundheitssport": "purple",
    "Kurse": "cadetblue",
    "Allg. Schüler-Sportgem.": "darkblue",
    "Lehrerarbeitsgemein": "lightgray",
    "Dienstsport": "black",
    "Behindertensport": "pink",
    "Lehrerfortbildung": "darkred",
    "Seniorensport": "lightgreen",
    "außersp. Veranstaltungen": "darkgreen"
}

# Seiteneinstellungen
st.set_page_config(page_title="Nutzergruppen-Karte", layout="wide")
st.title("Belegung nach Nutzergruppen – farblich dargestellt")

col1, col2 = st.columns([3, 1])

# 🎛 UI-Auswahl
with col1:
    wochentag_anzeige = st.selectbox("Wochentag auswählen", [
        "Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"
    ])
    wochentag_map = {
        "Montag": "Mo", "Dienstag": "Di", "Mittwoch": "Mi",
        "Donnerstag": "Do", "Freitag": "Fr", "Samstag": "Sa", "Sonntag": "So"
    }
    wochentag_sql = wochentag_map[wochentag_anzeige]

    zeit = st.slider("Uhrzeit auswählen", min_value=time(6, 0), max_value=time(22, 0),
                     value=time(16, 0), step=timedelta(minutes=15))
    zeit_str = zeit.strftime("%H:%M:%S")

# 📥 Belegungsdaten mit Nutzergruppe + Tätigkeit
def lade_belegungen_mit_farbe(wochentag, zeit):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    query = """
        SELECT DISTINCT g.breitengrad, g.laengengrad,
                        b.bereich, b.nutzer_gruppen, b.taetigkeit
        FROM belegungsplan b
        JOIN segmente s ON b.segment_id = s.id
        JOIN adressen a ON s.einrichtung_id = a.einrichtung_id
        JOIN geodaten g ON a.id = g.adressen_id
        WHERE b.wochentag = %s
          AND b.start <= %s
          AND b.ende > %s
          AND b.bereich IS NOT NULL
    """
    cursor.execute(query, (wochentag, zeit, zeit))
    daten = cursor.fetchall()
    cursor.close()
    db.close()
    return daten

# 🗺️ Karte mit farbigen Markern & Popups
def zeige_karte_farbig(daten):
    m = Map(location=[51.9607, 7.6261], zoom_start=12)

    for eintrag in daten:
        lat = eintrag["breitengrad"]
        lon = eintrag["laengengrad"]
        bereich = eintrag["bereich"]
        gruppe = eintrag["nutzer_gruppen"] or "Unbekannt"
        taetigkeit = eintrag["taetigkeit"] or "Keine Angabe"
        farbe = nutzergruppen_farben.get(bereich, "gray")

        popup_text = f"""
        <b>{bereich}</b><br>
        {gruppe}<br>
        <i>{taetigkeit}</i>
        """

        CircleMarker(
            location=[lat, lon],
            radius=8,
            popup=popup_text,
            color=farbe,
            fill=True,
            fill_opacity=0.7
        ).add_to(m)

    m.save("nutzergruppen_map.html")
    components.html(open("nutzergruppen_map.html", "r", encoding="utf-8").read(), height=600)

# ℹ️ Legende anzeigen
def zeige_glossar():
    st.markdown("### 🗂️ Legende – Nutzergruppen")
    for gruppe, farbe in nutzergruppen_farben.items():
        st.markdown(f"""
        <div style='display:flex;align-items:center;margin-bottom:6px;'>
            <div style='width:20px;height:20px;background-color:{farbe};margin-right:10px;border-radius:50%;border:1px solid #444;'></div>
            {gruppe}
        </div>
        """, unsafe_allow_html=True)

# 🔄 Daten abrufen & anzeigen
with col1:
    daten = lade_belegungen_mit_farbe(wochentag_sql, zeit_str)
    if daten:
        zeige_karte_farbig(daten)
    else:
        st.info("Keine Belegungen zum gewählten Zeitpunkt gefunden.")

with col2:
    zeige_glossar()
