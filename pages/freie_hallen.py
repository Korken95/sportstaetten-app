import streamlit as st
from datetime import time
import mysql.connector
import folium
import streamlit.components.v1 as components

st.set_page_config(page_title="Freie Hallen", layout="wide")

st.title("🏟️ Freie Hallen anzeigen")

# UI
wochentag_anzeige = st.selectbox("Wochentag auswählen", [
    "Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"
])
uhrzeit = st.time_input("Uhrzeit auswählen", value=time(16, 0))

wochentag_map = {
    "Montag": "Mo", "Dienstag": "Di", "Mittwoch": "Mi",
    "Donnerstag": "Do", "Freitag": "Fr", "Samstag": "Sa", "Sonntag": "So"
}
wochentag_sql = wochentag_map[wochentag_anzeige]

def get_freie_einrichtungen(wochentag, uhrzeit):
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Techlabs#2025",
        database="techlabs_projekt"
    )
    cursor = db.cursor(dictionary=True)
    zeit_str = uhrzeit.strftime("%H:%M:%S")
    query = """
        SELECT e.einrichtung_id
        FROM (
            SELECT DISTINCT einrichtung_id FROM segmente
        ) AS e
        WHERE NOT EXISTS (
            SELECT 1
            FROM segmente s
            JOIN belegungsplan b ON b.segment_id = s.id
            WHERE s.einrichtung_id = e.einrichtung_id
              AND b.wochentag = %s
              AND b.start <= %s
              AND b.ende > %s
        );
    """
    cursor.execute(query, (wochentag, zeit_str, zeit_str))
    freie = cursor.fetchall()
    cursor.close()
    db.close()
    return [f["einrichtung_id"] for f in freie]

def lade_geodaten(freie_ids):
    if not freie_ids:
        return []
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Techlabs#2025",
        database="techlabs_projekt"
    )
    cursor = db.cursor(dictionary=True)
    format_strings = ','.join(['%s'] * len(freie_ids))
    query = f"""
        SELECT g.breitengrad, g.laengengrad, a.strasse, a.hausnr, a.plz, a.ort
        FROM geodaten g
        JOIN adressen a ON g.adressen_id = a.id
        WHERE a.einrichtung_id IN ({format_strings})
    """
    cursor.execute(query, freie_ids)
    daten = cursor.fetchall()
    cursor.close()
    db.close()
    return daten

def zeige_karte(daten):
    m = folium.Map(location=[51.9607, 7.6261], zoom_start=12)
    for eintrag in daten:
        adresse = f"{eintrag['strasse']} {eintrag['hausnr']}, {eintrag['plz']} {eintrag['ort']}"
        folium.Marker(
            location=[eintrag["breitengrad"], eintrag["laengengrad"]],
            popup=adresse,
            icon=folium.Icon(color="green")
        ).add_to(m)
    m.save("karte.html")
    components.html(open("karte.html", "r", encoding="utf-8").read(), height=600)

# Aktion
if st.button("Freie Hallen anzeigen"):
    freie_ids = get_freie_einrichtungen(wochentag_sql, uhrzeit)
    if freie_ids:
        daten = lade_geodaten(freie_ids)
        zeige_karte(daten)
    else:
        st.info("Keine freien Hallen zum ausgewählten Zeitpunkt gefunden.")
