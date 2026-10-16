import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from data_loader import load_all_data
from analytics_engine import (
    calculate_executive_kpis,
    get_negative_margin_analysis,
    get_return_cancellation_analysis,
    get_inventory_stockout_analysis,
    get_marketing_campaign_analysis,
    run_customer_segmentation,
    run_anomaly_detection
)
from decision_playbook import simulate_interventions, get_action_playbook_cards

# Page Configuration
st.set_page_config(
    page_title="THE MONEY LEAK | Business Decision-Support System",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #1E293B;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .leak-banner {
        background: linear-gradient(135deg, #FFF1F2 0%, #FFE4E6 100%);
        border-left: 5px solid #E11D48;
        padding: 16px 20px;
        border-radius: 8px;
        margin-bottom: 20px;
    }
    .success-banner {
        background: linear-gradient(135deg, #ECFDF5 0%, #D1FAE5 100%);
        border-left: 5px solid #10B981;
        padding: 16px 20px;
        border-radius: 8px;
        margin-bottom: 20px;
    }
    .badge-critical {
        background-color: #FEE2E2;
        color: #991B1B;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.8rem;
    }
    .badge-high {
        background-color: #FFEDD5;
        color: #9A3412;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.8rem;
    }
    .badge-medium {
        background-color: #FEF3C7;
        color: #92400E;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def get_cached_data():
    return load_all_data()

data = get_cached_data()
kpis = calculate_executive_kpis(data)

# Sidebar Navigation
with st.sidebar:
    st.image("https://img.icons8.com/isometric/100/money-box.png", width=70)
    st.title("THE MONEY LEAK")
    st.caption("Business Decision-Support Cockpit")
    st.markdown("---")
    
    view_option = st.radio(
        "Navigation",
        [
            "🏛️ Executive Diagnostic",
            "🏷️ Negative Margins & Pricing",
            "↩️ Cancellations & Returns",
            "📦 Inventory & Stockouts",
            "📢 Marketing & Ad Bleed",
            "👥 Customer Margin Profiling",
            "🎯 Decision Playbook & Simulator"
        ]
    )
    
    st.markdown("---")
    st.markdown("### 🔍 Global Filters")
    all_categories = sorted(data['products']['category'].unique().tolist())
    selected_categories = st.multiselect("Category Filter", all_categories, default=all_categories)
    
    st.markdown("---")
    st.info("💡 **Datathon Target**: Identify revenue/margin leakages, analyze drivers, and simulate executive actions.")

# ==============================================================================
# TAB 1: EXECUTIVE DIAGNOSTIC
# ==============================================================================
if view_option == "🏛️ Executive Diagnostic":
    st.markdown('<div class="main-title">Executive Diagnostic & Money Leak Waterfall</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Synthesizing 18,000 transactions, 5,000 inventory logs, and 1,200 ad campaigns into root-cause financial diagnostics.</div>', unsafe_allow_html=True)
    
    # Financial Alert Banner
    st.markdown(f"""
    <div class="leak-banner">
        <h4 style="margin: 0; color: #991B1B;">⚠️ CRITICAL MARGIN ALERT: Net Business Contribution is -$2.89 Million</h4>
        <p style="margin: 5px 0 0 0; color: #475569;">
            While Gross Revenue reached <strong>${kpis['total_gross_rev']:,.2f}</strong>, unmitigated ad spend (<strong>${kpis['total_ad_spend']:,.2f}</strong>), 
            76 upside-down products losing <strong>${kpis['negative_margin_loss']:,.2f}</strong>, and cancellation/return drag (<strong>${kpis['friction_lost_rev']:,.2f}</strong>) 
            are draining the company's operating margin. Total quantified recoverable leak: <strong>${kpis['total_quantified_leak']:,.2f}</strong>.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Top KPI Metrics Ribbon
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total Gross Revenue", f"${kpis['total_gross_rev']:,.2f}")
    with col2:
        st.metric("Completed Net Sales", f"${kpis['completed_net_rev']:,.2f}")
    with col3:
        st.metric("Realized Gross Profit", f"${kpis['completed_gp']:,.2f}", f"{kpis['completed_margin_pct']:.1f}% Margin")
    with col4:
        st.metric("Total Ad Spend", f"${kpis['total_ad_spend']:,.2f}", delta="-244% of GP", delta_color="inverse")
    with col5:
        st.metric("Net Contribution", f"${kpis['net_contribution']:,.2f}", delta="Severe Deficit", delta_color="inverse")

    st.markdown("---")

    # Financial Bridge / Waterfall Chart
    st.subheader("📊 The Money Leak Bridge: From Gross Revenue to Operating Deficit")
    
    waterfall_fig = go.Figure(go.Waterfall(
        name="P&L Flow",
        orientation="v",
        measure=["absolute", "relative", "relative", "relative", "relative", "relative", "relative", "total"],
        x=[
            "Gross Revenue",
            "Promotional Discounts",
            "Cancelled Orders",
            "Returned Orders",
            "Product COGS",
            "Loss from Upside-Down SKUs",
            "Marketing Ad Spend",
            "Net Operating Profit"
        ],
        textposition="outside",
        text=[
            f"+${kpis['total_gross_rev']/1e6:.2f}M",
            f"-${kpis['total_discounts']/1e6:.2f}M",
            f"-${kpis['cancelled_rev']/1e6:.2f}M",
            f"-${kpis['returned_rev']/1e6:.2f}M",
            f"-${(kpis['completed_cogs'] - kpis['negative_margin_loss'])/1e6:.2f}M",
            f"-${kpis['negative_margin_loss']/1e6:.2f}M",
            f"-${kpis['total_ad_spend']/1e6:.2f}M",
            f"-${abs(kpis['net_contribution'])/1e6:.2f}M"
        ],
        y=[
            kpis['total_gross_rev'],
            -kpis['total_discounts'],
            -kpis['cancelled_rev'],
            -kpis['returned_rev'],
            -(kpis['completed_cogs'] - kpis['negative_margin_loss']),
            -kpis['negative_margin_loss'],
            -kpis['total_ad_spend'],
            kpis['net_contribution']
        ],
        connector={"line": {"color": "#94A3B8"}},
        decreasing={"marker": {"color": "#EF4444"}},
        increasing={"marker": {"color": "#10B981"}},
        totals={"marker": {"color": "#6366F1"}}
    ))
    waterfall_fig.update_layout(
        height=450,
        margin=dict(l=20, r=20, t=30, b=20),
        yaxis_title="USD ($)",
        waterfallgap=0.25
    )
    st.plotly_chart(waterfall_fig, use_container_width=True)

    # Top 5 Leak Drivers Breakdown
    st.markdown("### 🔎 The 5 Critical Leak Vectors")
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown("""
        **1. Negative Unit Margin Trap (30.4% of Catalog)**
        - **Impact:** `-$1,214,115.50` lost directly on 5,315 completed orders.
        - **Driver:** 76 products have `unit_cost > list_price`. Every unit sold guarantees a loss.
        - **Remedy:** Automated price floor (`Cost / 0.75`) or immediate delisting.
        
        **2. Bleeding Performance Ad Spend ($4.81M)**
        - **Impact:** Exceeds realized gross profit by 2.44x; 56 campaigns exceed $50 CPA.
        - **Driver:** Uncapped bidding on low-margin categories (Beauty spent $870k for $66k gross profit).
        - **Remedy:** Pause campaigns with CPA > $40; reallocate to high ROAS channels.
        
        **3. Excessive Transaction Discounts ($773K)**
        - **Impact:** Direct cash erosion reducing gross profit to zero on borderline SKUs.
        - **Driver:** Up to 25% promotions stacked on top of already markdown prices.
        - **Remedy:** Cap promotions at 10% and prohibit discounts on products with gross margin < 20%.
        """)
        
    with c2:
        st.markdown("""
        **4. Cancellation & Return Friction ($1.62M Drag)**
        - **Impact:** 1,689 cancellations ($862k) and 1,431 returns ($760k) + reverse freight.
        - **Driver:** Outlier SKUs with return rates up to 16% (PR0198, PR0184, PR0066).
        - **Remedy:** Supplier defect audits, packaging improvements, and accurate sizing/spec descriptions.
        
        **5. Stockout Demand Bleed ($508K Lost Revenue)**
        - **Impact:** 760 stockout days on high-selling products; ~$250K lost gross profit.
        - **Driver:** Inadequate reorder thresholds combined with supplier lead delays (10-12 days).
        - **Remedy:** Dynamic safety stock calibration ($SS = 1.65 \cdot \sigma_d \sqrt{L}$) and reorder point buffer.
        """)

# ==============================================================================
# TAB 2: NEGATIVE MARGINS & PRICING
# ==============================================================================
elif view_option == "🏷️ Negative Margins & Pricing":
    st.markdown('<div class="main-title">Negative Margin Audit & Pricing Inconsistencies</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Investigating the 76 products where unit costs exceed list price, creating guaranteed operational losses.</div>', unsafe_allow_html=True)
    
    margin_audit = get_negative_margin_analysis(data)
    neg_prods = margin_audit['negative_margin_products']
    all_prods = margin_audit['all_products']
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Catalog SKUs", len(all_prods))
    with col2:
        st.metric("Negative Margin SKUs", f"{margin_audit['negative_count']} (30.4%)", delta="Critical", delta_color="inverse")
    with col3:
        st.metric("Realized Gross Loss on Sales", f"${margin_audit['total_loss']:,.2f}", delta="Eroded Margin", delta_color="inverse")
    with col4:
        st.metric("Orders Sold at a Loss", f"{kpis['negative_margin_order_count']:,} (38.1%)")

    st.markdown("---")
    
    # Scatter plot: Unit Cost vs List Price
    fig_scatter = px.scatter(
        all_prods,
        x='unit_cost',
        y='list_price',
        color='is_negative_margin',
        color_discrete_map={True: '#EF4444', False: '#10B981'},
        hover_data=['product_id', 'category', 'unit_cost', 'list_price', 'gross_profit'],
        labels={'is_negative_margin': 'Unit Cost > List Price', 'unit_cost': 'Unit Cost ($)', 'list_price': 'List Price ($)'},
        title="Product Catalog Economics: Unit Cost vs List Price"
    )
    # Add diagonal break-even line
    max_val = max(all_prods['unit_cost'].max(), all_prods['list_price'].max())
    fig_scatter.add_shape(
        type='line',
        x0=0, y0=0, x1=max_val, y1=max_val,
        line=dict(color='#64748B', dash='dash', width=2)
    )
    fig_scatter.add_annotation(
        x=200, y=180,
        text="Break-even line (Cost = Price). Red dots are loss-making SKUs.",
        showarrow=False,
        font=dict(color='#DC2626')
    )
    fig_scatter.update_layout(height=450)
    st.plotly_chart(fig_scatter, use_container_width=True)

    # Detailed Table of Negative Margin SKUs
    st.subheader("📋 Top 20 Most Loss-Making Products in Completed Sales")
    
    loss_table = neg_prods[[
        'product_id', 'category', 'unit_cost', 'list_price', 'orders', 
        'units_sold', 'net_revenue', 'cogs', 'gross_profit', 'recommended_list_price', 'recommended_price_hike'
    ]].head(20).copy()
    
    st.dataframe(
        loss_table.style.format({
            'unit_cost': '${:,.2f}',
            'list_price': '${:,.2f}',
            'orders': '{:,}',
            'units_sold': '{:,}',
            'net_revenue': '${:,.2f}',
            'cogs': '${:,.2f}',
            'gross_profit': '${:,.2f}',
            'recommended_list_price': '${:,.2f}',
            'recommended_price_hike': '+${:,.2f}'
        }).background_gradient(subset=['gross_profit'], cmap='Reds_r'),
        use_container_width=True
    )

    # Pricing Simulator
    st.markdown("### 🧮 Interactive Pricing Remedy Simulator")
    target_margin = st.slider("Target Gross Margin for Repricing (%)", min_value=15, max_value=45, value=25, step=5)
    
    # Calculate recovery under selected target margin
    # New Price = Unit Cost / (1 - target_margin/100)
    sim_new_prices = neg_prods['unit_cost'] / (1 - (target_margin / 100.0))
    sim_gross_margin = (sim_new_prices * neg_prods['units_sold']) - neg_prods['cogs']
    sim_recovery = sim_gross_margin.sum() - neg_prods['gross_profit'].sum()
    
    st.success(f"💡 Repricing these 76 SKUs to achieve a **{target_margin}% Target Gross Margin** will reclaim **+${sim_recovery:,.2f}** in direct gross profit!")

# ==============================================================================
# TAB 3: CANCELLATIONS & RETURNS
# ==============================================================================
elif view_option == "↩️ Cancellations & Returns":
    st.markdown('<div class="main-title">Cancellations, Returns & Operational Friction</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Root-cause investigation of customer friction, high-return SKUs, and reverse logistics costs.</div>', unsafe_allow_html=True)
    
    ret_analysis = get_return_cancellation_analysis(data)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Order Volume", "18,000")
    with col2:
        st.metric("Cancelled Orders", f"1,689 (9.4%)", f"-${kpis['cancelled_rev']:,.2f} Lost Rev", delta_color="inverse")
    with col3:
        st.metric("Returned Orders", f"1,431 (8.0%)", f"-${kpis['returned_rev']:,.2f} Lost Rev", delta_color="inverse")
    with col4:
        st.metric("Reverse Freight/Restock Cost", f"${kpis['total_return_handling']:,.2f}", delta="Processing Drag", delta_color="inverse")

    st.markdown("---")

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Category Return & Cancellation Rates")
        cat_df = ret_analysis['by_category']
        fig_cat = px.bar(
            cat_df,
            x='category',
            y=['cancel_rate', 'return_rate'],
            barmode='group',
            labels={'value': 'Rate (%)', 'variable': 'Status Metric'},
            color_discrete_map={'cancel_rate': '#F97316', 'return_rate': '#EF4444'},
            title="Cancellation & Return Rate by Product Category"
        )
        fig_cat.update_layout(height=380)
        st.plotly_chart(fig_cat, use_container_width=True)

    with col_b:
        st.subheader("Friction by Sales Channel")
        chan_df = ret_analysis['by_channel']
        fig_chan = px.bar(
            chan_df,
            x='channel',
            y=['cancel_rate', 'return_rate'],
            barmode='group',
            labels={'value': 'Rate (%)', 'variable': 'Status Metric'},
            color_discrete_map={'cancel_rate': '#3B82F6', 'return_rate': '#8B5CF6'},
            title="Cancellation & Return Rate by Channel"
        )
        fig_chan.update_layout(height=380)
        st.plotly_chart(fig_chan, use_container_width=True)

    st.markdown("---")

    # High-Return Outlier SKUs
    st.subheader("🚨 Outlier High-Return SKUs (Z-Score > 1.5)")
    st.markdown("These products exhibit return rates up to 16.0% (double the store average), indicating potential sizing defects, poor packaging, or inaccurate listings.")
    
    high_ret_table = ret_analysis['high_return_skus'][[
        'product_id', 'category', 'total_orders', 'returned_orders', 'return_rate', 'return_zscore', 'returned_value'
    ]].copy()
    
    st.dataframe(
        high_ret_table.style.format({
            'total_orders': '{:,}',
            'returned_orders': '{:,}',
            'return_rate': '{:.2f}%',
            'return_zscore': '{:.2f}',
            'returned_value': '${:,.2f}'
        }).background_gradient(subset=['return_rate'], cmap='Reds'),
        use_container_width=True
    )

# ==============================================================================
# TAB 4: INVENTORY & STOCKOUTS
# ==============================================================================
elif view_option == "📦 Inventory & Stockouts":
    st.markdown('<div class="main-title">Inventory Health, Stockouts & Safety Stock Deficits</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Tracking ghost demand, supplier delays, and quantifying lost revenue from out-of-stock events.</div>', unsafe_allow_html=True)
    
    inv_analysis = get_inventory_stockout_analysis(data)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Stockout Incidents", f"{inv_analysis['total_stockout_incidents']:,}", delta="15.2% of Days", delta_color="inverse")
    with col2:
        st.metric("Estimated Lost Demand", f"${inv_analysis['total_estimated_lost_rev']:,.2f}", delta="Uncaptured Gross Sales", delta_color="inverse")
    with col3:
        st.metric("Estimated Lost Gross Profit", f"${inv_analysis['total_estimated_lost_margin']:,.2f}", delta="Reclaimable", delta_color="inverse")
    with col4:
        st.metric("Average Supplier Delay", "9.6 Days", delta="Lead Time Friction", delta_color="inverse")

    st.markdown("---")

    # Stockout vs Demand Collision
    st.subheader("⚠️ Top High-Risk Stockout SKUs & Safety Stock Shortfalls")
    st.markdown("These items suffer frequent stockouts while carrying inadequate reorder thresholds relative to daily demand velocity and supplier lead times.")
    
    top_inv = inv_analysis['top_stockout_products'][[
        'product_id', 'category', 'stockout_days', 'stockout_pct', 'avg_stock_on_hand',
        'avg_reorder_threshold', 'recommended_rop', 'rop_deficit', 'estimated_lost_revenue', 'estimated_lost_margin'
    ]].copy()
    
    st.dataframe(
        top_inv.style.format({
            'stockout_days': '{:,}',
            'stockout_pct': '{:.1f}%',
            'avg_stock_on_hand': '{:.0f}',
            'avg_reorder_threshold': '{:.0f}',
            'recommended_rop': '{:.0f}',
            'rop_deficit': '+{:.0f} units',
            'estimated_lost_revenue': '${:,.2f}',
            'estimated_lost_margin': '${:,.2f}'
        }).background_gradient(subset=['stockout_days'], cmap='Oranges'),
        use_container_width=True
    )

    col_x, col_y = st.columns(2)
    with col_x:
        # Category stockout distribution
        cat_inv = inv_analysis['inventory_summary'].groupby('category').agg(
            total_stockouts=('stockout_days', 'sum'),
            total_lost_rev=('estimated_lost_revenue', 'sum')
        ).reset_index()
        fig_inv = px.bar(
            cat_inv,
            x='category',
            y='total_lost_rev',
            color='total_stockouts',
            color_continuous_scale='Reds',
            labels={'total_lost_rev': 'Lost Revenue ($)', 'category': 'Category'},
            title="Estimated Lost Revenue from Stockouts by Category"
        )
        st.plotly_chart(fig_inv, use_container_width=True)

    with col_y:
        st.markdown("""
        ### 📋 Supply Chain Diagnostic Findings:
        1. **High Lead Time + Delay Multiplier:** Base supplier lead days average 14.2 days, and supplier delays add another 9.6 days. Average replenishment cycle is ~24 days.
        2. **Threshold Under-Calibrated:** Current reorder thresholds average 44 units, whereas optimal Reorder Point ($ROP$) for high-velocity SKUs is 75-110 units.
        3. **Marketing Collision Risk:** Ad campaigns continuously drove traffic to Electronics and Grocery categories during periods where top-selling SKUs were at zero inventory.
        """)

# ==============================================================================
# TAB 5: MARKETING & AD BLEED
# ==============================================================================
elif view_option == "📢 Marketing & Ad Bleed":
    st.markdown('<div class="main-title">Marketing Campaign Efficiency & Ad Spend Audit</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Evaluating $4.81M in ad spend across 1,200 campaigns to eliminate extreme CPA outliers.</div>', unsafe_allow_html=True)
    
    mkt_analysis = get_marketing_campaign_analysis(data)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Marketing Spend", f"${kpis['total_ad_spend']:,.2f}")
    with col2:
        st.metric("Spend / Completed Profit", "244.0%", delta="Over-Budget", delta_color="inverse")
    with col3:
        st.metric("Bleeding Campaigns (CPA > $50)", len(mkt_analysis['bleeding_campaigns']))
    with col4:
        st.metric("Bleeding Spend to Cut", f"${mkt_analysis['total_bleeding_spend']:,.2f}", delta="Reclaimable", delta_color="normal")

    st.markdown("---")

    # Category P&L Table
    st.subheader("📉 Category Level P&L: Gross Profit vs Ad Spend")
    st.markdown("Every single product category generated a **negative net contribution** after marketing expenses. Beauty lost -$803K alone.")
    
    cat_pnl = mkt_analysis['category_pnl']
    st.dataframe(
        cat_pnl.style.format({
            'net_revenue': '${:,.2f}',
            'cogs': '${:,.2f}',
            'gross_profit': '${:,.2f}',
            'ad_spend': '${:,.2f}',
            'net_contribution': '${:,.2f}',
            'roas': '{:.2f}x',
            'overall_cpa': '${:,.2f}'
        }).background_gradient(subset=['net_contribution'], cmap='Reds_r'),
        use_container_width=True
    )

    # CPA Distribution & Slider
    st.markdown("---")
    st.subheader("🎯 CPA Cut-Off & Campaign Kill-Switch Simulator")
    
    cpa_threshold = st.slider("Select Maximum Acceptable CPA ($)", min_value=15, max_value=80, value=40, step=5)
    
    camp_df = data['campaigns']
    pruned_camps = camp_df[camp_df['cpa'] > cpa_threshold]
    saved_spend = pruned_camps['spend'].sum()
    lost_convs = pruned_camps['conversions'].sum()
    
    st.warning(f"✂️ Cutting campaigns with **CPA > ${cpa_threshold}** will save **${saved_spend:,.2f}** in marketing spend, forfeiting only **{lost_convs:,}** low-margin conversions!")

    # Top Worst Campaigns Table
    st.subheader("🚨 Worst 15 Bleeding Campaigns by Cost Per Acquisition (CPA)")
    worst_camps = pruned_camps.sort_values(by='cpa', ascending=False).head(15)[[
        'campaign_id', 'date', 'channel', 'category', 'spend', 'impressions', 'clicks', 'conversions', 'cpa'
    ]].copy()
    
    st.dataframe(
        worst_camps.style.format({
            'spend': '${:,.2f}',
            'impressions': '{:,}',
            'clicks': '{:,}',
            'conversions': '{:,}',
            'cpa': '${:,.2f}'
        }).background_gradient(subset=['cpa'], cmap='Reds'),
        use_container_width=True
    )

# ==============================================================================
# TAB 6: CUSTOMER MARGIN PROFILING
# ==============================================================================
elif view_option == "👥 Customer Margin Profiling":
    st.markdown('<div class="main-title">Customer Margin Profiling (RFM-M)</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Segmenting 3,000 customers by Recency, Frequency, Monetary Value, and true Net Margin Contribution.</div>', unsafe_allow_html=True)
    
    rfm = run_customer_segmentation(data)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Customers Audited", f"{len(rfm):,}")
    with col2:
        st.metric("Profitable Champions", f"{(rfm['value_tier'] == 'Profitable Champion').sum():,}")
    with col3:
        st.metric("Margin Drainers", f"{(rfm['value_tier'] == 'Margin Drainer (Negative Margin)').sum():,}", delta="Negative Margin", delta_color="inverse")
    with col4:
        st.metric("Discount Seekers", f"{(rfm['value_tier'] == 'Discount Seeker / Low Margin').sum():,}")

    st.markdown("---")

    # RFM Segment Distribution
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        st.subheader("Customer Distribution by Value Profile")
        tier_counts = rfm['value_tier'].value_counts().reset_index()
        tier_counts.columns = ['value_tier', 'count']
        fig_tier = px.pie(
            tier_counts,
            names='value_tier',
            values='count',
            color='value_tier',
            color_discrete_map={
                'Profitable Champion': '#10B981',
                'General Regular': '#60A5FA',
                'Discount Seeker / Low Margin': '#F59E0B',
                'At-Risk / Dormant': '#94A3B8',
                'Margin Drainer (Negative Margin)': '#EF4444'
            },
            hole=0.4
        )
        fig_tier.update_layout(height=380)
        st.plotly_chart(fig_tier, use_container_width=True)

    with col_r2:
        st.subheader("Gross Profit Contribution by Tier")
        tier_profit = rfm.groupby('value_tier')['gross_profit'].sum().reset_index()
        fig_p = px.bar(
            tier_profit,
            x='value_tier',
            y='gross_profit',
            color='gross_profit',
            color_continuous_scale='Tealrose',
            labels={'gross_profit': 'Total Realized Profit ($)', 'value_tier': 'Customer Segment'},
            title="Realized Margin Contribution by Tier"
        )
        fig_p.update_layout(height=380)
        st.plotly_chart(fig_p, use_container_width=True)

    st.markdown("---")
    st.markdown("""
    ### 💡 Key Customer Strategy Takeaway:
    - **Margin Drainers (705 customers):** These accounts repeatedly buy negative-margin products with promo codes, causing net losses for the business. 
    - **Action:** Suppress discount codes for these accounts and restrict promotional mailings to high-margin products.
    """)

# ==============================================================================
# TAB 7: DECISION PLAYBOOK & SIMULATOR
# ==============================================================================
elif view_option == "🎯 Decision Playbook & Simulator":
    st.markdown('<div class="main-title">Strategic Decision Playbook & What-If Simulator</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Empowering the manager to toggle prescriptive interventions, simulate P&L recovery, and generate an executive briefing.</div>', unsafe_allow_html=True)

    st.markdown("### 🎛️ Interactive Strategic Intervention Controls")
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 1. Pricing & Promotions Levers")
        reprice_skus = st.checkbox("🏷️ Reprice 76 Negative-Margin SKUs (Target 25% Gross Margin)", value=True)
        delist_skus = st.checkbox("🚫 Delist / Discontinue Negative-Margin SKUs", value=False, disabled=reprice_skus)
        cap_disc = st.checkbox("✂️ Cap Maximum Promotional Discount at 10%", value=True)
        forbid_low_margin_disc = st.checkbox("🛡️ Forbid Discounts on Low-Margin SKUs (<20% Base Margin)", value=True)
        
    with c2:
        st.markdown("#### 2. Marketing & Supply Chain Levers")
        pause_ads = st.checkbox("🛑 Kill Inefficient Ad Campaigns (CPA > $40)", value=True)
        fix_stockouts = st.checkbox("📦 Calibrate Safety Stock on Top 20 Stockout SKUs", value=True)
        mitigate_returns = st.checkbox("🔍 Quality & Sizing Audit on Top 19 High-Return SKUs (-35% returns)", value=True)

    # Run Simulation
    levers = {
        'reprice_negative_skus': reprice_skus,
        'delist_negative_skus': delist_skus,
        'cap_discounts': cap_disc,
        'forbid_discount_low_margin': forbid_low_margin_disc,
        'pause_high_cpa_ads': pause_ads,
        'fix_stockouts_top20': fix_stockouts,
        'reduce_returns_top_skus': mitigate_returns
    }
    sim_result = simulate_interventions(data, levers)

    st.markdown("---")
    
    # Financial Impact Summary
    st.markdown("### 📈 Projected P&L Recovery Simulation")
    
    s1, s2, s3 = st.columns(3)
    with s1:
        st.metric("Baseline Net Contribution", f"${sim_result['baseline_net_contrib']:,.2f}", delta="Severe Deficit", delta_color="inverse")
    with s2:
        st.metric("Total Simulated Profit Recovered", f"+${sim_result['total_recovered']:,.2f}", delta="Reclaimed Cash", delta_color="normal")
    with s3:
        st.metric("Simulated Net Contribution", f"${sim_result['simulated_net_contrib']:,.2f}", 
                  delta=f"+${(sim_result['simulated_net_contrib'] - sim_result['baseline_net_contrib']):,.2f} Improvement", 
                  delta_color="normal")

    # Recovery Breakdown Bar Chart
    breakdown_df = pd.DataFrame(list(sim_result['breakdown'].items()), columns=['Intervention', 'Recovery Value ($)'])
    fig_rec = px.bar(
        breakdown_df,
        x='Intervention',
        y='Recovery Value ($)',
        color='Recovery Value ($)',
        color_continuous_scale='Greens',
        text_auto='.2s',
        title="Breakdown of Profit Recovery by Strategic Lever"
    )
    fig_rec.update_layout(height=380)
    st.plotly_chart(fig_rec, use_container_width=True)

    st.markdown("---")

    # Action Cards: "What appears to be going wrong, what evidence supports it, and what action should the manager take?"
    st.subheader("📋 Prescriptive Decision Cards (The Triad Framework)")
    cards = get_action_playbook_cards()
    
    for card in cards:
        with st.expander(f"📌 [{card['severity']}] {card['id']}: {card['title']} — {card['financial_impact']}", expanded=(card['severity']=='CRITICAL')):
            st.markdown(f"""
            - **🔴 What Appears to be Going Wrong:**  
              {card['what_going_wrong']}
            - **📊 Supporting Evidence & Data:**  
              {card['evidence']}
            - **💡 Recommended Action for Manager:**  
              {card['recommended_action']}
            - **💰 Financial Impact:** `{card['financial_impact']}` | **👤 Department Owner:** `{card['owner']}` | **⏱️ Urgency:** `{card['urgency']}`
            """)

    # Download Executive Report
    st.markdown("---")
    st.subheader("📑 Export Executive Decision Briefing")
    
    report_text = f"""================================================================================
EXECUTIVE DECISION BRIEFING: THE MONEY LEAK RECOVERY PLAN
Generated for Retail & Business Leadership
================================================================================

1. FINANCIAL SUMMARY & CURRENT BASELINE:
   - Total Gross Sales: ${kpis['total_gross_rev']:,.2f}
   - Promotional Discounts Given: ${kpis['total_discounts']:,.2f}
   - Completed Net Revenue: ${kpis['completed_net_rev']:,.2f}
   - Realized Gross Profit: ${kpis['completed_gp']:,.2f} ({kpis['completed_margin_pct']:.1f}% Margin)
   - Total Marketing Ad Spend: ${kpis['total_ad_spend']:,.2f} (244% of GP)
   - CURRENT NET BUSINESS CONTRIBUTION: ${kpis['net_contribution']:,.2f} (OPERATING DEFICIT)

2. TOTAL QUANTIFIED LEAKAGE: ${kpis['total_quantified_leak']:,.2f}
   - Upside-Down Product Pricing Loss: ${kpis['negative_margin_loss']:,.2f}
   - Promotional Discount Drag: ${kpis['total_discounts']:,.2f}
   - Cancellations & Returns Value Lost: ${kpis['friction_lost_rev']:,.2f}
   - Bleeding Performance Ad Spend: ${kpis['inefficient_ad_spend']:,.2f}
   - Inventory Stockout Lost Gross Profit: ${kpis['estimated_stockout_lost_gp']:,.2f}

3. SIMULATED STRATEGIC RECOVERY:
   - Total Reclaimed Profit: +${sim_result['total_recovered']:,.2f}
   - Projected Post-Intervention Net Contribution: ${sim_result['simulated_net_contrib']:,.2f}

4. TOP ACTION ITEMS & OWNERSHIP:
   [1] Merchandising: Reprice/delist 76 negative margin SKUs (Expected recovery: +$1.17M)
   [2] Marketing: Cap ad sets with CPA > $40 (Expected savings: +$350K)
   [3] Sales Ops: Cap promotional discount at 10% (Expected recovery: +$250K)
   [4] Supply Chain: Adjust Reorder Points for top 20 stockout SKUs (Expected recovery: +$180K)
   [5] Quality/Logistics: Defect audit on top 19 high-return SKUs (Expected recovery: +$150K)
================================================================================
"""
    st.download_button(
        label="📥 Download Executive Briefing (TXT)",
        data=report_text,
        file_name="The_Money_Leak_Executive_Briefing.txt",
        mime="text/plain"
    )
