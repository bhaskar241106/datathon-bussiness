import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

def calculate_executive_kpis(data):
    """
    Computes top-level financial metrics and quantifies the primary money leaks.
    """
    tx = data['transactions']
    camp = data['campaigns']
    inv = data['inventory']
    prod = data['products']

    # Completed orders
    completed = tx[tx['status'] == 'Completed']
    cancelled = tx[tx['status'] == 'Cancelled']
    returned = tx[tx['status'] == 'Returned']
    pending = tx[tx['status'] == 'Pending']

    total_gross_rev = tx['gross_revenue'].sum()
    total_discounts = tx['discount_amount'].sum()
    total_net_rev = tx['net_revenue'].sum()

    completed_net_rev = completed['net_revenue'].sum()
    completed_cogs = completed['cogs'].sum()
    completed_gp = completed['gross_profit'].sum()
    completed_margin_pct = (completed_gp / completed_net_rev * 100) if completed_net_rev > 0 else 0

    total_ad_spend = camp['spend'].sum()
    total_return_handling = returned['return_handling_cost'].sum()

    # Net contribution before overhead = Realized Gross Profit - Ad Spend - Return Handling
    net_contribution = completed_gp - total_ad_spend - total_return_handling

    # 1. Negative Margin Leak
    loss_orders = completed[completed['gross_profit'] < 0]
    negative_margin_loss = abs(loss_orders['gross_profit'].sum())
    negative_margin_order_count = len(loss_orders)

    # 2. Cancellations & Returns Lost Revenue
    cancelled_rev = cancelled['net_revenue'].sum()
    returned_rev = returned['net_revenue'].sum()
    friction_lost_rev = cancelled_rev + returned_rev

    # 3. Ad Spend Bleed (Campaigns with CPA > $40)
    high_cpa_camps = camp[camp['cpa'] > 40]
    inefficient_ad_spend = high_cpa_camps['spend'].sum()

    # 4. Estimated Stockout Loss
    product_daily_sales = completed.groupby(['product_id', 'date'])['quantity'].sum().reset_index()
    avg_daily_demand = product_daily_sales.groupby('product_id')['quantity'].mean().reset_index(name='avg_daily_units')
    stockout_events = inv[inv['stockout_flag'] == 1].merge(avg_daily_demand, on='product_id', how='left').merge(prod, on='product_id', how='left')
    stockout_events['lost_units'] = stockout_events['avg_daily_units'].fillna(1.5)
    stockout_events['lost_rev'] = stockout_events['lost_units'] * stockout_events['list_price']
    stockout_events['lost_gp'] = stockout_events['lost_units'] * (stockout_events['list_price'] - stockout_events['unit_cost'])
    estimated_stockout_lost_rev = stockout_events['lost_rev'].sum()
    estimated_stockout_lost_gp = stockout_events[stockout_events['lost_gp'] > 0]['lost_gp'].sum()

    # Total Quantified Money Leak
    total_quantified_leak = (
        negative_margin_loss +
        total_discounts +
        friction_lost_rev +
        inefficient_ad_spend +
        estimated_stockout_lost_gp
    )

    return {
        'total_gross_rev': total_gross_rev,
        'total_discounts': total_discounts,
        'total_net_rev': total_net_rev,
        'completed_net_rev': completed_net_rev,
        'completed_cogs': completed_cogs,
        'completed_gp': completed_gp,
        'completed_margin_pct': completed_margin_pct,
        'total_ad_spend': total_ad_spend,
        'total_return_handling': total_return_handling,
        'net_contribution': net_contribution,
        'negative_margin_loss': negative_margin_loss,
        'negative_margin_order_count': negative_margin_order_count,
        'cancelled_rev': cancelled_rev,
        'returned_rev': returned_rev,
        'friction_lost_rev': friction_lost_rev,
        'inefficient_ad_spend': inefficient_ad_spend,
        'estimated_stockout_lost_rev': estimated_stockout_lost_rev,
        'estimated_stockout_lost_gp': estimated_stockout_lost_gp,
        'total_quantified_leak': total_quantified_leak
    }

def get_negative_margin_analysis(data):
    """
    Detailed audit of products with unit_cost > list_price or orders sold at loss.
    """
    tx = data['transactions']
    prod = data['products']

    completed = tx[tx['status'] == 'Completed']

    # Product-level summary
    prod_perf = completed.groupby('product_id').agg(
        orders=('transaction_id', 'count'),
        units_sold=('quantity', 'sum'),
        net_revenue=('net_revenue', 'sum'),
        cogs=('cogs', 'sum'),
        gross_profit=('gross_profit', 'sum'),
        avg_discount=('discount_pct', 'mean'),
        avg_realized_price=('unit_price', 'mean')
    ).reset_index()

    prod_audit = prod.merge(prod_perf, on='product_id', how='left')
    prod_audit['orders'] = prod_audit['orders'].fillna(0).astype(int)
    prod_audit['units_sold'] = prod_audit['units_sold'].fillna(0).astype(int)
    prod_audit['gross_profit'] = prod_audit['gross_profit'].fillna(0)
    prod_audit['realized_margin_pct'] = np.where(
        prod_audit['net_revenue'] > 0,
        prod_audit['gross_profit'] / prod_audit['net_revenue'] * 100,
        0
    )

    # Recommended price based on standard 30% gross margin target: Price = Cost / (1 - 0.30)
    prod_audit['recommended_list_price'] = (prod_audit['unit_cost'] / 0.70).round(2)
    prod_audit['recommended_price_hike'] = (prod_audit['recommended_list_price'] - prod_audit['list_price']).round(2)

    # Flag negative products
    neg_prods = prod_audit[prod_audit['is_negative_margin'] | (prod_audit['gross_profit'] < 0)].sort_values(
        by='gross_profit', ascending=True
    )

    return {
        'all_products': prod_audit,
        'negative_margin_products': neg_prods,
        'negative_count': len(prod[prod['is_negative_margin']]),
        'total_loss': abs(neg_prods[neg_prods['gross_profit'] < 0]['gross_profit'].sum())
    }

def get_return_cancellation_analysis(data):
    """
    Analyzes cancellation and return patterns across dimensions.
    """
    tx = data['transactions']

    # By category
    by_category = tx.groupby('category').agg(
        total_orders=('transaction_id', 'count'),
        completed=('status', lambda s: (s == 'Completed').sum()),
        cancelled=('status', lambda s: (s == 'Cancelled').sum()),
        returned=('status', lambda s: (s == 'Returned').sum()),
        pending=('status', lambda s: (s == 'Pending').sum()),
        cancelled_val=('net_revenue', lambda val: val[tx.loc[val.index, 'status'] == 'Cancelled'].sum()),
        returned_val=('net_revenue', lambda val: val[tx.loc[val.index, 'status'] == 'Returned'].sum())
    ).reset_index()

    by_category['cancel_rate'] = (by_category['cancelled'] / by_category['total_orders']) * 100
    by_category['return_rate'] = (by_category['returned'] / by_category['total_orders']) * 100

    # By channel
    by_channel = tx.groupby('channel').agg(
        total_orders=('transaction_id', 'count'),
        cancelled=('status', lambda s: (s == 'Cancelled').sum()),
        returned=('status', lambda s: (s == 'Returned').sum()),
        net_revenue=('net_revenue', 'sum')
    ).reset_index()
    by_channel['cancel_rate'] = (by_channel['cancelled'] / by_channel['total_orders']) * 100
    by_channel['return_rate'] = (by_channel['returned'] / by_channel['total_orders']) * 100

    # By payment method
    by_payment = tx.groupby('payment_method').agg(
        total_orders=('transaction_id', 'count'),
        cancelled=('status', lambda s: (s == 'Cancelled').sum()),
        returned=('status', lambda s: (s == 'Returned').sum())
    ).reset_index()
    by_payment['cancel_rate'] = (by_payment['cancelled'] / by_payment['total_orders']) * 100
    by_payment['return_rate'] = (by_payment['returned'] / by_payment['total_orders']) * 100

    # Outlier High-Return Products
    prod_ret = tx.groupby(['product_id', 'category']).agg(
        total_orders=('transaction_id', 'count'),
        returned_orders=('status', lambda s: (s == 'Returned').sum()),
        cancelled_orders=('status', lambda s: (s == 'Cancelled').sum()),
        returned_value=('net_revenue', lambda v: v[tx.loc[v.index, 'status'] == 'Returned'].sum())
    ).reset_index()
    prod_ret['return_rate'] = (prod_ret['returned_orders'] / prod_ret['total_orders']) * 100
    prod_ret['cancel_rate'] = (prod_ret['cancelled_orders'] / prod_ret['total_orders']) * 100

    # Calculate z-score for return rate
    mean_ret = prod_ret['return_rate'].mean()
    std_ret = prod_ret['return_rate'].std()
    prod_ret['return_zscore'] = (prod_ret['return_rate'] - mean_ret) / std_ret
    high_return_skus = prod_ret[prod_ret['return_zscore'] > 1.5].sort_values(by='returned_orders', ascending=False)

    return {
        'by_category': by_category,
        'by_channel': by_channel,
        'by_payment': by_payment,
        'high_return_skus': high_return_skus,
        'all_product_returns': prod_ret
    }

def get_inventory_stockout_analysis(data):
    """
    Identifies inventory stockouts, supplier delay impact, and safety stock shortfalls.
    """
    inv = data['inventory']
    tx = data['transactions']
    prod = data['products']

    # Daily sales velocity per product
    completed = tx[tx['status'] == 'Completed']
    daily_sales = completed.groupby(['product_id', 'date'])['quantity'].sum().reset_index()
    sales_stats = daily_sales.groupby('product_id').agg(
        avg_daily_demand=('quantity', 'mean'),
        std_daily_demand=('quantity', 'std')
    ).reset_index()
    sales_stats['std_daily_demand'] = sales_stats['std_daily_demand'].fillna(sales_stats['avg_daily_demand'] * 0.3)

    # Product inventory stats
    inv_stats = inv.groupby('product_id').agg(
        total_audit_days=('date', 'count'),
        stockout_days=('stockout_flag', 'sum'),
        avg_stock_on_hand=('stock_on_hand', 'mean'),
        min_stock=('stock_on_hand', 'min'),
        avg_reorder_threshold=('reorder_threshold', 'mean'),
        avg_supplier_delay=('supplier_delay_days', 'mean')
    ).reset_index()

    inv_merged = inv_stats.merge(prod, on='product_id', how='left').merge(sales_stats, on='product_id', how='left')
    inv_merged['avg_daily_demand'] = inv_merged['avg_daily_demand'].fillna(1.0)
    inv_merged['std_daily_demand'] = inv_merged['std_daily_demand'].fillna(0.5)

    inv_merged['stockout_pct'] = (inv_merged['stockout_days'] / inv_merged['total_audit_days']) * 100

    # Recommended Safety Stock: SS = Z * std_d * sqrt(LeadTime) [Z=1.65 for 95% service level]
    effective_lead_time = inv_merged['supplier_lead_days'] + inv_merged['avg_supplier_delay']
    inv_merged['recommended_safety_stock'] = (
        1.65 * inv_merged['std_daily_demand'] * np.sqrt(effective_lead_time)
    ).round().astype(int)

    # Recommended Reorder Point: ROP = (Avg Daily Demand * Lead Time) + Safety Stock
    inv_merged['recommended_rop'] = (
        (inv_merged['avg_daily_demand'] * effective_lead_time) + inv_merged['recommended_safety_stock']
    ).round().astype(int)

    inv_merged['rop_deficit'] = inv_merged['recommended_rop'] - inv_merged['avg_reorder_threshold']
    inv_merged['estimated_lost_sales_units'] = (inv_merged['stockout_days'] * inv_merged['avg_daily_demand']).round(1)
    inv_merged['estimated_lost_revenue'] = inv_merged['estimated_lost_sales_units'] * inv_merged['list_price']
    inv_merged['estimated_lost_margin'] = inv_merged['estimated_lost_sales_units'] * (inv_merged['list_price'] - inv_merged['unit_cost'])

    at_risk_inventory = inv_merged.sort_values(by='stockout_days', ascending=False)

    return {
        'inventory_summary': inv_merged,
        'top_stockout_products': at_risk_inventory.head(20),
        'total_stockout_incidents': int(inv['stockout_flag'].sum()),
        'total_estimated_lost_rev': inv_merged['estimated_lost_revenue'].sum(),
        'total_estimated_lost_margin': inv_merged[inv_merged['estimated_lost_margin'] > 0]['estimated_lost_margin'].sum()
    }

def get_marketing_campaign_analysis(data):
    """
    Detailed audit of ad spend, CPA, CVR, ROAS, and category contribution.
    """
    camp = data['campaigns']
    tx = data['transactions']

    completed = tx[tx['status'] == 'Completed']

    # Category P&L
    cat_sales = completed.groupby('category').agg(
        net_revenue=('net_revenue', 'sum'),
        cogs=('cogs', 'sum'),
        gross_profit=('gross_profit', 'sum')
    )

    cat_marketing = camp.groupby('category').agg(
        ad_spend=('spend', 'sum'),
        impressions=('impressions', 'sum'),
        clicks=('clicks', 'sum'),
        conversions=('conversions', 'sum')
    )

    cat_pnl = cat_sales.join(cat_marketing)
    cat_pnl['net_contribution'] = cat_pnl['gross_profit'] - cat_pnl['ad_spend']
    cat_pnl['roas'] = cat_pnl['net_revenue'] / cat_pnl['ad_spend']
    cat_pnl['overall_cpa'] = cat_pnl['ad_spend'] / cat_pnl['conversions']

    # Channel efficiency
    chan_marketing = camp.groupby('channel').agg(
        ad_spend=('spend', 'sum'),
        clicks=('clicks', 'sum'),
        conversions=('conversions', 'sum'),
        avg_cpa=('cpa', 'mean')
    ).reset_index()
    chan_marketing['weighted_cpa'] = chan_marketing['ad_spend'] / chan_marketing['conversions']

    # Campaign CPA tiers
    camp_copy = camp.copy()
    bins = [0, 10, 25, 50, float('inf')]
    labels = ['Ultra-Efficient (<$10)', 'Standard ($10-$25)', 'Caution ($25-$50)', 'Bleeding (>$50)']
    camp_copy['efficiency_tier'] = pd.cut(camp_copy['cpa'], bins=bins, labels=labels)

    tier_summary = camp_copy.groupby('efficiency_tier', observed=False).agg(
        campaign_count=('campaign_id', 'count'),
        total_spend=('spend', 'sum'),
        total_conversions=('conversions', 'sum'),
        avg_cpa=('cpa', 'mean')
    ).reset_index()

    # Bleeding campaigns list
    bleeding_campaigns = camp_copy[camp_copy['cpa'] > 50].sort_values(by='cpa', ascending=False)

    return {
        'category_pnl': cat_pnl.reset_index(),
        'channel_efficiency': chan_marketing,
        'tier_summary': tier_summary,
        'bleeding_campaigns': bleeding_campaigns,
        'total_bleeding_spend': bleeding_campaigns['spend'].sum()
    }

def run_customer_segmentation(data):
    """
    Computes Recency, Frequency, Monetary, and Margin Contribution (RFM-M) score per customer.
    """
    tx = data['transactions']
    cust = data['customers']

    snapshot_date = tx['date'].max()

    completed = tx[tx['status'] == 'Completed']
    rfm = completed.groupby('customer_id').agg(
        recency=('date', lambda d: (snapshot_date - d.max()).days),
        frequency=('transaction_id', 'count'),
        monetary=('net_revenue', 'sum'),
        gross_profit=('gross_profit', 'sum'),
        avg_discount=('discount_pct', 'mean')
    ).reset_index()

    # Add returns count
    returns = tx[tx['status'] == 'Returned'].groupby('customer_id').size().reset_index(name='return_count')
    rfm = rfm.merge(returns, on='customer_id', how='left')
    rfm['return_count'] = rfm['return_count'].fillna(0).astype(int)

    # Merge with original customer table
    rfm = rfm.merge(cust[['customer_id', 'region', 'customer_segment', 'preferred_channel']], on='customer_id', how='left')

    # Quantile scores
    rfm['r_score'] = pd.qcut(rfm['recency'].rank(method='first'), 4, labels=[4, 3, 2, 1])
    rfm['f_score'] = pd.qcut(rfm['frequency'].rank(method='first'), 4, labels=[1, 2, 3, 4])
    rfm['m_score'] = pd.qcut(rfm['monetary'].rank(method='first'), 4, labels=[1, 2, 3, 4])
    rfm['margin_score'] = pd.qcut(rfm['gross_profit'].rank(method='first'), 4, labels=[1, 2, 3, 4])

    # Classify customer value profile
    conditions = [
        (rfm['gross_profit'] < 0),
        (rfm['f_score'].isin([3, 4])) & (rfm['margin_score'].isin([3, 4])),
        (rfm['f_score'].isin([3, 4])) & (rfm['margin_score'].isin([1, 2])),
        (rfm['r_score'].isin([1, 2]))
    ]
    choices = [
        'Margin Drainer (Negative Margin)',
        'Profitable Champion',
        'Discount Seeker / Low Margin',
        'At-Risk / Dormant'
    ]
    rfm['value_tier'] = np.select(conditions, choices, default='General Regular')

    return rfm

def run_anomaly_detection(data):
    """
    Applies Isolation Forest to detect anomalous loss transactions.
    """
    tx = data['transactions'].copy()
    completed = tx[tx['status'] == 'Completed'].copy()

    feature_cols = ['quantity', 'unit_price', 'discount_pct', 'unit_cost', 'net_revenue', 'gross_profit']
    X = completed[feature_cols].copy()

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    iso = IsolationForest(contamination=0.03, random_state=42)
    completed['anomaly_score'] = iso.fit_predict(X_scaled)
    # -1 indicates anomaly
    anomalies = completed[completed['anomaly_score'] == -1].sort_values(by='gross_profit', ascending=True)

    return anomalies
