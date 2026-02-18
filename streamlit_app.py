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
    
    # 1. Numerische Korrekturen (Confidence Score)
    if 'confidence_score' in df.columns:
        # Ersetzt Komma durch Punkt und wandelt alles in Zahlen um, Fehler werden zu NaN
        df['confidence_score'] = pd.to_numeric(df['confidence_score'].str.replace(',', '.'), errors='coerce')
    
    # 2. Level Extraktion (sicherstellen, dass es Zahlen sind)
    if 'predicted_level' in df.columns:
        df['level_num'] = pd.to_numeric(df['predicted_level'].str.extract('(\d+)')[0], errors='coerce')
    if 'owner_role' in df.columns:
        df['role_num'] = pd.to_numeric(df['owner_role'].str.extract('(\d+)')[0], errors='coerce')

    # 3. Zeit-Konvertierung
    df['created'] = pd.to_datetime(df['created'], errors='coerce')
    if 'closed' in df.columns:
        df['closed'] = pd.to_datetime(df['closed'], errors='coerce')
        # Business Hours nur berechnen, wenn beide Daten vorhanden sind
        df['business_hours'] = df.apply(lambda row: calculate_business_hours(row['created'], row['closed']), axis=1)
    
    # Hilfsspalten für zeitliche Gruppierung
    if 'created' in df.columns:
        df['m_name'] = df['created'].dt.strftime('%B %Y')
        df['m_sort'] = df['created'].dt.strftime('%Y-%m')
        
    if 'ticket_id' in df.columns:
        df['hubspot_url'] = df['ticket_id'].apply(lambda x: f"https://app.hubspot.com/contacts/{HUBSPOT_PORTAL_ID}/ticket/{x}")
    
    return df.sort_values(by='created', ascending=False)

# --- LAYOUT SETUP ---
st.set_page_config(page_title="CS Smart Dashboard", layout="wide")
st.title("🎫 Customer Success Smart Dashboard")

try:
    data = load_data()

    # --- 2. OPERATIONAL VIEW ---
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

    st.dataframe(
        df_filtered[['subject', 'created', 'predicted_level', 'owner', 'status', 'hubspot_url']].head(100),
        column_config={
            "hubspot_url": st.column_config.LinkColumn("HubSpot Link", display_text="Open 🔗"),
            "created": st.column_config.DatetimeColumn("Created At", format="DD.MM.YYYY, HH:mm")
        },
        use_container_width=True, hide_index=True
    )

    st.markdown("---")

    # --- 3. CUSTOMER SUCCESS INSIGHTS ---
    st.header("📊 Customer Success Insights")
    
    if 'business_hours' in data.columns and 'predicted_level' in data.columns:
        col_chart, col_top_owner = st.columns([3, 1])
        
        with col_chart:
            st.subheader("Avg. Resolution Time (Hours) by Level & Month")
            res_time_data = data.groupby(['m_sort', 'm_name', 'predicted_level'])['business_hours'].mean().reset_index()
            res_time_data = res_time_data.sort_values('m_sort')
            
            fig_res = px.bar(res_time_data, x='m_name', y='business_hours', color='predicted_level',
                             barmode='group', text_auto='.1f',
                             color_discrete_map={"1st level": "#2ecc71", "2nd level": "#f1c40f", "3rd level": "#e74c3c"})
            st.plotly_chart(fig_res, use_container_width=True)

        with col_top_owner:
            st.subheader("Top 5 Owners")
            if 'owner' in data.columns and 'm_sort' in data.columns:
                latest_month_sort = data['m_sort'].max()
                latest_month_name = data[data['m_sort'] == latest_month_sort]['m_name'].iloc[0]
                st.caption(f"Tickets in {latest_month_name}")
                
                top_owners = (data[data['m_sort'] == latest_month_sort]['owner']
                              .value_counts()
                              .head(5)
                              .reset_index())
                top_owners.columns = ['Owner', 'Tickets']
                st.table(top_owners)

    col_a, col_b = st.columns(2)
    with col_a:
        if 'created' in data.columns:
            m_lvl = data.groupby(['m_sort', 'm_name', 'predicted_level']).size().reset_index(name='Tickets').sort_values('m_sort')
            fig_vol = px.bar(m_lvl, x='m_name', y='Tickets', color='predicted_level', 
                             title="Monthly Volume & Complexity", text_auto=True,
                             color_discrete_map={"1st level": "#2ecc71", "2nd level": "#f1c40f", "3rd level": "#e74c3c"})
            st.plotly_chart(fig_vol, use_container_width=True)
            
    with col_b:
        if 'predicted_level' in data.columns:
            st.plotly_chart(px.pie(data, names='predicted_level', title="Total Complexity Distribution", hole=0.4), use_container_width=True)

    st.markdown("---")

    # --- 4. STRATEGIC INSIGHTS ---
    st.header("📈 Strategic Insights")
    k1, k2, k3 = st.columns(3)
    
    # KPI 1: Auto Route Coverage
    coverage_val = 0.0
    if 'routing_score' in data.columns:
        auto_count = data['routing_score'].fillna("").str.lower().str.contains("auto").sum()
        coverage_val = auto_count / len(data) if len(data) > 0 else 0.0
    k1.metric("Auto Route Coverage", f"{coverage_val:.1%}")

    # KPI 2: Engineering Noise
    noise = 0.0
    if 'level_num' in data.columns and 'role_num' in data.columns:
        l3_pred = data[data['level_num'] == 3].copy()
        if len(l3_pred) > 0:
            # Sicherstellen, dass Vergleiche nur mit Zahlen stattfinden
            noise = (l3_pred['role_num'] < 3).mean()
        k2.metric("Engineering Noise", f"{noise:.1%}", delta="Goal: <10%", delta_color="inverse")

    # KPI 3: AI Confidence
    avg_conf = 0.0
    if 'confidence_score' in data.columns:
        avg_conf = data['confidence_score'].mean()
    k3.metric("Avg. AI Confidence", f"{avg_conf:.1%}" if not pd.isna(avg_conf) else "0.0%")

    # Confusion Matrix
    st.subheader("Deep Dive: AI Prediction vs. Actual Human Assignment")
    if 'owner_role' in data.columns and 'predicted_level' in data.columns:
        matrix = pd.crosstab(data['predicted_level'], data['owner_role'])
        st.plotly_chart(px.imshow(matrix, text_auto=True, color_continuous_scale='Blues'), use_container_width=True)

except Exception as e:
    st.error(f"Ein Fehler ist aufgetreten: {e}")
    st.info("Hinweis: Überprüfe, ob alle numerischen Spalten im Sheet (z.B. confidence_score) korrekt gefüllt sind.")
