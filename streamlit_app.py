import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. KONFIGURATION ---
# Ersetze diesen Link durch deinen Google Sheet Browser-Link
SHEET_URL = "DEIN_NORMALER_GOOGLE_SHEET_LINK"
# Ersetze die Portal ID durch deine HubSpot ID (aus der Browser-URL bei HubSpot)
HUBSPOT_PORTAL_ID = "1234567" 

def get_csv_url(url):
    """Wandelt den normalen Link in einen Export-Link um."""
    if "/edit" in url:
        return url.split("/edit")[0] + "/export?format=csv"
    return url

@st.cache_data(ttl=600)
def load_data():
    csv_url = get_csv_url(SHEET_URL)
    df = pd.read_csv(csv_url)
    
    # Datums-Konvertierung (Wichtig für Berechnungen)
    df['created'] = pd.to_datetime(df['created'], errors='coerce')
    if 'closed' in df.columns:
        df['closed'] = pd.to_datetime(df['closed'], errors='coerce')
    
    # Dynamischer HubSpot Link basierend auf der ticket_id
    df['hubspot_url'] = df['ticket_id'].apply(
        lambda x: f"https://app.hubspot.com/contacts/{HUBSPOT_PORTAL_ID}/ticket/{x}"
    )
    
    # Numerische Extraktion für Accuracy (z.B. "Level 2" -> 2)
    df['role_num'] = df['owner_role'].astype(str).str.extract('(\d+)').astype(float)
    return df

# --- 2. SEITEN-LAYOUT ---
st.set_page_config(page_title="Customer Success Ticket Dashboard", layout="wide")
st.title("🎫 Customer Success Ticket Dashboard")

try:
    data = load_data()

    # --- 3. OPERATIONAL VIEW (FOR CS) ---
    st.header("Operational View")
    
    # Filter-Bereich
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        owner_filter = st.multiselect("Filter by Owner", options=sorted(data['owner'].unique()))
    with col_f2:
        status_filter = st.multiselect("Filter by Status", options=sorted(data['status'].unique()))
    with col_f3:
        level_filter = st.multiselect("Filter by Predicted Level", options=sorted(data['predicted_level'].unique()))

    # Filter anwenden
    df_filtered = data.copy()
    if owner_filter:
        df_filtered = df_filtered[df_filtered['owner'].isin(owner_filter)]
    if status_filter:
        df_filtered = df_filtered[df_filtered['status'].isin(status_filter)]
    if level_filter:
        df_filtered = df_filtered[df_filtered['predicted_level'].isin(level_filter)]

    # Tabelle für das CS Team
    # Fokus: Subject, Time, Level, Owner, Status, Routing & Link
    st.dataframe(
        df_filtered[['subject', 'created', 'predicted_level', 'owner', 'status', 'routing_status', 'hubspot_url']],
        column_config={
            "hubspot_url": st.column_config.LinkColumn("HubSpot Link", display_text="Open in HubSpot 🔗"),
            "created": st.column_config.DatetimeColumn("Created At", format="DD.MM.YYYY, HH:mm"),
            "predicted_level": st.column_config.NumberColumn("Level", format="%d")
        },
        use_container_width=True,
        hide_index=True
    )

    st.markdown("---")

    # --- 4. STRATEGIC DASHBOARD (FOR STRATEGISTS) ---
    st.header("📈 Strategic Insights")

    # KPI Zeile
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    
    # 1. Avg Resolution Time
    if 'closed' in data.columns:
        valid_dates = data.dropna(subset=['created', 'closed'])
        avg_res = (valid_dates['closed'] - valid_dates['created']).dt.total_seconds() / 3600
        kpi1.metric("Avg. Resolution Time", f"{avg_res.mean():.1f} Hours")

    # 2. Avg Confidence Score
    if 'confidence_score' in data.columns:
        kpi2.metric("Avg. Confidence Score", f"{data['confidence_score'].mean():.1%}")

    # 3. Accuracy Calculation
    correct = (data['role_num'] == data['predicted_level']).sum()
    accuracy = correct / len(data) if len(data) > 0 else 0
    kpi3.metric("Routing Accuracy", f"{accuracy:.1%}", help="How often predicted level matches owner role")

    # 4. Level 3 Share
    l3_share = (data['predicted_level'] == 3).sum() / len(data) if len(data) > 0 else 0
    kpi4.metric("Level 3 Share", f"{l3_share:.1%}")

    # Diagramme
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        # Entwicklung über Monate
        data['month'] = data['created'].dt.strftime('%Y-%m')
        monthly_data = data.groupby('month').size().reset_index(name='Tickets')
        fig_line = px.line(monthly_data, x='month', y='Tickets', title="Ticket Volume per Month", markers=True)
        st.plotly_chart(fig_line, use_container_width=True)

    with col_chart2:
        # Pie Chart Levels
        fig_pie = px.pie(data, names='predicted_level', title="Tickets by Level (Predicted)", hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)

    # Deep Dive: Accuracy Heatmap
    st.subheader("Classification Deep Dive: AI Prediction vs. Actual Handling")
    accuracy_matrix = pd.crosstab(data['predicted_level'], data['owner_role'])
    fig_heat = px.imshow(
        accuracy_matrix, 
        text_auto=True, 
        color_continuous_scale='Greens',
        labels=dict(x="Actual Owner Role (Human)", y="Predicted Level (AI)")
    )
    st.plotly_chart(fig_heat, use_container_width=True)

except Exception as e:
    st.error(f"Error: {e}")
    st.info("Check if your Google Sheet is public and columns are named correctly.")
