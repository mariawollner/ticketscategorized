# --- 3. CUSTOMER SUCCESS INSIGHTS (Angepasst) ---
    st.header("📊 Customer Success Insights")
    
    # A) Resolution Time (Bleibt gleich)
    if 'business_hours' in data.columns and 'predicted_level' in data.columns:
        st.subheader("Avg. Resolution Time (Hours) by Level & Month")
        res_time_data = data.groupby(['m_sort', 'm_name', 'predicted_level'])['business_hours'].mean().reset_index()
        res_time_data = res_time_data.sort_values('m_sort')
        
        fig_res = px.bar(res_time_data, x='m_name', y='business_hours', color='predicted_level',
                         barmode='group', text_auto='.1f',
                         color_discrete_map={"1st level": "#2ecc71", "2nd level": "#f1c40f", "3rd level": "#e74c3c"})
        st.plotly_chart(fig_res, use_container_width=True)

    # B) NEUES LAYOUT: Monthly Volume & Top Owners
    col_a, col_b = st.columns([2, 1]) # Das Verhältnis 2:1 macht das Diagramm breiter als die Tabelle

    with col_a:
        # Monthly Volume Chart
        m_lvl = data.groupby(['m_sort', 'm_name', 'predicted_level']).size().reset_index(name='Tickets').sort_values('m_sort')
        fig_vol = px.bar(m_lvl, x='m_name', y='Tickets', color='predicted_level', title="Monthly Volume & Complexity", text_auto=True,
                         color_discrete_map={"1st level": "#2ecc71", "2nd level": "#f1c40f", "3rd level": "#e74c3c"})
        st.plotly_chart(fig_vol, use_container_width=True)
            
    with col_b:
        # Top 5 Owners Tabelle für den letzten Monat
        st.subheader("🏆 Top 5 Owners")
        if 'owner' in data.columns and 'm_sort' in data.columns:
            # Den neuesten Monat im Datensatz finden
            latest_month = data['m_sort'].max()
            latest_month_name = data[data['m_sort'] == latest_month]['m_name'].iloc[0]
            
            # Daten filtern und Top 5 berechnen
            top_owners = (data[data['m_sort'] == latest_month]['owner']
                          .value_counts()
                          .reset_index()
                          .rename(columns={'index': 'Owner', 'owner': 'Tickets', 'count': 'Tickets'}) # Kompatibilität je nach pandas Version
                          .head(5))
            
            st.markdown(f"**Last Month:** {latest_month_name}")
            st.dataframe(top_owners, use_container_width=True, hide_index=True)
        else:
            st.info("No owner data available for leaderboard.")

    # C) Pie Chart (Neue Zeile darunter oder weiter unten)
    st.plotly_chart(px.pie(data, names='predicted_level', title="Total Complexity Distribution", hole=0.4), use_container_width=True)
