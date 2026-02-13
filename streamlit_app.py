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


import plotly.express as px

# --- DATEN-VORBEREITUNG FÜR DAS LINIENDIAGRAMM ---
# Wir wandeln das Datum in ein Monats-Format um (z.B. 2024-01)
df['month'] = pd.to_datetime(df['created_at']).dt.to_period('M').astype(str)
tickets_per_month = df.groupby('month').size().reset_index(name='Anzahl')

# --- LAYOUT: ZWEI SPALTEN FÜR DIE CHARTS ---
col_left, col_right = st.columns(2)

with col_left:
    st.markdown("### 📊 Tickets pro Level")
    # Zähle die Tickets pro Support_Level
    level_counts = filtered_df['Support_Level'].value_counts().reset_index()
    level_counts.columns = ['Support_Level', 'Anzahl']
    
    # Balkendiagramm (Horizontal ist oft schöner für Level)
    fig_bar = px.bar(
        level_counts, 
        x='Anzahl', 
        y='Support_Level', 
        orientation='h',
        color='Support_Level',
        color_discrete_map={'1st Level': '#00b4d8', '2nd Level': '#0077b6', '3rd Level': '#03045e'} # Blau-Töne
    )
    st.plotly_chart(fig_bar, use_container_width=True)

with col_right:
    st.markdown("### 📈 Ticket-Trend pro Monat")
    # Liniendiagramm
    fig_line = px.line(
        tickets_per_month, 
        x='month', 
        y='Anzahl',
        markers=True,
        title="Eingangsvolumen"
    )
    # Optik-Tuning für das Liniendiagramm
    fig_line.update_traces(line_color='#ff7a59') # HubSpot-Orange
    st.plotly_chart(fig_line, use_container_width=True)
