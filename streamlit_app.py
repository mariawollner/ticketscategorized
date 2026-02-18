import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# --- 1. KONFIGURATION ---
# Dein Google Sheet Link (bereits eingefügt)
SHEET_URL = "https://docs.google.com/spreadsheets/d/14I3ru-sF5Q889NYBzUJDyUzLeIHN8G8ZFwzk78IOCKM/edit?usp=sharing"
# Deine HubSpot Portal ID (bitte hier anpassen, falls nötig)
HUBSPOT_PORTAL_ID = "1234567" 

def get_csv_url(url):
    """Wandelt den normalen Google Sheet Link in einen CSV-Export-Link um."""
    if "/edit" in url:
        return url.split("/edit")[0] + "/export?format=csv"
    return url

def calculate_business_hours(start, end):
    """Berechnet Arbeitsstunden ohne Samstage und Sonntage."""
    if pd.isna(start) or pd.isna(end) or start > end:
        return np.nan
    # Business Days (Mo-Fr)
    bdays = len(pd.bdate_range(start, end)) - 1
    # Kalkulation der Stunden (basiert auf 24h/Werktag)
    total_hours = (bdays * 24) + (end.hour - start.hour) + (end.minute - start.minute) / 60
    return max(0, total_hours)

@st.cache_data(ttl=300) # Aktualisiert die Daten alle 5 Minuten
def load_data():
    csv_url = get_csv_url(SHEET_URL)
    # Daten erst als Text laden, um Formatfehler zu vermeiden
    df = pd.read_csv(csv_url, dtype=str)
    
    # --- Datenbereinigung ---
    # 1. Numerische Werte (Komma zu Punkt)
    if 'confidence_score' in df.columns:
        df['confidence_score'] = df['confidence_score'].str.replace(',', '.').pipe(pd.to_numeric, errors='coerce')
    
    # 2. Level Extraktion (Zahl extrahieren aus "1st-line" oder "1st level")
    if 'predicted_level' in df.columns:
        df['level_num'] = df['predicted_level'].str.extract('(\d+)').astype(float)
    if 'owner_role' in df.columns:
        df['role_num'] = df['owner_role'].str.extract('(\d+)').astype(float)

    # 3. Datumskonvertierung
    df['created'] = pd.to_datetime(df['created'], errors='coerce')
    if 'closed' in df.columns:
        df['closed'] = pd.to_datetime(df['closed'], errors='coerce')
        # Business Hours berechnen
        df['business_hours'] = df.apply(lambda row: calculate_business_hours(row['created'], row['closed']), axis=1)
    
    # 4. HubSpot Link generieren
    if 'ticket_id' in df.columns:
        df['hubspot_url'] = df['ticket_id'].apply(lambda x: f"https://app.hubspot.com/contacts/{HUBSPOT_PORTAL_ID}/ticket/{x}")
    
    # Sortierung: Neueste oben
    return df.sort_values(by='created', ascending=False)

# --- 2. LAYOUT ---
st.set_page_config(page_title="Customer Success Ticket Dashboard", layout="wide")
st.title("🎫 Customer Success Ticket Dashboard")

try:
    data = load_data()

    # --- 3. OPERATIONAL VIEW (CS TEAM) ---
    st.header("Operational View")
    
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        owner_f = st.multiselect("Filter by Owner", options=sorted(data['owner'].dropna().unique()))
    with col_f2:
        status_f = st.multiselect("Filter by Status", options=sorted(data['status'].dropna().unique()))
    with col_f3:
        level_f = st.multiselect("Filter by Predicted Level", options=sorted(data['predicted_level'].dropna().unique()))

    # Filter anwenden
    df_filtered = data.copy()
    if owner_f: df_filtered = df_filtered[df_filtered['owner'].isin(owner_f)]
    if status_f: df_filtered = df_filtered[df_filtered['status'].isin(status_f)]
    if level_f: df_filtered = df_filtered[df_filtered['predicted_level'].isin(level_f)]

    # Tabelle anzeigen
    st.dataframe(
        df_filtered[['subject', 'created', 'predicted_level', 'owner', 'status', 'routing_status', 'hubspot_url']],
        column_config={
            "hubspot_url": st.column_config.LinkColumn("HubSpot Link", display_text="Open Ticket 🔗"),
            "created": st.column_config.DatetimeColumn("Created At", format="DD.MM.YYYY, HH:mm"),
        },
        use_container_width=True, hide_index=True
    )

    st.markdown("---")

    # --- 4. STRATEGIC INSIGHTS (STRATEGISTS) ---
    st.header("📈 Strategic Insights")

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    
    if 'business_hours' in data.columns:
        kpi1.metric("Avg. Resolution (Mo-Fr)", f"{data['business_hours'].mean():.1f}h")
    
    if 'confidence_score' in data.columns:
        kpi2.metric("Avg. Confidence Score", f"{data['confidence_score'].mean():.1%}")

    if 'role_num' in data.columns and 'level_num' in data.columns:
        correct = (data['role_num'] == data['level_num']).sum()
        acc = correct / len(data) if len(data) > 0 else 0
        kpi3.metric("Routing Accuracy", f"{acc:.1%}")

    if 'level_num' in data.columns:
        l3_share = (data['level_num'] == 3).sum() / len(data) if len(data) > 0 else 0
        kpi4.metric("Level 3 Share", f"{l3_share:.1%}")

    # Diagramme
    col_chart_a, col_chart_b = st.columns(2)

    with col_chart_a:
        if 'created' in data.columns:
            # Monatsnamen und Sortierung vorbereiten
            data['month_sort'] = data['created'].dt.strftime('%Y-%m')
            data['month_name'] = data['created'].dt.strftime('%B %Y')
            monthly = data.groupby(['month_sort', 'month_name']).size().reset_index(name='Tickets').sort_values('month_sort')
            
            fig_bar = px.bar(monthly, x='month_name', y='Tickets', title="Ticket Volume by Month", text_auto=True)
            st.plotly_chart(fig_bar, use_container_width=True)

    with col_chart_b:
        if 'predicted_level' in data.columns:
            fig_pie = px.pie(data, names='predicted_level', title="Total Level Distribution", hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)

    # Heatmap
    st.subheader("Deep Dive: AI Prediction vs. Human Assignment")
    if 'owner_role' in data.columns and 'predicted_level' in data.columns:
        matrix = pd.crosstab(data['predicted_level'], data['owner_role'])
        fig_heat = px.imshow(matrix, text_auto=True, color_continuous_scale='Blues', labels=dict(x="Actual Role", y="AI Prediction"))
        st.plotly_chart(fig_heat, use_container_width=True)

except Exception as e:
    st.error(f"Error loading dashboard: {e}")
