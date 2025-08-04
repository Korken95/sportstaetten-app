import streamlit as st
import pandas as pd
import mysql.connector
import sys, os

# 🔄 DB Connection importieren
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from db import get_db_connection

st.set_page_config(page_title="Auslastungsanalyse", layout="wide")
st.title("Auslastungs-Analyse pro Halle")

# 📅 Auswahl für Wochentag oder "Alle"
wochentage = ["Alle", "Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
auswahl_tag = st.selectbox("Wochentag auswählen", wochentage)

# 🔍 Daten laden
def lade_auslastung(wochentag=None):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # SQL: Summiere Dauer aus belegungsplan
    query = """
        SELECT e.id AS einrichtung_id, e.name,
               b.wochentag,
               SUM(TIME_TO_SEC(b.dauer))/60 AS belegte_minuten
        FROM belegungsplan b
        JOIN segmente s ON b.segment_id = s.id
        JOIN einrichtungen e ON s.einrichtung_id = e.id
        GROUP BY e.id, b.wochentag
    """
    cursor.execute(query)
    belegung = cursor.fetchall()

    # SQL: Summiere verfügbare Zeit aus verfugbarkeit
    query2 = """
        SELECT e.id AS einrichtung_id, e.name,
               v.wochentag,
               SUM(TIME_TO_SEC(TIMEDIFF(v.ende, v.start)))/60 AS verfuegbare_minuten
        FROM verfugbarkeit v
        JOIN segmente s ON v.segment_id = s.id
        JOIN einrichtungen e ON s.einrichtung_id = e.id
        GROUP BY e.id, v.wochentag
    """
    cursor.execute(query2)
    verfuegbarkeit = cursor.fetchall()

    db.close()

    df_belegung = pd.DataFrame(belegung)
    df_verf = pd.DataFrame(verfuegbarkeit)

    st.write("Belegung", df_belegung.head())
    st.write("Verfügbarkeit", df_verf.head())

    map_kurz_zu_lang = {
    "Mo": "Montag", "Di": "Dienstag", "Mi": "Mittwoch",
    "Do": "Donnerstag", "Fr": "Freitag", "Sa": "Samstag", "So": "Sonntag"
    }

    df_belegung["wochentag"] = df_belegung["wochentag"].replace(map_kurz_zu_lang)

    # Merge
    df = pd.merge(df_belegung, df_verf, on=["einrichtung_id", "name", "wochentag"])
    df["auslastung_%"] = (df["belegte_minuten"] / df["verfuegbare_minuten"]) * 100

    if wochentag and wochentag != "Alle":
        df = df[df["wochentag"] == wochentag]

    return df

# Daten anzeigen
df = lade_auslastung(auswahl_tag)
st.dataframe(df)

#Ranking
ranking = df.groupby("name")["auslastung_%"].mean().sort_values(ascending=False)
st.subheader("Ranking der Hallen (Durchschnitt über alle Tage)")
st.bar_chart(ranking)
