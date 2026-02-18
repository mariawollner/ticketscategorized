import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# --- 1. KONFIGURATION ---
# Ersetze den Link und die ID mit deinen Daten
SHEET_URL = "https://docs.google.com/spreadsheets/d/14I3ru-sF5Q889NYBzUJDyUzLeIHN8G8ZFwzk78IOCKM/edit?usp=sharing"
HUBSPOT_PORTAL_ID = "1234567" 

def get_csv_url(url):
    if "/edit" in url:
        return url.split("/edit")[0] + "/export?format=csv"
    return url

def calculate_business_hours(start, end):
    """Berechnet die Arbeitsstunden zwischen zwei Zeitstempeln ohne Wochenenden."""
    if pd.isna(start) or pd.isna(end) or start > end:
        return np.nan
    # Business Days (Mo-Fr) zählen
    bdays = len(pd.bdate_range(start, end)) - 1
    # Berechnung der Stunden
    total_hours = (bdays * 24) + (end.hour - start.hour) + (end.minute - start.minute) / 60
    return max(0, total_hours)

@st.cache_data(ttl=600)
def load_data():
    csv_url = get_csv_url(SHEET_URL)
    # Erst als String laden, um Komma-Fehler zu vermeiden
    df = pd.read_csv(csv_url, dtype=str)
    
    # Numerische Spalten korrigieren (Komma -> Punkt)
    for col in ['confidence_score', 'predicted_level']:
        if col in df.columns:
            df[col] = df[col].str.replace(',', '.').pipe(pd.to_numeric, errors='coerce')

    # Datumskonvertierung
    df['created'] = pd.to_datetime(df['created'], errors='coerce')
    if 'closed' in df.columns:
        df['closed'] = pd.to_datetime(df['closed'], errors='coerce')
        # Netto-Arbeitszeit berechnen
        df['business_hours'] = df.apply(lambda row: calculate_business_hours(row['created'], row['closed']), axis=1)
    
    # HubSpot Link generieren
    df['hubspot_url'] = df['ticket_id'].apply(lambda x: f"https://app.hubspot.com/contacts/{HUBSPOT_PORTAL_ID}/ticket/{x}")
    
    # Accuracy-Extraktion (Zahl aus owner_role extrahieren)
    df['role_num'] = df['owner_role'].str.extract('(\d+)').astype(float)
    
    return df

# --- 2. LAYOUT ---
st.set_page_config(page_title="CS Ticket Dashboard", layout="wide")
st.title("🎫 Customer Success Ticket Dashboard")

try:
    data = load_data()

    # --- 3. OPERATIONAL VIEW ---
    st.header("Operational View")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        owner_list = sorted(data['owner'].dropna().unique())
        owner_f = st.multiselect("Filter by Owner", options=owner_list)
    with c2:
        status_list = sorted(data['status'].dropna().unique())
        status_f = st.multiselect("Filter by Status", options=status_list)
    with c3:
        level_list = sorted([int(x) for x in data['predicted_level'].dropna().unique()])
        level_f = st.multiselect("Filter by Predicted Level", options=level_list)

    # Filter anwenden
    df_filtered = data.copy()
    if owner_f:
        df_filtered = df_filtered[df_filtered['owner'].isin(owner_f)]
    if status_f:
        df_filtered = df_filtered[df_filtered['status'].isin(status_f)]
    if level_f:
        df_filtered = df_filtered[df_filtered['predicted_level'].isin(level_f)]

    # Tabelle anzeigen
    st.dataframe(
        df_filtered[['subject', 'created', 'predicted_level', 'owner', 'status', 'routing_status', 'hubspot_url']],
        column_config={
            "hubspot_url": st.column_config.LinkColumn("HubSpot Link", display_text="Open Ticket"),
            "created": st.column_config.DatetimeColumn("Created At", format="DD.MM.YYYY, HH:mm"),
            "predicted_level": st.column_config.NumberColumn("Level", format="%d")
        },
        use_container_width=True,
        hide_index=True
    )

    st.markdown("---")

    # --- 4. STRATEGIC INSIGHTS ---
    st.header("📈 Strategic Insights")

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    
    # KPIs berechnen
    if 'business_hours' in data.columns:
        avg_h = data['business_hours'].mean()
        kpi1.metric("Avg. Resolution (Mo-Fr)", f"{avg_h:.1f}h")

    if 'confidence_score' in data.columns:
        kpi2.metric("Avg. Confidence", f"{data['confidence_score'].mean():.1%}")

    correct = (data['role_num'] == data['predicted_level']).sum()
    acc = correct / len(data) if len(data) > 0 else 0
    kpi3.metric("Routing Accuracy", f"{acc:.1%}")

    l3_share = (data['predicted_level'] == 3).sum() / len(data) if len(data) > 0 else 0
    kpi4.metric("Level 3 Share", f"{l3_share:.1%}")

    # Visualisierungen
    col_a, col_b = st.columns(2)
    with col_a:
        # Hier lag der Syntax-Fehler - jetzt repariert:
        data['month'] = data['created'].dt.strftime('%Y-%m')
        monthly_counts = data.groupby('month').size().reset_index(name='Tickets')
        fig_line = px.line(monthly_counts, x='month', y='Tickets', title="Ticket Volume per Month", markers=True)
        st.plotly_chart(fig_line, use_container_width=True)

    with col_b:
        fig_pie = px.pie(data, names='predicted_level', title="Level Distribution", hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)

    # Heatmap für Strategen
    st.subheader("Deep Dive: AI Prediction vs. Human Assignment")
    if not data['owner_role'].isnull().all():
        matrix = pd.crosstab(data['predicted_level'], data['owner_role'])
        fig_heat = px.imshow(matrix, text_auto=True, color_continuous_scale='RdYlGn', labels=dict(x="Actual Role", y="Predicted Level"))
        st.plotly_chart(fig_heat, use_container_width=True)

except Exception as e:
    st.error(f"Ein Fehler ist aufgetreten: {
