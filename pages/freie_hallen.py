import streamlit as st
import folium
import streamlit.components.v1 as components
from datetime import time
import sys, os

# 🔄 Zugriff auf db.py im Projekt-Hauptverzeichnis
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from db import get_db_connection

st.set_page_config(page_title="Freie Hallen", layout="wide")
st.title("Freie Hallen anzeigen")

# 📅 UI: Wochentag, Uhrzeit & Segmentfilter
wochentag_anzeige = st.selectbox("Wochentag auswählen", [
    "Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"
])
uhrzeit = st.time_input("Uhrzeit auswählen", value=time(16, 0))
segment_filter = st.selectbox("Nur Hallen mit wie vielen Segmenten?", [1, 2, 3, 4])

# 🔄 Doppelte Mapping-Lösung (wegen „Montag“ vs „Mo“)
wochentag_map_verfugbarkeit = {
    "Montag": "Montag", "Dienstag": "Dienstag", "Mittwoch": "Mittwoch",
    "Donnerstag": "Donnerstag", "Freitag": "Freitag", "Samstag": "Samstag", "Sonntag": "Sonntag"
}
wochentag_map_belegung = {
    "Montag": "Mo", "Dienstag": "Di", "Mittwoch": "Mi",
    "Donnerstag": "Do", "Freitag": "Fr", "Samstag": "Sa", "Sonntag": "So"
}

v_tag = wochentag_map_verfugbarkeit[wochentag_anzeige]
b_tag = wochentag_map_belegung[wochentag_anzeige]

# 🧠 Freie Einrichtungen mit Segmentfilter
def get_freie_einrichtungen(wochentag_v, wochentag_b, uhrzeit, segmentanzahl):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    zeit_str = uhrzeit.strftime("%H:%M:%S")

    query = """
SELECT 
    e.id AS einrichtung_id,
    e.name,
    e.typ,
    COUNT(DISTINCT s.id) AS verfuegbare_segmente
FROM einrichtungen e
JOIN segmente s ON s.einrichtung_id = e.id
JOIN verfugbarkeit v ON v.segment_id = s.id
WHERE v.wochentag = %s
  AND v.start <= %s
  AND v.ende > %s
  AND NOT EXISTS (
      SELECT 1 FROM belegungsplan b
      JOIN segmente s2 ON b.segment_id = s2.id
      WHERE b.segment_id = s.id
        AND b.wochentag = %s
        AND b.start <= %s
        AND b.ende > %s
        AND s2.name = 'Gesamtspielfläche'
  )
GROUP BY e.id
HAVING COUNT(DISTINCT s.id) = %s;
    """
    params = (wochentag_v, zeit_str, zeit_str, wochentag_b, zeit_str, zeit_str, segmentanzahl)
    print("DEBUG PARAMS:", params)  # ✅ Debug-Ausgabe
    cursor.execute(query, params)
    freie = cursor.fetchall()
    cursor.close()
    db.close()
    return freie

# 📍 Geodaten & Adressinfos laden
def lade_geodaten_infos(einrichtung_ids):
    if not einrichtung_ids:
        return []

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    format_strings = ','.join(['%s'] * len(einrichtung_ids))

    query = f"""
        SELECT a.einrichtung_id, g.breitengrad, g.laengengrad,
               a.strasse, a.hausnr, a.plz, a.ort
        FROM geodaten g
        JOIN adressen a ON g.adressen_id = a.id
        WHERE a.einrichtung_id IN ({format_strings})
    """
    cursor.execute(query, einrichtung_ids)
    daten = cursor.fetchall()
    cursor.close()
    db.close()
    return daten

# 🗺️ Karte mit Popup-Infos (Typ, Name, Adresse)
def zeige_karte(freie_infos, geo_infos):
    m = folium.Map(location=[51.9607, 7.6261], zoom_start=12)
    geo_dict = {g["einrichtung_id"]: g for g in geo_infos}

    for einr in freie_infos:
        einr_id = einr["einrichtung_id"]
        geo = geo_dict.get(einr_id)
        if geo:
            popup = f"""
            <b>{einr['name']}</b><br>
            Typ: {einr['typ']}<br>
            Adresse: {geo['strasse']} {geo['hausnr']}, {geo['plz']} {geo['ort']}<br>
            Verfügbare Segmente: {einr['verfuegbare_segmente']}
            """
            folium.Marker(
                location=[geo["breitengrad"], geo["laengengrad"]],
                popup=popup,
                icon=folium.Icon(color="green")
            ).add_to(m)

    m.save("karte.html")
    components.html(open("karte.html", "r", encoding="utf-8").read(), height=600)

# 🚀 Aktion
if st.button("Freie Hallen anzeigen"):
    freie_infos = get_freie_einrichtungen(v_tag, b_tag, uhrzeit, segment_filter)
    ids = [e["einrichtung_id"] for e in freie_infos]
    if ids:
        geo_infos = lade_geodaten_infos(ids)
        zeige_karte(freie_infos, geo_infos)
    else:
        st.info("Keine freien Hallen mit dieser Segmentanzahl gefunden.")
