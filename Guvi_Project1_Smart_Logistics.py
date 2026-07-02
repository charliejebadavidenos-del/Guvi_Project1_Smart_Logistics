#Smart Logistics Management & Analytics Platform

import streamlit as st
import mysql.connector
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
import seaborn as sns
import pydeck as pdk
from sqlalchemy import create_engine


# Function to connect to SQLite database
def get_data(query, params=None):
    conn = mysql.connector.connect(
          host="localhost",
          user="root",
          password="hopePraise8gt",
          database = "guvi_db"
    )
    
    if params:
        df = pd.read_sql_query(query, conn, params=params)
    else:
        df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# Streamlit App Title
st.set_page_config(page_title="Smart Logistics Management & Analytics Platform", layout="wide")

# Sidebar for navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Project Introduction", "Shipment - Filtering/Analytics","Potential Business Insights", "Implementation","Creator Info"])

# -------------------------------- PAGE 1: Introduction --------------------------------
if page == "Project Introduction":
    st.title("Smart Logistics Management & Analytics Platform")
    st.subheader("Exploring growing Logistics Management and Analytics")
    st.write("""
        This project aims to build a centralized Smart Logistics Management and Analytics Platform that consolidates operational data 
    into a MySQL database and provides an interactive Streamlit dashboard for real-time analysis and decision-making.
    
        The objective of this project is to design and implement an end-to-end logistics analytics system that:
            1. Ingests large-scale logistics datasets (70,000+ shipment records).
            2. Stores data in a normalized MySQL relational database.
            3. Enables shipment-level tracking through status logs.
            4. Provides operational insights via Streamlit dashboards.
            5. Supports filtering, KPI monitoring, and business performance evaluation.
    
    **Database Used:** `guvi_db.mysql`
    """)



# ---------- PAGE 2: Shipment - Filtering/Analytics ----------
elif page == "Shipment - Filtering/Analytics":
    st.title("Shipment Search & Filtering")
    
    # 1. Fetch all filter options first - keep this at top
    
    status_df = get_data("select distinct status from guvi_db.shipments")
    origin_df = get_data("select distinct origin from guvi_db.shipments")
    destination_df = get_data("select distinct destination from guvi_db.shipments")
    order_date_df = get_data("SELECT MIN(DATE(order_date)) as min_d, MAX(DATE(order_date)) as max_d FROM guvi_db.shipments")
    #delivery_date_df=get_data("SELECT MIN(DATE(delivery_date)) as min_d, MAX(DATE(delivery_date)) as max_d FROM guvi_db.shipments")
        
    # 2. PUT ALL FILTERS IN SIDEBAR 
    with st.sidebar:
        st.header("🔍 Filters")
        
        status = ["All"] + status_df['status'].tolist()
        selected_status = st.selectbox("Status", status, key="stat")

        origin = ["All"] + origin_df['origin'].tolist()
        selected_origin = st.selectbox("Origin", origin, key="o")
        
        destination = ["All"] + destination_df['destination'].tolist()
        selected_destination = st.selectbox("Destination", destination, key="d")
        
        shipment_id = st.text_input("Search by Shipment ID", key="ship_id", placeholder="Enter shipment_id")

        col1, col2 = st.columns(2)
        with col1:
            order_date_start = st.date_input("Order Date Start", value=order_date_df['min_d'][0], key="s")
        with col2:
            order_date_end = st.date_input("Order Date End", value=order_date_df['max_d'][0], key="e")
        

     # 4. Build dynamic query - keep this in main area
    query1 = """
            select  shipments.shipment_id,
                    shipments.order_date,
                    shipments.origin,
                    shipments.destination,
                    shipments.weight,
                    shipments.courier_id,
                    shipments.status as shipments_status,
                    shipments.delivery_date ,
                    tracking.tracking_id,
                    tracking.status as tracking_status,
                    tracking.timestamp,
                    costs.fuel_cost,
                    costs.labor_cost,
                    costs.misc_cost,
                    courier.name,
                    courier.rating,
                    courier.vehicle_type
            from guvi_db.shipments shipments
            left join guvi_db.shipment_tracking tracking
            on shipments.shipment_id =tracking.shipment_id
            left join guvi_db.costs
            on shipments.shipment_id =costs.shipment_id
            left join guvi_db.courier_staff courier
            on shipments.courier_id = courier.courier_id
            WHERE 1=1
            """
    params = []
    
    if selected_status!= "All":
        query1 += " AND `shipments`.`status` = %s"
        params.append(selected_status)

    if selected_origin!= "All":
        query1 += " AND `shipments`.`origin` = %s"
        params.append(selected_origin)
    
    if selected_destination!= "All":
        query1 += " AND `shipments`.`destination` = %s"
        params.append(selected_destination)

    if shipment_id:  # if user typed something
        query1 += " AND shipments.shipment_id = %s"
        params.append(shipment_id)
    
    query1 += " AND DATE(`shipments`.`order_date`) BETWEEN %s AND %s"
    params.extend([str(order_date_start), str(order_date_end)])
           
    query1 += " LIMIT 10000"
    
    # 4. Show results in main area - more space now
    df = get_data(query1, tuple(params))
    if not df.empty:
        st.write(f"Rows found: {len(df)}")
        st.dataframe(df, width="stretch", height=500)


        #st.write("Actual columns:", df.columns.tolist())
        #st.stop()  # This will pause app and show column names


        
        # ---------- Data Table ----------
        #st.subheader("Shipment Details")
        #st.dataframe(df, width="stretch", height=500)
    
    else:
        st.warning("No data available for selected filters.")


    
    # ---------- B. Operational KPIs ----------
    total_shipments = len(df)

    # Handle case sensitivity in status column
    df['shipments_status'] = df['shipments_status'].str.title()

    delivered_count = len(df[df['shipments_status'] == 'Delivered'])
    delivered_pct = (delivered_count / total_shipments) * 100 if total_shipments > 0 else 0

    cancelled_count = len(df[df['shipments_status'] == 'Cancelled'])
    cancelled_pct = (cancelled_count / total_shipments) * 100 if total_shipments > 0 else 0

    # Avg Delivery Time - only for delivered shipments with valid dates
    delivered_df = df[(df['shipments_status'] == 'Delivered') & 
                    df['delivery_date'].notna() & 
                    df['order_date'].notna()].copy()

    if not delivered_df.empty:
        delivered_df['delivery_time'] = pd.to_datetime(delivered_df['delivery_date']) - pd.to_datetime(delivered_df['order_date'])
        avg_delivery_time = delivered_df['delivery_time'].dt.days.mean()
    else:
        avg_delivery_time = 0

    # Total Operational Cost
    df['total_cost'] = df['fuel_cost'].fillna(0) + df['labor_cost'].fillna(0) + df['misc_cost'].fillna(0)
    total_op_cost = df['total_cost'].sum()

    # Display KPIs in 5 columns
    st.subheader("📊 Operational KPIs")
    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Total Shipments", f"{total_shipments:,}")
    col2.metric("Delivered %", f"{delivered_pct:.1f}%", f"{delivered_count} shipments")
    col3.metric("Cancelled %", f"{cancelled_pct:.1f}%", f"{cancelled_count} shipments") 
    col4.metric("Avg Delivery Time", f"{avg_delivery_time:.1f} days")
    col5.metric("Total Op Cost", f"₹{total_op_cost:,.0f}")

    # ---------- 1. Delivery Performance Insights ----------
    st.subheader("1. Delivery Performance Insights")

    # Create route column + delivery time
    df['route'] = df['origin'] + " → " + df['destination']
    delivered_df = df[(df['shipments_status'] == 'Delivered') & df['delivery_date'].notna()].copy()
    delivered_df['delivery_days'] = (pd.to_datetime(delivered_df['delivery_date']) - pd.to_datetime(delivered_df['order_date'])).dt.days

    # 1. Avg delivery time per route
    avg_by_route = delivered_df.groupby('route')['delivery_days'].mean().sort_values(ascending=False).reset_index()
    st.write("**Avg Delivery Time per Route**")
    st.bar_chart(avg_by_route.set_index('route'))

    # 2. Most delayed routes - top 10
    most_delayed = avg_by_route.head(10)
    st.write("**Most Delayed Routes - Top 10**")
    st.dataframe(most_delayed)

    # 3. Delivery time vs distance - need distance column. If not in df, skip for now
    # st.scatter_chart(df, x='distance', y='delivery_days')

    # ---------- 2. Courier Performance ----------
    # Courier Performance
    st.subheader("2. Courier Performance")

    # 1. Shipments handled per courier
    ship_per_courier = df.groupby('name').size().reset_index(name='total_shipments')
    st.bar_chart(ship_per_courier.set_index('name'))

    # 2. On-time delivery % - assuming <3 days = on-time
    on_time = delivered_df[delivered_df['delivery_days'] <= 3].groupby('name').size()
    total = delivered_df.groupby('name').size()
    on_time_pct = (on_time / total * 100).fillna(0).reset_index(name='on_time_%')
    st.write("**On-time Delivery % by Courier**")
    st.dataframe(on_time_pct)

    # 3. Avg rating comparison
    avg_rating = df.groupby('name')['rating'].mean().reset_index()
    st.bar_chart(avg_rating.set_index('name'))

    # ---------- 3. Cost Analytics ----------
    st.subheader("3. Cost Analytics")

    df['total_cost'] = df['fuel_cost'].fillna(0) + df['labor_cost'].fillna(0) + df['misc_cost'].fillna(0)

    # 1. Total cost per shipment
    st.write("**Top 10 High Cost Shipments**")
    st.dataframe(df.nlargest(10, 'total_cost')[['shipment_id', 'route', 'total_cost']])

    # 2. Cost per route
    cost_by_route = df.groupby('route')['total_cost'].sum().reset_index()
    st.bar_chart(cost_by_route.set_index('route'))

    # 3. Fuel vs Labor % contribution
    fuel_total = df['fuel_cost'].sum()
    labor_total = df['labor_cost'].sum()
    fuel_pct = fuel_total / (fuel_total + labor_total) * 100
    st.metric("Fuel Cost %", f"{fuel_pct:.1f}%", f"Labor: {100-fuel_pct:.1f}%")


    # ---------- 4. Cancellation Analysis ----------
    st.subheader("4. Cancellation Analysis")
    
    total_shipments = len(df)
    cancelled_df = df[df['shipments_status'] == 'Cancelled'].copy()
    total_cancelled = len(cancelled_df)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Cancelled", total_cancelled)
    col2.metric("Cancellation Rate", f"{(total_cancelled/total_shipments*100):.1f}%" if total_shipments > 0 else "0%")
    col3.metric("Delivered Rate", f"{(len(df[df['shipments_status']=='Delivered'])/total_shipments*100):.1f}%" if total_shipments > 0 else "0%")
    
    col1, col2 = st.columns(2)
    
    # 1. Cancellation rate by origin
    with col1:
        st.write("**Cancellation Rate by Origin - Top 15**")
        cancel_rate_origin = df.groupby('origin')['shipments_status'].apply(
            lambda x: (x == 'Cancelled').mean() * 100
        ).sort_values(ascending=False).head(15)
        st.bar_chart(cancel_rate_origin)
        st.dataframe(cancel_rate_origin.reset_index(name='Cancel %'), width="stretch")
    
    # 2. Cancellation rate by courier
    with col2:
        st.write("**Cancellation Rate by Courier - Top 15**")
        cancel_rate_courier = df.groupby('name')['shipments_status'].apply(
            lambda x: (x == 'Cancelled').mean() * 100
        ).sort_values(ascending=False).head(15)
        st.bar_chart(cancel_rate_courier)
        st.dataframe(cancel_rate_courier.reset_index(name='Cancel %'), width="stretch")
    
    # 3. Time-to-cancellation analysis
    if 'cancellation_date' in df.columns and not cancelled_df.empty:
        st.write("**Time-to-Cancellation Analysis**")
        cancelled_df['time_to_cancel_days'] = (pd.to_datetime(cancelled_df['cancellation_date']) - 
                                               pd.to_datetime(cancelled_df['order_date'])).dt.days
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Avg Time to Cancel", f"{cancelled_df['time_to_cancel_days'].mean():.1f} days")
            st.metric("Median Time to Cancel", f"{cancelled_df['time_to_cancel_days'].median():.1f} days")
        
        with col2:
            st.write("**Avg Time to Cancel by Origin**")
            avg_cancel_time = cancelled_df.groupby('origin')['time_to_cancel_days'].mean().sort_values().head(15)
            st.bar_chart(avg_cancel_time)
        
        st.write("**Time to Cancel Distribution**")
        st.histogram_chart(cancelled_df['time_to_cancel_days'], bins=20)
    else:
        st.info("Add `cancellation_date` column to DB to enable Time-to-Cancellation analysis")

    


# ---------- PAGE 3: Potential Business Insights ----------
elif page == "Potential Business Insights":
    st.set_page_config(page_title="Potential Business Insights", layout="wide")
    st.title("📦 Smart Logistics - Business Insights Dashboard")

    # 1. DB Connection - replace with your credentials
    @st.cache_data
    def load_data():
        conn = mysql.connector.connect(
            host="localhost",
            user="root", 
            password="hopePraise8gt",
            database="guvi_db"
        )
        
        query = """
        SELECT shipments.shipment_id,
            shipments.order_date,
            shipments.origin,
            shipments.destination,
            routes.distance_km,
            routes.avg_time_hours,
            shipments.weight,
            shipments.courier_id,
            shipments.status as shipment_status,
            shipments.delivery_date,
            tracking.tracking_id,
            tracking.status as tracking_status,
            tracking.timestamp,
            costs.fuel_cost,
            costs.labor_cost,
            costs.misc_cost,
            courier.name as courier_name,
            courier.rating,
            courier.vehicle_type,
            warehouses.state,
            warehouses.capacity,
            warehouses.city,
            CASE 
                WHEN delivery_date IS NOT NULL AND order_date IS NOT NULL
                THEN DATEDIFF(delivery_date, order_date) + 1
            END AS delivery_days,
            COALESCE(costs.fuel_cost, 0) + COALESCE(costs.labor_cost, 0) + COALESCE(costs.misc_cost, 0) as total_cost
        FROM guvi_db.shipments shipments
        LEFT JOIN guvi_db.shipment_tracking tracking ON shipments.shipment_id = tracking.shipment_id
        LEFT JOIN guvi_db.costs costs ON shipments.shipment_id = costs.shipment_id
        LEFT JOIN guvi_db.routes routes ON routes.origin = shipments.origin AND routes.destination = shipments.destination
        LEFT JOIN guvi_db.courier_staff courier ON shipments.courier_id = courier.courier_id
        LEFT JOIN guvi_db.warehouses warehouses ON warehouses.city = shipments.origin
        """
        df = pd.read_sql(query, conn)
        conn.close()
        return df

    df = load_data()

    # Filters
    col1, col2 = st.columns(2)
    with col1:
        origin_filter = st.multiselect("Filter by Origin", df['origin'].unique())
    with col2:
        courier_filter = st.multiselect("Filter by Courier", df['courier_name'].unique())

    if origin_filter:
        df = df[df['origin'].isin(origin_filter)]
    if courier_filter:
        df = df[df['courier_name'].isin(courier_filter)]

    # 7 Business Insights as tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "1. Route Delays", "2. Courier Volume", "3. Rating vs Speed", 
        "4. Expensive Shipments", "5. Cost vs Weight", "6. Cancellations", "7. Underperforming Routes","8. Warehouse Insights"
    ])

    with tab1:
        st.subheader("Routes which has the highest delays")
        route_delay = df.groupby(['origin','destination'])['delivery_days'].mean().sort_values(ascending=False).head(10).reset_index()
        fig = px.bar(route_delay, x='origin', y='delivery_days', color='destination', title="Top 10 Delayed Routes")
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("Couriers which handled most shipments")
        courier_vol = df['courier_name'].value_counts().head(10).reset_index()
        fig = px.pie(courier_vol, names='courier_name', values='count', title="Shipment Volume by Courier")
        st.plotly_chart(fig)

    with tab3:
        st.subheader("High-rated couriers vs Fast delivery")
        fig = px.scatter(df, x='rating', y='delivery_days', color='courier_name', 
                        title="Courier Rating vs Avg Delivery Days")
        st.plotly_chart(fig)

    with tab4:
        st.subheader("Shipments are most expensive")
        top_cost = df.nlargest(10, 'total_cost')[['shipment_id','origin','destination','total_cost']]
        st.dataframe(top_cost)

    with tab5:
        st.subheader("Cost directly proportional to weight")
        fig = px.scatter(df, x='weight', y='total_cost', trendline="ols", title="Cost vs Weight")
        st.plotly_chart(fig)

    with tab6:
        st.subheader("Cities generate maximum cancellations")
        cancel_df = df[df['shipment_status'] == 'Cancelled']
        city_cancel = cancel_df['origin'].value_counts().head(10).reset_index()
        fig = px.bar(city_cancel, x='origin', y='count', title="Top Cities by Cancellations")
        st.plotly_chart(fig)

    with tab7:
        st.subheader("Routes are underperforming relative to distance")
        df['delay_vs_expected'] = df['delivery_days'] - (df['distance_km'] / 500) # assuming 500km/day
        underperf = df.groupby(['origin','destination'])['delay_vs_expected'].mean().sort_values(ascending=False).head(10).reset_index()
        st.dataframe(underperf)

    with tab8:
        st.subheader("8. Warehouse Insights")


        st.markdown("**1. Warehouse Capacity Comparison**")
        # Remove duplicate cities first
        warehouse_cap = df[['city','state','capacity']].drop_duplicates().sort_values('capacity', ascending=False)
        
        fig = px.bar(warehouse_cap, x='city', y='capacity', color='state',
                    title="Capacity by Warehouse City")
        fig.update_xaxes(tickangle=45)
        st.plotly_chart(fig, use_container_width=True)

   
        st.markdown("**2. High-Traffic Warehouse Cities**")
        
        origin_traffic = df['origin'].value_counts().reset_index()
        origin_traffic.columns = ['city', 'shipments']
        origin_traffic['type'] = 'Origin'
        
        dest_traffic = df['destination'].value_counts().reset_index()
        dest_traffic.columns = ['city', 'shipments'] 
        dest_traffic['type'] = 'Destination'
        
        traffic_df = pd.concat([origin_traffic, dest_traffic], ignore_index=True)
        
        # Take top 15 cities by total shipments so names are readable
        top_cities = traffic_df.groupby('city')['shipments'].sum().nlargest(15).index
        traffic_df = traffic_df[traffic_df['city'].isin(top_cities)]
        
        fig2 = px.bar(traffic_df, x='city', y='shipments', color='type', barmode='group',
                    title="Top 15 High-Traffic Cities - Origin vs Destination")
        
        fig2.update_layout(
            height=500,
            xaxis_tickangle=-45,  # 45 degree rotation
            xaxis={'categoryorder':'total descending'}  # sort by traffic
        )
        st.plotly_chart(fig2, use_container_width=True)
                
    st.sidebar.info("Data from shipments + routes + tracking + costs + courier + warehouses")



# ---------- PAGE 5: Implementation ----------

elif page == "Implementation":
    st.set_page_config(layout="wide")
    st.title("Smart Logistics Management & Analytics Platform")
    st.caption("Dashboard /Statistics / Data Cleaning & Interactive Streamlit Dashboard")
    
    st.divider()
    
    # Problem Statement in a nice card
    with st.container(border=True):
        st.subheader("📋 Problem Statement")
        st.markdown("""
            In modern logistics operations, companies similar to DHL and FedEx manage thousands of shipments daily across multiple routes, warehouses,
        and courier personnel.Operational inefficiencies such as delivery delays, high transportation costs, underutilized warehouses, and 
        inconsistent courier performance can significantly impact profitability and customer satisfaction.
        
            However, raw operational data is often scattered across multiple files and systems (shipment records, tracking logs, cost sheets,
        route details). Without centralized analytics, it becomes difficult for management to:
                ● Monitor delivery performance
                ● Identify bottleneck routes
                ● Track real-time shipment status
                ● Analyze operational costs
                ● Evaluate courier efficiency
                ● Detect cancellation patterns
        """)
    
        
    col1, col2 = st.columns(2)
    
    # Business Use Cases
    with col1:
        with st.container(border=True):
            st.subheader("🎯 Business Use Cases")
            st.markdown("""
            objective of this project is to design and implement an end-to-end logistics analytics system that:
                    1. Ingests large-scale logistics datasets (70,000+ shipment records).
                    2. Stores data in a normalized MySQL relational database.
                    3. Enables shipment-level tracking through status logs.
                    4. Provides operational insights via Streamlit dashboards.
                    5. Supports filtering, KPI monitoring, and business performance evaluation
            """)
    
    # Data Cleaning steps
    with col2:
        with st.container(border=True):
            st.subheader("Data Architecture")
            st.markdown("""
            The system integrates structured data across six core datasets:
                ● Shipments
                ● Shipment Tracking
                ● Courier Staff
                ● Routes
                ● Warehouses
                ● Costs
            These datasets simulate real-world logistics operations.
            """)
    
    st.divider()
   
    st.subheader("System Workflow")
    st.markdown("""

                1. Import CSV/JSON datasets into MySQL.
                2. Establish foreign key relationships.
                3. Build optimized SQL queries for KPIs.
                4. Connect Streamlit to MySQL using a Python database connector.
                5. Display real-time data with filtering options.
                6. Create required indexes on the table. **
                
    """)

    st.subheader("Shipment - Filtering/Analytics")
    st.markdown("""
        
        A. Shipment Search & Filtering
                ● Search by shipment_id
                
                ● Filter by:
                    ○ Status (Delivered, Cancelled, In Transit)
                    ○ Origin / Destination
                    ○ Date range
                    ○ Courier 
                
        📊 B. Operational KPIs
                
                ● Total Shipments
                ● Delivered Shipments %
                ● Cancelled Shipments %
                ● Average Delivery Time
                ● Total Operational Cost

        📈 C. Analytical Views
                
        1️⃣ Delivery Performance Insights
                ● Average delivery time per route
                ● Most delayed routes
                ● Delivery time vs distance comparison
                
        2️⃣ Courier Performance
                ● Shipments handled per courier
                ● On-time delivery %
                ● Average rating comparison

        3️⃣ Cost Analytics
                ● Total cost per shipment
                ● Cost per route
                ● Fuel vs labor percentage contribution
                ● High-cost shipments

         4️⃣ Cancellation Analysis
                ● Cancellation rate by origin
                ● Cancellation rate by courier
                ● Time-to-cancellation analysis

        5️⃣ Warehouse Insights
                ● Warehouse capacity comparison
                ● High-traffic warehouse cities

    """)

    st.subheader("Potential Business Insights")
    st.markdown("""
    There were few questions provided on the project document.The results to the project report is 
                
                - Routes which has the highest delays
                - Couriers which handled most shipments
                - High-rated couriers vs Fast delivery
                - Shipments are most expensive
                - Cost directly proportional to weight
                - Cities generate maximum cancellations
                - Routes are underperforming relative to distance
    """)


# ---------- PAGE 5: Creator Info ----------
elif page == "Creator Info":
    st.title("👨‍💻 Creator of this Project")
    st.write("""
    **Developed by:** CharlieJeba
    **Skills:** Python, SQL, Streamlit, Pandas
    """)
    st.image("https://via.placeholder.com/150", caption="Your Profile Picture", width=150)