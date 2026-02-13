import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. Seiteneinstellungen
st.set_page_config(page_title="CS Efficiency Dashboard", layout="wide")

st.title("🚀 CS & Engineering Alignment Dashboard")
st.markdown("---")

# 2. Verbindung zu Google Sheets
# Ersetze den Link durch deinen "Jeder kann lesen"-Link aus Google Sheets
url = "https://docs.google.com/spreadsheets/d/14I3ru-sF5Q889NYBzUJDyUzLeIHN8G8ZFwzk78IOCKM/edit?usp=sharing"

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=url)
    
    # --- SIDEBAR / FILTER ---
    st.sidebar.header("Filter")
    selected_owner = st.sidebar.multiselect("Mitarbeiter (Owner)", options=df['owner'].unique(), default=df['owner'].unique())
    selected_prio = st.sidebar.multiselect("Priorität", options=df['priority'].unique(), default=df['priority'].unique())

    # Daten filtern
    filtered_df = df[(df['owner'].isin(selected_owner)) & (df['priority'].isin(selected_prio))]

    # --- METRIKEN ---
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Tickets Gesamt", len(filtered_df))
    with col2:
        # Beispiel: Wie viele Tickets sind 3rd Level?
        eng_tickets = len(filtered_df[filtered_df['Support_Level'] == '3rd Level'])
        st.metric("Engineering Tickets", eng_tickets)
    with col3:
        # Zeitersparnis-Platzhalter
        st.metric("CS Zeit-Gewinn", "ca. 40h/Monat")

    st.markdown("---")

    # --- TABELLE MIT LINKS ---
    st.subheader("📋 Ticket-Liste & Direkt-Bearbeitung")
    
    # HubSpot Link Logik (Platzhalter ID)
    portal_id = "123456789" 
    filtered_df['Link'] = filtered_df['ticket_id'].apply(lambda x: f"https://app.hubspot.com/contacts/{portal_id}/ticket/{x}")

    # Tabelle anzeigen
    st.dataframe(
        filtered_df[['priority', 'Support_Level', 'subject', 'owner', 'Link']],
        column_config={
            "Link": st.column_config.LinkColumn("In HubSpot öffnen", display_text="Bearbeiten ↗️")
        },
        hide_index=True,
        use_container_width=True
    )

except Exception as e:
    st.error("Verbindung zum Google Sheet noch nicht konfiguriert.")
    st.info("Bitte stelle sicher, dass die URL in der streamlit_app.py korrekt ist und das Sheet auf 'Jeder mit dem Link kann lesen' steht.")


import streamlit as st
import pandas as pd
import plotly.express as px

# --- DATEN-AUFBEREITUNG ---
# Wir wandeln die Spalte "Created" in echte Datumswerte um
df['Created'] = pd.to_datetime(df['Created'], errors='coerce')

# Neue Spalte für das Monats-Format (für das Liniendiagramm)
df['Monat'] = df['Created'].dt.strftime('%Y-%m') 

# --- GRAFIKEN ---
st.markdown("---")
col_left, col_right = st.columns(2)

with col_left:
    st.markdown("### 📊 Tickets nach Support-Level")
    # Zähle die Tickets pro Support_Level (basierend auf gefilterten Daten)
    level_counts = filtered_df['Support_Level'].value_counts().reset_index()
    level_counts.columns = ['Level', 'Anzahl']
    
    # Balkendiagramm
    fig_bar = px.bar(
        level_counts, 
        x='Level', 
        y='Anzahl', 
        color='Level',
        color_discrete_map={'1st Level': '#00b4d8', '2nd Level': '#0077b6', '3rd Level': '#03045e'}
    )
    st.plotly_chart(fig_bar, use_container_width=True)

with col_right:
    st.markdown("### 📈 Ticket-Trend pro Monat")
    # Wir zählen die Tickets pro Monat (sortiert nach Datum)
    monthly_counts = df.groupby('Monat').size().reset_index(name='Anzahl').sort_values('Monat')
    
    # Liniendiagramm
    fig_line = px.line(
        monthly_counts, 
        x='Monat', 
        y='Anzahl',
        markers=True
    )
    fig_line.update_traces(line_color='#ff7a59', line_width=3) # HubSpot Orange
    st.plotly_chart(fig_line, use_container_width=True)

# --- TABELLE ---
st.markdown("### 📋 Aktuelle Tickets")
# In der Tabelle zeigen wir das Datum schön formatiert an
filtered_df['Datum'] = filtered_df['Created'].dt.strftime('%d.%m.%Y')

display_cols = ['Datum', 'Support_Level', 'subject', 'owner', 'Link']
st.dataframe(
    filtered_df[display_cols],
    column_config={
        "Link": st.column_config.LinkColumn("HubSpot", display_text="Öffnen ↗️")
    },
    hide_index=True,
    use_container_width=True
)
