# --- 3. CUSTOMER SUCCESS INSIGHTS ---
    st.header("📊 Customer Success Insights")
    
    # A) Resolution Time pro Level & Monat
    if 'business_hours' in data.columns and 'predicted_level' in data.columns:
        st.subheader("Avg. Resolution Time (Hours) by Level & Month")
        
        # Wir teilen das Layout hier in 2 Spalten: Links das große Diagramm, rechts die kleine Tabelle
        col_chart, col_top_owner = st.columns([3, 1]) # Verhältnis 3 zu 1
        
        with col_chart:
            res_time_data = data.groupby(['m_sort', 'm_name', 'predicted_level'])['business_hours'].mean().reset_index()
            res_time_data = res_time_data.sort_values('m_sort')
            
            fig_res = px.bar(res_time_data, x='m_name', y='business_hours', color='predicted_level',
                             barmode='group', text_auto='.1f',
                             color_discrete_map={"1st level": "#2ecc71", "2nd level": "#f1c40f", "3rd level": "#e74c3c"})
            st.plotly_chart(fig_res, use_container_width=True)

        with col_top_owner:
            st.markdown(f"**Top 5 Owners (Last Month)**")
            if 'owner' in data.columns and 'm_sort' in data.columns:
                # Den neuesten Monat ermitteln
                latest_month_sort = data['m_sort'].max()
                latest_month_name = data[data['m_sort'] == latest_month_sort]['m_name'].iloc[0]
                
                st.caption(f"Data for: {latest_month_name}")
                
                # Filter auf letzten Monat & Top 5 Owner
                top_owners = (data[data['m_sort'] == latest_month_sort]['owner']
                              .value_counts()
                              .head(5)
                              .reset_index())
                top_owners.columns = ['Owner', 'Tickets']
                
                st.table(top_owners) # Kompakte Darstellung ohne Interaktion
            else:
                st.info("No owner data available.")

    # B) Monthly Volume & C) Pie Chart (bleiben darunter in ihren 2 Spalten)
    col_a, col_b = st.columns(2)
    # ... (Rest des Codes wie zuvor)
