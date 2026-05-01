#!/usr/bin/env python3
# dashboard_app.py - Complete Professional Dashboard with Fixed Excel Export

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

# Page configuration
st.set_page_config(
    page_title="Code Squad Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .stMetric {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 10px;
    }
    .main-header {
        font-size: 2.5rem;
        color: #2c3e50;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

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
    # Sidebar
    with st.sidebar:
        st.image("https://centralsoft.com.my/company.png", width=150) if False else st.markdown("### 📊 Code Squad")
        st.title("📊 Analytics")
        
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
    
    # Main content area
    st.markdown("<h1 class='main-header'>📈 Code Squad Accounting Dashboard</h1>", unsafe_allow_html=True)
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
        # Remove timezone for Excel compatibility
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
        st.metric(
            "📄 Total Invoices",
            f"{total_invoices:,}",
            delta=None,
            help="Total number of invoices"
        )
    
    with col2:
        st.metric(
            "💰 Total Revenue",
            f"RM {total_revenue:,.2f}",
            delta=None,
            help="Sum of all invoice amounts"
        )
    
    with col3:
        st.metric(
            "📊 Average Invoice",
            f"RM {avg_invoice:,.2f}",
            delta=None,
            help="Average amount per invoice"
        )
    
    with col4:
        st.metric(
            "✅ LHDN Validation Rate",
            f"{validation_rate:.1f}%",
            delta=f"{validated_count}/{total_invoices}",
            help="Percentage of invoices validated by LHDN"
        )
    
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
                    color_discrete_map={
                        'VALIDATED': '#2ecc71',
                        'SUBMITTED': '#f39c12',
                        'NOT_SUBMITTED': '#e74c3c',
                        'REJECTED': '#c0392b'
                    } if 'lhdn_status' in chart_df.columns else None,
                    text='net_amount'
                )
                fig.update_traces(texttemplate='RM %{text:,.0f}', textposition='outside')
                fig.update_layout(
                    height=450,
                    showlegend=True,
                    title_x=0.5,
                    font=dict(size=12)
                )
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
                    color_discrete_sequence=px.colors.qualitative.Set3,
                    hole=0.3
                )
                fig.update_traces(textposition='inside', textinfo='percent+label')
                fig.update_layout(height=450, title_x=0.5)
                st.plotly_chart(fig, width="stretch")
            else:
                st.info("No revenue data by status available")
        else:
            st.info("No invoice data available for chart")
    
    # Charts Row - Second Row
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📉 Revenue Trend")
        if not df.empty and 'invoice_date' in df.columns and 'net_amount' in df.columns:
            df_sorted = df[df['invoice_date'].notna()].sort_values('invoice_date')
            if len(df_sorted) > 1:
                fig = px.line(
                    df_sorted,
                    x='invoice_date',
                    y='net_amount',
                    title='Revenue Trend Over Time',
                    labels={'invoice_date': 'Date', 'net_amount': 'Revenue (RM)'},
                    markers=True,
                    line_shape='linear'
                )
                fig.update_traces(marker=dict(size=10, symbol='circle'), line=dict(width=3))
                fig.update_layout(height=450, title_x=0.5)
                st.plotly_chart(fig, width="stretch")
            else:
                st.info("Not enough date data for trend analysis (need at least 2 data points)")
        else:
            st.info("No date data available for trend analysis")
    
    with col2:
        st.subheader("🏆 Top 5 Partners by Revenue")
        if not df.empty and 'net_amount' in df.columns and 'partner_name' in df.columns:
            top_partners = df.groupby('partner_name')['net_amount'].sum().nlargest(5).reset_index()
            top_partners = top_partners[top_partners['net_amount'] > 0]
            if not top_partners.empty:
                fig = px.bar(
                    top_partners,
                    x='partner_name',
                    y='net_amount',
                    title='Top Partners by Revenue',
                    labels={'partner_name': 'Partner', 'net_amount': 'Revenue (RM)'},
                    text='net_amount',
                    color='net_amount',
                    color_continuous_scale='Viridis'
                )
                fig.update_traces(
                    texttemplate='RM %{text:,.0f}',
                    textposition='outside',
                    textfont=dict(size=11)
                )
                fig.update_layout(height=450, title_x=0.5, xaxis_tickangle=-45)
                st.plotly_chart(fig, width="stretch")
            else:
                st.info("No partner revenue data available")
        else:
            st.info("No partner data available")
    
    # Status Distribution Chart
    st.markdown("---")
    st.subheader("📊 Invoice Status Distribution")
    if not df.empty and 'lhdn_status' in df.columns:
        status_counts = df['lhdn_status'].value_counts().reset_index()
        status_counts.columns = ['Status', 'Count']
        fig = px.bar(
            status_counts,
            x='Status',
            y='Count',
            title='Number of Invoices by Status',
            labels={'Status': 'LHDN Status', 'Count': 'Number of Invoices'},
            color='Status',
            color_discrete_map={
                'VALIDATED': '#2ecc71',
                'SUBMITTED': '#f39c12',
                'NOT_SUBMITTED': '#e74c3c',
                'REJECTED': '#c0392b'
            }
        )
        fig.update_layout(height=400, title_x=0.5)
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("No status data available")
    
    # Recent Invoices Table
    st.markdown("---")
    st.subheader("📋 Recent Invoices")
    if not df.empty:
        # Format the dataframe for display
        display_df = df.copy()
        if 'net_amount' in display_df.columns:
            display_df['net_amount'] = display_df['net_amount'].apply(
                lambda x: f"RM {x:,.2f}" if pd.notna(x) else "N/A"
            )
        if 'invoice_date' in display_df.columns:
            display_df['invoice_date'] = display_df['invoice_date'].dt.strftime('%Y-%m-%d') if not display_df['invoice_date'].isna().all() else display_df['invoice_date']
        
        # Select columns to display
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
    
    # Download buttons section
    st.markdown("---")
    st.subheader("📥 Download Reports")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if not df.empty:
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Download as CSV",
                data=csv,
                file_name=f"invoices_{company_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                width="stretch"
            )
    
    with col2:
        if not df.empty and OPENPYXL_AVAILABLE:
            # Create Excel with timezone-naive dates
            df_excel = df.copy()
            if 'invoice_date' in df_excel.columns:
                df_excel['invoice_date'] = pd.to_datetime(df_excel['invoice_date']).dt.strftime('%Y-%m-%d')
            
            from io import BytesIO
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_excel.to_excel(writer, sheet_name='Invoices', index=False)
                summary_df = pd.DataFrame([
                    ['Company Name', company.get('companyName', 'N/A')],
                    ['Industry', company.get('industry', 'N/A')],
                    ['LHDN TIN', company.get('lhdnTinNo', 'N/A')],
                    ['Report Date', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
                    ['', ''],
                    ['Total Invoices', total_invoices],
                    ['Total Revenue', f"RM {total_revenue:,.2f}"],
                    ['Average Invoice', f"RM {avg_invoice:,.2f}"],
                    ['LHDN Validated', f"{validated_count}/{total_invoices} ({validation_rate:.1f}%)"]
                ], columns=['Metric', 'Value'])
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
            excel_data = output.getvalue()
            
            st.download_button(
                label="📊 Download as Excel",
                data=excel_data,
                file_name=f"dashboard_{company_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width="stretch"
            )
        elif not df.empty:
            st.warning("⚠️ Excel export requires openpyxl. Run: pip install openpyxl")
    
    with col3:
        # JSON download
        st.download_button(
            label="📄 Download as JSON",
            data=json.dumps(dashboard_data, indent=2),
            file_name=f"dashboard_{company_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            width="stretch"
        )
    
    # Footer
    st.markdown("---")
    st.markdown(
        f"<p style='text-align: center; color: gray;'>© 2026 Code Squad Accounting System | Dashboard v2.0</p>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()