import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- CONFIGURATION ---
# Ersetze diesen Link durch deinen Google Sheet Link (Freigabe: Jeder mit dem Link)
SHEET_URL = "https://docs.google.com/spreadsheets/d/14I3ru-sF5Q889NYBzUJDyUzLeIHN8G8ZFwzk78IOCKM/edit?usp=sharing"

def get_csv_url(url):
    if "/edit" in url:
        return url.split("/edit")[0] + "/export?format=csv"
    return url

@st.cache_data(ttl=600) # Cache für 10 Minuten, um Ladezeiten zu optimieren
def load_data():
    csv_url = get_csv_url(SHEET_URL)
    df = pd.read_csv(csv_url)
    
    # Datumskonvertierung
    df['created'] = pd.to_datetime(df['created'])
    if 'closed' in df.columns:
        df['closed'] = pd.to_datetime(df['closed'])
    
    return df

# --- PAGE SETUP ---
st.set_page_config(page_title="CS Ticket Dashboard", layout="wide")
st.title("🎫 Customer Success Ticket Dashboard")

try:
    df = load_data()

    # --- SECTION 1: OPERATIONAL (CS TEAM) ---
    st.header("Operational View")
    
    # Filter-Zeile
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        owner_filter = st.multiselect("Filter by Owner", options=df['owner'].unique())
    with col_f2:
        status_filter = st.multiselect("Filter by Status", options=df['status'].unique())
    with col_f3:
        level_filter = st.multiselect("Filter by Predicted Level", options=df['predicted_level'].unique())

    # Filter anwenden
    filtered_df = df.copy()
    if owner_filter:
        filtered_df = filtered_df[filtered_df['owner'].isin(owner_filter)]
    if status_filter:
        filtered_df = filtered_df[filtered_df['status'].isin(status_filter)]
    if level_filter:
        filtered_df = filtered_df[filtered_df['predicted_level'].isin(level_filter)]

    # Tabelle für CS (Spalten Auswahl & HubSpot Link)
    # Wir nutzen st.column_config für den klickbaren Link
    display_cols = ['subject', 'created', 'predicted_level', 'owner', 'status', 'routing_status', 'hubspot_link']
    
    st.dataframe(
        filtered_df[display_cols],
        column_config={
            "hubspot_link": st.column_config.LinkColumn("HubSpot Link", display_text="Open Ticket"),
            "created": st.column_config.DatetimeColumn("Created At", format="DD.MM.YYYY, HH:mm"),
        },
        use_container_width=True,
        hide_index=True
    )

    st.markdown("---")

    # --- SECTION 2: STRATEGIC DASHBOARD ---
    st.header("📈 Strategic Insights")

    # KPI Reihe 1: Bearbeitungszeit & Confidence
    col_s1, col_s2, col_s3 = st.columns(3)
    
    # 1. Avg Resolution Time
    if 'closed' in df.columns:
        duration = (df['closed'] - df['created']).dt.total_seconds() / 3600 # in Stunden
        avg_time = duration.mean()
        col_s1.metric("Avg. Resolution Time", f"{avg_time:.1f} Hours")

    # 2. Avg Confidence Score
    if 'confidence_score' in df.columns:
        avg_conf = df['confidence_score'].mean()
        col_s2.metric("Avg. Confidence Score", f"{avg_conf:.1%}")

    # 3. Level 3 Distribution
    l3_share = (df['predicted_level'] == 3).mean()
    col_s3.metric("Level 3 Share", f"{l3_share:.1%}")

    # Grafik Reihe 1: Zeitverlauf & Level-Verteilung
    col_g1, col_g2 = st.columns(2)

    with col_g1:
        # Tickets per Month
        df['month'] = df['created'].dt.to_period('M').astype(str)
        monthly_tickets = df.groupby('month').size().reset_index(name='count')
        fig_line = px.line(monthly_tickets, x='month', y='count', title="Tickets per Month", markers=True)
        st.plotly_chart(fig_line, use_container_width=True)

    with col_g2:
        # Pie Chart Levels
        fig_pie = px.pie(df, names='predicted_level', title="Tickets by Predicted Level", hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)

    # KPI Reihe 2: Accuracy (Owner Role vs Predicted Level)
    st.subheader("Classification Accuracy")
    # Logik: Wir zählen, wo owner_role (z.B. "L2") dem predicted_level (2) entspricht
    # Hinweis: Spalten müssen vergleichbare Typen haben (z.B. beide Strings oder Integers)
    correct_mask = df['owner_role'].astype(str).str.extract('(\d+)')[0] == df['predicted_level'].astype(str)
    correct_count = correct_mask.sum()
    accuracy = correct_count / len(df)

    c1, c2 = st.columns(2)
    c1.metric("Correctly Classified Tickets", f"{correct_count} Tickets")
    c2.metric("Classification Accuracy", f"{accuracy:.1%}")

except Exception as e:
    st.error(f"Error loading dashboard: {e}")
    st.warning("Please ensure your Google Sheet has the correct column headers.")

    hide_index=True,
    use_container_width=True
)
