import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# --- 1. KONFIGURATION ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/14I3ru-sF5Q889NYBzUJDyUzLeIHN8G8ZFwzk78IOCKM/edit?usp=sharing"
HUBSPOT_PORTAL_ID = "1234567" 

def get_csv_url(url):
    if "/edit" in url:
        return url.split("/edit")[0] + "/export?format=csv"
    return url

def calculate_business_hours(start, end):
    if pd.isna(start) or pd.isna(end) or start > end:
        return np.nan
    bdays = len(pd.bdate_range(start, end)) - 1
    total_hours = (bdays * 24) + (end.hour - start.hour) + (end.minute - start.minute) / 60
    return max(0, total_hours)

@st.cache_data(ttl=300)
def load_data():
    csv_url = get_csv_url(SHEET_URL)
    df = pd.read_csv(csv_url, dtype=str)
    
    # Numerische Korrekturen
    if 'confidence_score' in df.columns:
        df['confidence_score'] = df['confidence_score'].str.replace(',', '.').pipe(pd.to_numeric, errors='coerce')
    
    # Zahlen aus Text extrahieren (z.B. "1st-line" -> 1.0)
    if 'predicted_level' in df.columns:
        df['level_num'] = df['predicted_level'].str.extract('(\d+)').astype(float)
    if 'owner_role' in df.columns:
        df['role_num'] = df['owner_role'].str.extract('(\d+)').astype(float)

    # Zeitformate
    df['created'] = pd.to_datetime(df['created'], errors='coerce')
    if 'closed' in df.columns:
        df['closed'] = pd.to_datetime(df['closed'], errors='coerce')
        df['business_hours'] = df.apply(lambda row: calculate_business_hours(row['created'], row['closed']), axis=1)
    
    # HubSpot Link
    if 'ticket_id' in df.columns:
        df['hubspot_url'] = df['ticket_id'].apply(lambda x: f"https://app.hubspot.com/contacts/{HUBSPOT_PORTAL_ID}/ticket/{x}")
    
    return df.sort_values(by='created', ascending=False)

# --- 2. LAYOUT ---
st.set_page_config(page_title="CS Smart Dashboard", layout="wide")
st.title("🎫 Customer Success Smart Dashboard")

try:
    data = load_data()

    # --- OPERATIONAL VIEW ---
    st.header("Operational View")
    c1, c2, c3 = st.columns(3)
    with c1: 
        owner_options = sorted(data['owner'].dropna().unique()) if 'owner' in data.columns else []
        owner_f = st.multiselect("Filter by Owner", options=owner_options)
    with c2: 
        status_options = sorted(data['status'].dropna().unique()) if 'status' in data.columns else []
        status_f = st.multiselect("Filter by Status", options=status_options)
    with c3: 
        level_options = sorted(data['predicted_level'].dropna().unique()) if 'predicted_level' in data.columns else []
        level_f = st.multiselect("Filter by Predicted Level", options=level_options)

    df_filtered = data.copy()
    if owner_f: df_filtered = df_filtered[df_filtered['owner'].isin(owner_f)]
    if status_f: df_filtered = df_filtered[df_filtered['status'].isin(status_f)]
    if level_f: df_filtered = df_filtered[df_filtered['predicted_level'].isin(level_f)]

    # Tabelle oben anzeigen
    st.dataframe(
        df_filtered[['subject', 'created', 'predicted_level', 'owner', 'status', 'hubspot_url']].head(100),
        column_config={
            "hubspot_url": st.column_config.LinkColumn("HubSpot Link", display_text="Open 🔗"),
            "created": st.column_config.DatetimeColumn("Created At", format="DD.MM.YYYY, HH:mm")
        },
        use_container_width=True, hide_index=True
    )

    st.markdown("---")

    # --- STRATEGIC INSIGHTS ---
    st.header("📈 Strategic Insights")
    k1, k2, k3, k4 = st.columns(4)
    
    # KPI 1: Bearbeitungszeit
    if 'business_hours' in data.columns:
        k1.metric("Avg. Resolution (Mo-Fr)", f"{data['business_hours'].mean():.1f}h")
    
    # KPI 2: Auto Route Coverage (basierend auf routing_score == "Auto-route")
    if 'routing_score' in data.columns:
        auto_route_count = (data['routing_score'] == "Auto-route").sum()
        coverage = auto_route_count / len(data) if len(data) > 0 else 0
        k2.metric("Auto Route Coverage", f"{coverage:.1%}", help="Tickets with 'Auto-route' in routing_score")

    # KPI 3: Engineering Noise
    if 'level_num' in data.columns and 'role_num' in data.columns:
        l3_pred = data[data['level_num'] == 3]
        noise = (l3_pred['role_num'] < 3).mean() if len(l3_pred) > 0 else 0
        k3.metric("Engineering Noise", f"{noise:.1%}", delta="Goal: <10%", delta_color="inverse")

    # KPI 4: AI Confidence
    if 'confidence_score' in data.columns:
        k4.metric("Avg. AI Confidence", f"{data['confidence_score'].mean():.1%}")

    # Diagramme
    ca, cb = st.columns(2)
    with ca:
        if 'created' in data.columns:
            data['m_name'] = data['created'].dt.strftime('%B %Y')
            data['m_sort'] = data['created'].dt.strftime('%Y-%m')
            m_lvl = data.groupby(['m_sort', 'm_name', 'predicted_level']).size().reset_index(name='Tickets').sort_values('m_sort')
            
            fig_bar = px.bar(
                m_lvl, x='m_name', y='Tickets', color='predicted_level', 
                title="Monthly Volume & Complexity", text_auto=True,
                color_discrete_map={"1st level": "#2ecc71", "2nd level": "#f1c40f", "3rd level": "#e74c3c"}
            )
            st.plotly_chart(fig_bar, use_container_width=True)
            
    with cb:
        if 'predicted_level' in data.columns:
            st.plotly_chart(px.pie(data, names='predicted_level', title="Total Complexity Distribution", hole=0.4), use_container_width=True)

except Exception as e:
    st.error(f"Error: {e}")
