#!/usr/bin/env python3
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import requests
import json

# Check for openpyxl
try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

# Import your existing client
from analytics_client_clean import AnalyticsClient

# Page configuration - UPDATED
st.set_page_config(
    page_title="CS Analytics Dashboard",  # ← CHANGED
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Password protection function
def check_password():
    """Returns True if user enters correct password"""
    
    if st.session_state.get("authenticated", False):
        return True
    
    st.title("🔐 CS Analytics")  # ← CHANGED (optional)
    st.markdown("### Please login to access the dashboard")
    st.markdown("---")
    
    with st.form("login_form"):
        password = st.text_input("Enter Password", type="password", placeholder="Enter your password")
        col1, col2 = st.columns([1, 5])
        with col1:
            submit = st.form_submit_button("Login", width="stretch")
        
        if submit:
            if password == "codesquad2024":
                st.session_state.authenticated = True
                st.success("Login successful! Redirecting...")
                st.rerun()
            else:
                st.error("❌ Incorrect password. Please try again.")
    
    st.markdown("---")
    st.caption("Contact administrator for access")
    
    return False

# Initialize client
@st.cache_resource
def get_client():
    return AnalyticsClient("https://centralsoft.com.my")

# Cache data to avoid repeated API calls
@st.cache_data(ttl=300)
def fetch_dashboard_data(company_id):
    client = get_client()
    return client.get_dashboard(company_id)

# Helper functions for type conversion
def safe_float(value, default=0):
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default

def safe_int(value, default=0):
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except ValueError:
            return default
    return default

def main():
    # Check authentication FIRST
    if not check_password():
        st.stop()
    
    # Sidebar - UPDATED
    with st.sidebar:
        st.title("📊 CS Analytics")  # ← CHANGED
        
        # Company selector
        company_id = st.text_input("Company ID", value="codesquad")
        
        st.markdown("---")
        st.markdown("### Filters")
        
        # Date range filter
        days_back = st.slider("Days to analyze", 7, 90, 30)
        
        st.markdown("---")
        st.markdown("### Export Options")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📥 CSV", width="stretch"):
                client = get_client()
                client.export_to_csv(company_id)
                st.success("CSV exported!")
        
        with col2:
            if st.button("📊 Excel", width="stretch"):
                if OPENPYXL_AVAILABLE:
                    client = get_client()
                    client.export_to_excel_pandas(company_id)
                    st.success("Excel exported!")
                else:
                    st.error("Install openpyxl: pip install openpyxl")
        
        st.markdown("---")
        st.markdown(f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Main content area - UPDATED
    st.title("📈 CS Analytics Dashboard")  # ← CHANGED
    st.markdown("---")
    
    # Fetch data
    with st.spinner("Loading dashboard data..."):
        dashboard_data = fetch_dashboard_data(company_id)
    
    if not dashboard_data or not dashboard_data.get('success'):
        st.error("Failed to load dashboard data. Please check your connection and company ID.")
        return
    
    data = dashboard_data['data']
    company = data.get('company', {})
    summary = data.get('summary', {})
    invoices = data.get('recent_invoices', [])
    
    # Convert invoices to DataFrame
    df = pd.DataFrame(invoices)
    if not df.empty and 'net_amount' in df.columns:
        df['net_amount'] = pd.to_numeric(df['net_amount'], errors='coerce')
    if not df.empty and 'invoice_date' in df.columns:
        df['invoice_date'] = pd.to_datetime(df['invoice_date'], errors='coerce')
        if df['invoice_date'].dt.tz is not None:
            df['invoice_date'] = df['invoice_date'].dt.tz_localize(None)
    
    # Safely extract summary values
    total_invoices = safe_int(summary.get('total_invoices', 0))
    total_revenue = safe_float(summary.get('total_revenue', 0))
    avg_invoice = safe_float(summary.get('avg_invoice', 0))
    validated_count = safe_int(summary.get('validated_count', 0))
    
    # Calculate validation rate
    validation_rate = (validated_count / total_invoices * 100) if total_invoices > 0 else 0
    
    # Top KPI Cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📄 Total Invoices", f"{total_invoices:,}")
    
    with col2:
        st.metric("💰 Total Revenue", f"RM {total_revenue:,.2f}")
    
    with col3:
        st.metric("📊 Average Invoice", f"RM {avg_invoice:,.2f}")
    
    with col4:
        st.metric("✅ LHDN Validation Rate", f"{validation_rate:.1f}%", delta=f"{validated_count}/{total_invoices}")
    
    st.markdown("---")
    
    # Company Info Row
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info(f"🏢 **Company:** {company.get('companyName', 'N/A')}")
    with col2:
        st.info(f"🏭 **Industry:** {company.get('industry', 'N/A')}")
    with col3:
        st.info(f"📋 **LHDN TIN:** {company.get('lhdnTinNo', 'N/A')}")
    
    st.markdown("---")
    
    # Charts Row - First Row
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Revenue by Invoice")
        if not df.empty and 'net_amount' in df.columns:
            chart_df = df[df['net_amount'].notna()].copy()
            if not chart_df.empty:
                fig = px.bar(
                    chart_df,
                    x='invoice_no',
                    y='net_amount',
                    title='Invoice Amounts',
                    labels={'invoice_no': 'Invoice Number', 'net_amount': 'Amount (RM)'},
                    color='lhdn_status' if 'lhdn_status' in chart_df.columns else None,
                    text='net_amount'
                )
                fig.update_traces(texttemplate='RM %{text:,.0f}', textposition='outside')
                fig.update_layout(height=450, title_x=0.5)
                st.plotly_chart(fig, width="stretch")
            else:
                st.info("No valid amount data available for chart")
        else:
            st.info("No invoice data available for chart")
    
    with col2:
        st.subheader("📈 Revenue by Status")
        if not df.empty and 'net_amount' in df.columns and 'lhdn_status' in df.columns:
            status_summary = df.groupby('lhdn_status')['net_amount'].sum().reset_index()
            status_summary = status_summary[status_summary['net_amount'] > 0]
            if not status_summary.empty:
                fig = px.pie(
                    status_summary,
                    values='net_amount',
                    names='lhdn_status',
                    title='Revenue Distribution by LHDN Status',
                    hole=0.3
                )
                fig.update_traces(textposition='inside', textinfo='percent+label')
                fig.update_layout(height=450, title_x=0.5)
                st.plotly_chart(fig, width="stretch")
            else:
                st.info("No revenue data by status available")
        else:
            st.info("No invoice data available for chart")
    
    # Recent Invoices Table
    st.markdown("---")
    st.subheader("📋 Recent Invoices")
    if not df.empty:
        display_df = df.copy()
        if 'net_amount' in display_df.columns:
            display_df['net_amount'] = display_df['net_amount'].apply(
                lambda x: f"RM {x:,.2f}" if pd.notna(x) else "N/A"
            )
        if 'invoice_date' in display_df.columns:
            display_df['invoice_date'] = display_df['invoice_date'].dt.strftime('%Y-%m-%d')
        
        columns_to_show = ['invoice_no', 'partner_name', 'net_amount', 'lhdn_status', 'invoice_date']
        available_columns = [col for col in columns_to_show if col in display_df.columns]
        
        if available_columns:
            st.dataframe(
                display_df[available_columns],
                width="stretch",
                height=400,
                hide_index=True
            )
        else:
            st.info("No displayable columns found")
    else:
        st.info("No invoice data available")

if __name__ == "__main__":
    main()