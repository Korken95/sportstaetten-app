import streamlit as st
import pandas as pd
import numpy as np
import mysql.connector
import sys, os
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import altair as alt

# 🔄 DB Connection importieren
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from db import get_db_connection

st.set_page_config(page_title="Clusteranalyse", layout="wide")
st.title("Clusteranalyse der Hallennutzung")

st.markdown("""
Diese Analyse zeigt **ähnliche Nutzungsmuster** von Hallen-Segmenten.
- **X-Achse:** Startzeit der Belegung (in Stunden)
- **Y-Achse:** Dauer der Belegung (in Minuten)
- **Farbe:** Cluster mit ähnlichem Verhalten
""")

#Daten laden
def lade_nutzungsdaten():
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    query = """
        SELECT b.segment_id,
               b.wochentag,
               TIME_TO_SEC(b.start)/3600 AS start_stunde,
               TIME_TO_SEC(b.dauer)/60 AS dauer_minuten,
               b.bereich
        FROM belegungsplan b
    """
    cursor.execute(query)
    daten = cursor.fetchall()
    db.close()
    return pd.DataFrame(daten)

df = lade_nutzungsdaten()

if df.empty:
    st.warning("Keine Daten für die Clusteranalyse gefunden.")
    st.stop()

# 🔧 Sicherstellen, dass numerische Spalten floats sind
df["start_stunde"] = df["start_stunde"].astype(float)
df["dauer_minuten"] = df["dauer_minuten"].astype(float)

# Bereich in numerischen Wert umwandeln
df["bereich_code"] = df["bereich"].astype("category").cat.codes

# Features für Clustering
features = df[["start_stunde", "dauer_minuten", "bereich_code"]]

# Normalisieren
scaler = StandardScaler()
X_scaled = scaler.fit_transform(features)

# Clusteranzahl wählbar
k = st.slider("Anzahl der Cluster (k)", 2, 6, 4)

# KMeans anwenden
kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
df["cluster"] = kmeans.fit_predict(X_scaled)

# Labels für Cluster automatisch basierend auf Mittelwert der Startzeit
cluster_labels = {}
for c in df["cluster"].unique():
    avg_start = df[df["cluster"] == c]["start_stunde"].mean()
    if avg_start < 12:
        cluster_labels[c] = "Vormittags-Nutzung"
    elif avg_start < 17:
        cluster_labels[c] = "Nachmittags-Nutzung"
    else:
        cluster_labels[c] = "Abend-Nutzung"

df["cluster_label"] = df["cluster"].map(cluster_labels)

# Tabelle mit Erklärung
st.subheader("📋 Daten mit Clusterzuordnung")
st.dataframe(df[["segment_id", "wochentag", "start_stunde", "dauer_minuten", "bereich", "cluster_label"]].head(50))

# Visualisierung
st.subheader("⏱️ Cluster-Visualisierung")
chart = alt.Chart(df).mark_circle(size=70).encode(
    x=alt.X("start_stunde", title="Startzeit (Stunden)"),
    y=alt.Y("dauer_minuten", title="Dauer (Minuten)"),
    color=alt.Color("cluster_label", title="Cluster"),
    tooltip=["wochentag", "bereich", "start_stunde", "dauer_minuten", "cluster_label"]
).interactive()

st.altair_chart(chart, use_container_width=True)

# Clustergrößen
st.subheader("📊 Clustergrößen")
cluster_counts = df["cluster_label"].value_counts().reset_index()
cluster_counts.columns = ["Cluster", "Anzahl"]
st.bar_chart(cluster_counts.set_index("Cluster"))
