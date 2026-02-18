import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# --- 1. CONFIGURATION ---
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
    if 'confidence_score' in df.columns:
        df['confidence_score'] = df['confidence_score'].str.replace(',', '.').pipe(pd.to_numeric, errors='coerce')
    if 'predicted_level' in df.columns:
        df['level_num'] = df['predicted_level'].str.extract('(\d+)').astype(float)
    if 'owner_role' in df.columns:
        df['role_num'] = df['owner_role'].str.extract('(\d+)').astype(float)
    df['created'] = pd.to_datetime(df['created'], errors='coerce')
    if 'closed' in df.columns:
        df['closed'] = pd.to_datetime(df['closed'], errors='coerce')
        df['business_hours'] = df.apply(lambda row: calculate_business_hours(row['created'], row['closed']), axis=1)
    if 'ticket_id' in df.columns:
        df['hubspot_url'] = df['ticket_id'].apply(lambda x: f"https://app.hubspot.com/contacts/{HUBSPOT_PORTAL_ID}/ticket/{x}")
    return df.sort_values(by='created', ascending=False)

# --- 2. LAYOUT ---
st.set_page_config(page_title="CS Smart Ticket Dashboard", layout="wide")
st.title("🎫 Customer Success Smart Dashboard")

try:
    data = load_data()
    st.header("Operational View")
    c1, c2, c3 = st.columns(3)
    with c1: owner_f = st.multiselect("Filter by Owner", options=sorted(data['owner'].dropna().unique()))
    with c2: status_f = st.multiselect("Filter by Status", options=sorted(data['status'].dropna().unique()))
    with c3: level_f = st.multiselect("Filter by Predicted Level", options=sorted(data['predicted_level'].dropna().unique()))

    df_filtered = data.copy()
    if owner_f: df_filtered = df_filtered[df_filtered['owner'].isin(owner_f)]
    if status_f: df_filtered = df_filtered[df_filtered['status'].isin(status_f)]
    if level_f: df_filtered = df_filtered[df_filtered['predicted_level'].isin(level_f)]

    st.dataframe(
        df_filtered[['subject', 'created', 'predicted_level', 'owner', 'status', 'routing_status', 'hubspot_url']],
        column_config={"hubspot_url": st.column_config.LinkColumn("HubSpot Link", display_text="Open 🔗"),
                       "created": st.column_config.DatetimeColumn("Created", format="DD.MM.YY, HH:mm")},
        use_container_width=True, hide_index=True
    )

    st.markdown("---")
    st.header("📈 Strategic Insights")
    k1, k2, k3, k4 = st.columns(4)
    
    if 'business_hours' in data.columns:
        k1.metric("Avg. Resolution (Mo-Fr)", f"{data['business_hours'].mean():.1f}h")
    
    if 'confidence_score' in data.columns:
        cov = data['confidence_score'].notnull().mean()
        k2.metric("Auto Route Coverage", f"{cov:.1%}")

    if 'level_num' in data.columns and 'role_num' in data.columns:
        l3_pred = data[data['level_num'] == 3]
        noise = (l3_pred['role_num'] < 3).mean() if len(l3_pred) > 0 else 0
        k3.metric("Engineering Noise", f"{noise:.1%}", delta="Goal: <10%", delta_color="inverse")

    if 'confidence_score' in data.columns:
        k4.metric("AI Confidence Avg.", f"{data['confidence_score'].mean():.1%}")

    ca, cb = st.columns(2)
    with ca:
        data['m_name'] = data['created'].dt.strftime('%B %Y')
        data['m_sort'] = data['created'].dt.strftime('%Y-%m')
        m_lvl = data.groupby(['m_sort', 'm_name', 'predicted_level']).size().reset_index(name='Tickets').sort_values('m_sort')
        st.plotly_chart(px.bar(m_lvl, x='m_name', y='Tickets', color='predicted_level', title="Monthly Volume & Complexity", text_auto=True), use_container_width=True)
    with cb:
        st.plotly_chart(px.pie(data, names='predicted_level', title="Level Distribution", hole=0.4), use_container_width=True)

    st.subheader("Routing Analysis: AI Prediction vs. Human Assignment")
    if 'owner_role' in data.columns and 'predicted_level' in data.columns:
        matrix = pd.crosstab(data['predicted_level'], data['owner_role'])
        st.plotly_chart(px.imshow(matrix, text_auto=True, color_continuous_scale='Blues'), use_container_width=True)

except Exception as e:
    st.error(f"Error: {e}")
