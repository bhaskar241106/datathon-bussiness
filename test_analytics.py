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

data = load_all_data()
kpis = calculate_executive_kpis(data)
print(f"Total Quantified Leak: ${kpis['total_quantified_leak']:,.2f}")
print(f"Realized Gross Profit: ${kpis['completed_gp']:,.2f}")
print(f"Total Ad Spend: ${kpis['total_ad_spend']:,.2f}")
print(f"Net Business Contribution: ${kpis['net_contribution']:,.2f}")

neg = get_negative_margin_analysis(data)
print(f"Negative Margin Products: {neg['negative_count']} SKUs, Loss: ${neg['total_loss']:,.2f}")

ret = get_return_cancellation_analysis(data)
print(f"High Return SKUs flagged: {len(ret['high_return_skus'])}")

inv = get_inventory_stockout_analysis(data)
print(f"Stockout Incidents: {inv['total_stockout_incidents']}, Est Lost Rev: ${inv['total_estimated_lost_rev']:,.2f}")

mkt = get_marketing_campaign_analysis(data)
print(f"Bleeding Ad Spend: ${mkt['total_bleeding_spend']:,.2f}")

rfm = run_customer_segmentation(data)
print("RFM value tiers:\n", rfm['value_tier'].value_counts())

anom = run_anomaly_detection(data)
print(f"Isolation Forest Anomalies flagged: {len(anom)}")
