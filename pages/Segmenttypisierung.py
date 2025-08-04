import streamlit as st
import pandas as pd
import numpy as np
import sys, os
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

# DB Connection laden
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from db import get_db_connection

st.set_page_config(page_title="Ähnliche Segmente vergleichen", layout="wide")
st.title("Ähnliche Segmente vergleichen")

st.markdown("""
### Was zeigt diese Analyse?
- Vergleicht **Größe** (Länge, Breite, Fläche) und **Nutzungsvielfalt** (Sportarten & Bereiche)
- Findet automatisch Segmente, die für ähnliche Sportarten geeignet sind
- Hilft bei **Planung, Umbuchungen und Typisierung von Hallen**
""")

# Segmentdaten inkl. Einrichtung laden
def lade_segmentdaten():
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    query = """
        SELECT s.id AS segment_id,
               s.name AS segment_name,
               e.name AS einrichtung_name,
               s.laenge,
               s.breite,
               s.flaeche,
               COUNT(DISTINCT b.taetigkeit) AS sportarten_vielfalt,
               COUNT(DISTINCT b.bereich) AS bereichs_vielfalt
        FROM segmente s
        JOIN einrichtungen e ON e.id = s.einrichtung_id
        LEFT JOIN belegungsplan b ON b.segment_id = s.id
        GROUP BY s.id, s.name, e.name, s.laenge, s.breite, s.flaeche
    """
    cursor.execute(query)
    daten = cursor.fetchall()
    cursor.close()
    db.close()
    return pd.DataFrame(daten)

df = lade_segmentdaten()

if df.empty:
    st.warning("Keine Segmentdaten gefunden.")
    st.stop()

# Typen konvertieren
for col in ["laenge", "breite", "flaeche"]:
    df[col] = df[col].astype(float)
df["sportarten_vielfalt"] = df["sportarten_vielfalt"].astype(int)
df["bereichs_vielfalt"] = df["bereichs_vielfalt"].astype(int)

# Features
features = df[["laenge", "breite", "flaeche", "sportarten_vielfalt", "bereichs_vielfalt"]]
scaler = StandardScaler()
X_scaled = scaler.fit_transform(features)

# KMeans Cluster für Typisierung
kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
df["segment_typ"] = kmeans.fit_predict(X_scaled)

# Segmentauswahl mit Name + Einrichtung
df["display_name"] = df.apply(lambda x: f"{x['segment_name']} – {x['einrichtung_name']}", axis=1)
selected_display = st.selectbox("Segment auswählen", df["display_name"])
selected_segment = df[df["display_name"] == selected_display]["segment_id"].iloc[0]
selected_data = df[df["segment_id"] == selected_segment].iloc[0]

# 📍 Einrichtung & Adresse des ausgewählten Segments laden
db = get_db_connection()
cursor = db.cursor(dictionary=True)
cursor.execute("""
    SELECT e.name AS einrichtung_name, e.typ, a.strasse, a.plz, a.ort
    FROM segmente s
    JOIN einrichtungen e ON e.id = s.einrichtung_id
    JOIN adressen a ON a.einrichtung_id = e.id
    WHERE s.id = %s
""", (int(selected_segment),))   # Fix hier

einr_info = cursor.fetchone() or {
    "einrichtung_name": "Unbekannt",
    "typ": "N/A",
    "strasse": "-",
    "plz": "-",
    "ort": "-"
}

# Distanzberechnung für Ähnlichkeiten
df["distanz"] = np.linalg.norm(
    X_scaled - X_scaled[df.index[df["segment_id"] == selected_segment][0]], axis=1
)
empfehlungen = df.sort_values("distanz").head(6)

# Ausgewähltes Segment ausführlich darstellen
st.markdown(f"""
### Ausgewähltes Segment:
**{selected_data['segment_name']}** (ID {selected_segment})  
**Einrichtung:** {einr_info['einrichtung_name']} ({einr_info['typ']})  
**Adresse:** {einr_info['strasse']}, {einr_info['plz']} {einr_info['ort']}  
**Fläche:** {selected_data['flaeche']:.1f} m² (L {selected_data['laenge']} × B {selected_data['breite']} m)  
**Sportartenvielfalt:** {selected_data['sportarten_vielfalt']}  
**Automatischer Segment-Typ:** {selected_data['segment_typ']}
""")

# Ähnliche Segmente mit Kontext ausgeben
st.markdown("### Ähnliche Segmente (nach Größe & Nutzung):")

for _, row in empfehlungen.iterrows():
    if row["segment_id"] != selected_segment:
        # Einrichtung zu diesem Segment laden
        cursor.execute("""
            SELECT e.name AS einrichtung_name, e.typ, a.strasse, a.plz, a.ort
            FROM segmente s
            JOIN einrichtungen e ON e.id = s.einrichtung_id
            JOIN adressen a ON a.einrichtung_id = e.id
            WHERE s.id = %s
        """, (int(row["segment_id"]),))   # Fix hier

        einr = cursor.fetchone() or {
            "einrichtung_name": "Unbekannt",
            "typ": "N/A",
            "strasse": "-",
            "plz": "-",
            "ort": "-"
        }

        flaeche_diff = abs(selected_data["flaeche"] - row["flaeche"])

        st.markdown(f"""
        #### 🔗 Segment {row['segment_id']} – {row['segment_name']}
        **Einrichtung:** {einr['einrichtung_name']} ({einr['typ']})  
        **Adresse:** {einr['strasse']}, {einr['plz']} {einr['ort']}  
        **Fläche:** {row['flaeche']:.1f} m² (_Abweichung: {flaeche_diff:.1f} m²_)  
        **Sportartenvielfalt:** {row['sportarten_vielfalt']}  
        **Segment-Typ:** {row['segment_typ']}  

        **Warum empfohlen:** Ähnliche Fläche und ähnliche Vielfalt an Sportarten und Nutzungen.
        """)
        st.markdown("---")

cursor.close()
db.close()
