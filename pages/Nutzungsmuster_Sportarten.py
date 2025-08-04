import streamlit as st
import pandas as pd
import numpy as np
import sys, os
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import altair as alt

# 🔄 DB Connection importieren
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from db import get_db_connection

st.set_page_config(page_title="Clusteranalyse Sportarten", layout="wide")
st.title("🤾‍♂️ Clusteranalyse der Sportarten-Nutzungsmuster")

st.markdown("""
### 📌 Was zeigt diese Analyse?
- Wir gruppieren **Sportarten nach ihrem zeitlichen Nutzungsverhalten**.
- Jede Farbe ist ein **Cluster**: Sportarten, die ähnlich oft zur gleichen Tageszeit und Dauer genutzt werden.
- Damit siehst du Muster wie z.B.:
    - **Schulsport** am Vormittag  
    - **Vereinssportarten** am Abend  
    - **Kurse & Gesundheitssport** tagsüber

➡️ **Achsen-Erklärung:**
- **X-Achse:** Startzeit der Belegung in Stunden  
- **Y-Achse:** Dauer der Nutzung in Minuten  
""")

# 📥 Daten laden
def lade_sportdaten():
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    query = """
        SELECT b.taetigkeit,
               b.wochentag_int,
               TIME_TO_SEC(b.start)/3600 AS start_stunde,
               TIME_TO_SEC(b.dauer)/60 AS dauer_minuten,
               b.bereich
        FROM belegungsplan b
        WHERE b.taetigkeit IS NOT NULL AND b.taetigkeit <> ''
    """
    cursor.execute(query)
    daten = cursor.fetchall()
    db.close()
    return pd.DataFrame(daten)

df = lade_sportdaten()

if df.empty:
    st.warning("Keine Daten mit Sportarten gefunden.")
    st.stop()

# 🔧 Werte konvertieren
df["start_stunde"] = df["start_stunde"].astype(float)
df["dauer_minuten"] = df["dauer_minuten"].astype(float)

# 🔄 Sportarten in Codes umwandeln
df["sportart_code"] = df["taetigkeit"].astype("category").cat.codes

# 📊 Features für Clustering
features = df[["sportart_code", "wochentag_int", "start_stunde", "dauer_minuten"]]

# 🔧 Normalisieren
scaler = StandardScaler()
X_scaled = scaler.fit_transform(features)

# 📌 Clusteranzahl
k = st.slider("Anzahl der Cluster (k)", 2, 8, 4, help="Wie viele Gruppen sollen gebildet werden?")

# 🤖 KMeans
kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
df["cluster"] = kmeans.fit_predict(X_scaled)

# 📋 Übersicht der Sportarten pro Cluster
st.subheader("📋 Übersicht: Welche Sportarten gehören zu welchem Cluster?")
cluster_groups = df.groupby("cluster")["taetigkeit"].unique()

for cluster_id, sportarten in cluster_groups.items():
    st.markdown(f"**Cluster {cluster_id+1}:**")
    st.write(", ".join(sorted(set(sportarten))))

# 📈 Visualisierung
st.subheader("⏱️ Visualisierung der Cluster (Startzeit vs. Dauer)")
chart = alt.Chart(df).mark_circle(size=70).encode(
    x=alt.X("start_stunde:Q", title="Startzeit der Nutzung (Stunden)"),
    y=alt.Y("dauer_minuten:Q", title="Dauer der Nutzung (Minuten)"),
    color=alt.Color("cluster:N", title="Cluster"),
    tooltip=["taetigkeit", "wochentag_int", "start_stunde", "dauer_minuten", "cluster"]
).interactive()

st.altair_chart(chart, use_container_width=True)

# 📊 Verteilung der Cluster
st.subheader("📊 Wie viele Belegungen pro Cluster?")
cluster_counts = df["cluster"].value_counts().reset_index()
cluster_counts.columns = ["Cluster", "Anzahl Belegungen"]
st.bar_chart(cluster_counts.set_index("Cluster"))
