import streamlit as st
import mysql.connector
import folium
from folium import Marker
from datetime import time, timedelta
import streamlit.components.v1 as components

def lade_verfuegbare_taetigkeiten():
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Techlabs#2025",
        database="techlabs_projekt"
    )
    cursor = db.cursor()
    cursor.execute("""
        SELECT DISTINCT taetigkeit
        FROM belegungsplan
        WHERE taetigkeit IS NOT NULL AND taetigkeit != ''
        ORDER BY taetigkeit ASC
    """)
    taetigkeiten = [row[0] for row in cursor.fetchall()]
    cursor.close()
    db.close()
    return taetigkeiten

# Seiteneinstellungen
st.set_page_config(page_title="Tätigkeit suchen", layout="wide")
st.title("🎯 Sportmöglichkeit nach Tätigkeit finden")

col1, col2 = st.columns([3, 1])

# UI-Auswahl
with col1:
    verfuegbare_taetigkeiten = lade_verfuegbare_taetigkeiten()
    taetigkeit = st.selectbox("Tätigkeit auswählen", verfuegbare_taetigkeiten)


    wochentag_anzeige = st.selectbox("Wochentag auswählen", [
        "Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"
    ])
    wochentag_map = {
        "Montag": "Mo", "Dienstag": "Di", "Mittwoch": "Mi",
        "Donnerstag": "Do", "Freitag": "Fr", "Samstag": "Sa", "Sonntag": "So"
    }
    wochentag_sql = wochentag_map[wochentag_anzeige]

    startzeit = st.slider("Startzeit (von)", min_value=time(6, 0), max_value=time(22, 0), value=time(16, 0))
    endzeit = st.slider("Endzeit (bis)", min_value=time(6, 0), max_value=time(22, 0), value=time(18, 0))

    start_str = startzeit.strftime("%H:%M:%S")
    end_str = endzeit.strftime("%H:%M:%S")

# Datenbankabfrage
def lade_hallen_mit_taetigkeit(taetigkeit, wochentag, start, ende):
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Techlabs#2025",
        database="techlabs_projekt"
    )
    cursor = db.cursor(dictionary=True)

    query = """
        SELECT DISTINCT g.breitengrad, g.laengengrad, b.start,
                        b.nutzer_gruppen, b.taetigkeit, a.strasse, a.hausnr, a.ort
        FROM belegungsplan b
        JOIN segmente s ON b.segment_id = s.id
        JOIN adressen a ON s.einrichtung_id = a.einrichtung_id
        JOIN geodaten g ON a.id = g.adressen_id
        WHERE b.wochentag = %s
          AND b.taetigkeit LIKE %s
          AND b.start >= %s
          AND b.start <= %s
    """
    params = (wochentag, f"%{taetigkeit}%", start, ende)
    cursor.execute(query, params)
    daten = cursor.fetchall()
    cursor.close()
    db.close()
    return daten

# Karte
def zeige_karte(daten):
    m = folium.Map(location=[51.9607, 7.6261], zoom_start=12)

    for eintrag in daten:
        popup_text = f"""
        <b>{eintrag['taetigkeit']}</b><br>
        {eintrag['nutzer_gruppen']}<br>
        🕒 Startzeit: {eintrag['start']}<br>
        {eintrag['strasse']} {eintrag['hausnr']}, {eintrag['ort']}
        """
        Marker(
            location=[eintrag["breitengrad"], eintrag["laengengrad"]],
            popup=popup_text,
            icon=folium.Icon(color="green")
        ).add_to(m)

    m.save("taetigkeit_map.html")
    components.html(open("taetigkeit_map.html", "r", encoding="utf-8").read(), height=600)

# Ausgabe
with col1:
    daten = lade_hallen_mit_taetigkeit(taetigkeit, wochentag_sql, start_str, end_str)
    if daten:
        zeige_karte(daten)
    else:
        st.info("Keine Hallen für diese Tätigkeit und Zeitspanne gefunden.")

with col2:
    st.markdown("### ℹ️ Hinweis")
    st.write("Die Karte zeigt alle Hallen, in denen **die gewählte Tätigkeit** innerhalb des Zeitbereichs **beginnt**.")
