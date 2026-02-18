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

@st.cache_data(ttl=60)
def load_data():
    csv_url = get_csv_url(SHEET_URL)
    df = pd.read_csv(csv_url, dtype=str)
    
    # Zeit-Konvertierung
    df['created'] = pd.to_datetime(df['created'], errors='coerce')
    if 'closed' in df.columns:
        df['closed'] = pd.to_datetime(df['closed'], errors='coerce')
        df['business_hours'] = df.apply(lambda row: calculate_business_hours(row['created'], row['closed']), axis=1)
    
    # Hilfsspalten für Monate
    if 'created' in df.columns:
        df['m_name'] = df['created'].dt.strftime('%B %Y')
        df['m_sort'] = df['created'].dt.strftime('%Y-%m')

    # Numerische Felder SÄUBERN (Wichtig für die Fehlervermeidung)
    if 'confidence_score' in df.columns:
        df['confidence_score'] = pd.to_numeric(df['confidence_score'].str.replace(',', '.'), errors='coerce')
    
    # Wir speichern die Level als saubere Strings für Diagramme
    df['predicted_level'] = df['predicted_level'].fillna("Unknown")
    
    if 'ticket_id' in df.columns:
        df['hubspot_url'] = df['ticket_id'].apply(lambda x: f"https://app.hubspot.com/contacts/{HUBSPOT_PORTAL_ID}/ticket/{x}")
    
    return df

# --- LAYOUT ---
st.set_page_config(page_title="CS Smart Dashboard", layout="wide")
st.title("🎫 Customer Success Smart Dashboard")

try:
    data = load_data()

    # --- 2. OPERATIONAL VIEW (Tabelle oben) ---
    st.header("Operational View")
    df_filtered = data.copy()
    
    # Einfache Filter
    c1, c2 = st.columns(2)
    with c1:
        owner_f = st.multiselect("Filter by Owner", options=sorted(data['owner'].dropna().unique()))
    with c2:
        level_f = st.multiselect("Filter by Level", options=sorted(data['predicted_level'].unique()))

    if owner_f: df_filtered = df_filtered[df_filtered['owner'].isin(owner_f)]
    if level_f: df_filtered = df_filtered[df_filtered['predicted_level'].isin(level_f)]

    st.dataframe(df_filtered[['subject', 'created', 'predicted_level', 'owner', 'status', 'hubspot_url']].head(100), use_container_width=True, hide_index=True)

    st.markdown("---")

    # --- 3. CUSTOMER SUCCESS INSIGHTS ---
    st.header("📊 Customer Success Insights")
    
    col_chart, col_top_owner = st.columns([3, 1])
    
    with col_chart:
        st.subheader("Avg. Resolution Time (Hours)")
        if 'business_hours' in data.columns:
            res_data = data.groupby(['m_sort', 'm_name', 'predicted_level'])['business_hours'].mean().reset_index()
            fig_res = px.bar(res_data.sort_values('m_sort'), x='m_name', y='business_hours', color='predicted_level', barmode='group', text_auto='.1f')
            st.plotly_chart(fig_res, use_container_width=True)

    with col_top_owner:
        st.subheader("Top 5 Owners")
        if 'm_sort' in data.columns:
            latest = data['m_sort'].max()
            top_5 = data[data['m_sort'] == latest]['owner'].value_counts().head(5).reset_index()
            top_5.columns = ['Owner', 'Tickets']
            st.table(top_5)

    col_a, col_b = st.columns(2)
    with col_a:
        vol_data = data.groupby(['m_sort', 'm_name', 'predicted_level']).size().reset_index(name='Tickets')
        st.plotly_chart(px.bar(vol_data.sort_values('m_sort'), x='m_name', y='Tickets', color='predicted_level', title="Monthly Volume"), use_container_width=True)
    with col_b:
        st.plotly_chart(px.pie(data, names='predicted_level', title="Complexity Distribution", hole=0.4), use_container_width=True)

    st.markdown("---")

    # --- 4. STRATEGIC INSIGHTS ---
    st.header("📈 Strategic Insights")
    k1, k2, k3 = st.columns(3)
    
    # Auto Route
    cov = (data['routing_score'].fillna("").str.lower().str.contains("auto").mean()) if 'routing_score' in data.columns else 0
    k1.metric("Auto Route Coverage", f"{cov:.1%}")

    # Engineering Noise (Sichere Berechnung ohne >= Fehler)
    noise = 0.0
    if 'predicted_level' in data.columns and 'owner_role' in data.columns:
        # Wir filtern rein über Strings, das ist sicherer
        l3_tickets = data[data['predicted_level'].str.contains("3", na=False)]
        if len(l3_tickets) > 0:
            # Wie viele davon wurden NICHT von einem L3 Owner gelöst?
            noise = (~l3_tickets['owner_role'].str.contains("3", na=False)).mean()
    k2.metric("Engineering Noise", f"{noise:.1%}")

    # AI Confidence
    conf = data['confidence_score'].mean() if 'confidence_score' in data.columns else 0
    k3.metric("Avg. AI Confidence", f"{conf:.1%}")

    st.subheader("Deep Dive: AI Prediction vs. Actual Human Assignment")
    st.plotly_chart(px.imshow(pd.crosstab(data['predicted_level'], data['owner_role']), text_auto=True, color_continuous_scale='Blues'), use_container_width=True)

except Exception as e:
    st.error(f"Kritischer Fehler: {e}")
