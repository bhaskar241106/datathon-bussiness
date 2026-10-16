import os
import pandas as pd
import numpy as np

DATA_DIR = r"C:\Users\bhaskar\Desktop\datathon\04_business_money_leak (2)\04_business_money_leak"

customers = pd.read_csv(os.path.join(DATA_DIR, "customers.csv"))
products = pd.read_csv(os.path.join(DATA_DIR, "products.csv"))
transactions = pd.read_csv(os.path.join(DATA_DIR, "transactions.csv"))
inventory = pd.read_csv(os.path.join(DATA_DIR, "inventory.csv"))
campaigns = pd.read_csv(os.path.join(DATA_DIR, "campaigns.csv"))

transactions['timestamp'] = pd.to_datetime(transactions['timestamp'])
transactions['date'] = transactions['timestamp'].dt.date
inventory['date'] = pd.to_datetime(inventory['date']).dt.date
campaigns['date'] = pd.to_datetime(campaigns['date']).dt.date

tx = transactions.merge(products, on='product_id', how='left').merge(customers, on='customer_id', how='left')
tx['gross_revenue'] = tx['quantity'] * tx['unit_price']
tx['discount_amount'] = tx['gross_revenue'] * tx['discount_pct']
tx['net_revenue'] = tx['gross_revenue'] - tx['discount_amount']
tx['cogs'] = tx['quantity'] * tx['unit_cost']
tx['gross_profit'] = tx['net_revenue'] - tx['cogs']

print("=== 1. CANCELLATION & RETURN DRIVERS ===")
print("Return Rate by Category:")
cat_status = tx.groupby('category')['status'].value_counts(normalize=True).unstack().fillna(0)
print(cat_status)

print("\nReturn Rate by Channel:")
chan_status = tx.groupby('channel')['status'].value_counts(normalize=True).unstack().fillna(0)
print(chan_status)

print("\nReturn Rate by Region:")
reg_status = tx.groupby('region')['status'].value_counts(normalize=True).unstack().fillna(0)
print(reg_status)

print("\nReturn Rate by Customer Segment:")
seg_status = tx.groupby('customer_segment')['status'].value_counts(normalize=True).unstack().fillna(0)
print(seg_status)

print("\nReturn Rate by Payment Method:")
pay_status = tx.groupby('payment_method')['status'].value_counts(normalize=True).unstack().fillna(0)
print(pay_status)

print("\nTop 10 High Return Products:")
prod_ret = tx[tx['status'] == 'Returned'].groupby(['product_id', 'category']).size().reset_index(name='returned_count')
prod_total = tx.groupby('product_id').size().reset_index(name='total_count')
prod_ret_merged = prod_ret.merge(prod_total, on='product_id')
prod_ret_merged['return_rate'] = prod_ret_merged['returned_count'] / prod_ret_merged['total_count']
print(prod_ret_merged.sort_values(by='returned_count', ascending=False).head(10))

print("\n=== 2. NEGATIVE MARGIN & DISCOUNT LEAKAGE ===")
print("Gross Profit distribution on Completed Orders:")
completed_tx = tx[tx['status'] == 'Completed']
neg_profit_tx = completed_tx[completed_tx['gross_profit'] < 0]
print(f"Completed orders selling at a loss: {len(neg_profit_tx)} / {len(completed_tx)} ({len(neg_profit_tx)/len(completed_tx)*100:.1f}%)")
print(f"Total loss from negative profit completed orders: ${neg_profit_tx['gross_profit'].sum():,.2f}")

print("\nLoss by Category (Completed orders):")
print(completed_tx.groupby('category').agg(
    total_net_rev=('net_revenue', 'sum'),
    total_cogs=('cogs', 'sum'),
    total_gp=('gross_profit', 'sum'),
    neg_gp_orders=('gross_profit', lambda x: (x < 0).sum())
))

print("\nTop 10 Most Loss-Making Products in Completed Sales:")
prod_loss = completed_tx.groupby(['product_id', 'category']).agg(
    orders=('transaction_id', 'count'),
    net_rev=('net_revenue', 'sum'),
    cogs=('cogs', 'sum'),
    gross_profit=('gross_profit', 'sum'),
    avg_unit_cost=('unit_cost', 'mean'),
    avg_unit_price=('unit_price', 'mean'),
    avg_discount=('discount_pct', 'mean')
).sort_values(by='gross_profit', ascending=True).head(10)
print(prod_loss)

print("\n=== 3. INVENTORY STOCKOUT IMPACT & DELAYS ===")
print(f"Unique products in inventory: {inventory['product_id'].nunique()} / {products['product_id'].nunique()}")
stockout_by_prod = inventory.groupby('product_id').agg(
    total_days=('date', 'count'),
    stockout_days=('stockout_flag', 'sum'),
    avg_delay=('supplier_delay_days', 'mean')
).reset_index()
stockout_by_prod['stockout_rate'] = stockout_by_prod['stockout_days'] / stockout_by_prod['total_days']
print("Top 10 Products with highest stockout rate:")
print(stockout_by_prod.sort_values(by='stockout_days', ascending=False).head(10))

# Check overlap of stockouts with high demand products
top_selling_prods = completed_tx.groupby('product_id')['quantity'].sum().reset_index(name='units_sold')
stockout_demand = stockout_by_prod.merge(top_selling_prods, on='product_id').merge(products[['product_id', 'category', 'list_price']], on='product_id')
print("\nHigh selling products suffering stockouts:")
print(stockout_demand[stockout_demand['stockout_days'] > 5].sort_values(by='units_sold', ascending=False).head(10))

print("\n=== 4. CAMPAIGN EFFICIENCY & AD SPEND BLEED ===")
campaigns['cpa'] = campaigns['spend'] / campaigns['conversions'].replace(0, np.nan)
campaigns['cpc'] = campaigns['spend'] / campaigns['clicks'].replace(0, np.nan)
print("Campaign stats by Category:")
print(campaigns.groupby('category').agg(
    total_spend=('spend', 'sum'),
    total_clicks=('clicks', 'sum'),
    total_conv=('conversions', 'sum'),
    avg_cpa=('cpa', 'mean'),
    avg_cpc=('cpc', 'mean')
))

print("\nCampaign stats by Channel:")
print(campaigns.groupby('channel').agg(
    total_spend=('spend', 'sum'),
    total_clicks=('clicks', 'sum'),
    total_conv=('conversions', 'sum'),
    avg_cpa=('cpa', 'mean'),
    avg_cpc=('cpc', 'mean')
))

# Compare campaign category spend vs completed sales gross profit
cat_gp = completed_tx.groupby('category')['gross_profit'].sum()
cat_spend = campaigns.groupby('category')['spend'].sum()
cat_pnl = pd.DataFrame({'Gross_Profit': cat_gp, 'Ad_Spend': cat_spend})
cat_pnl['Net_Contribution'] = cat_pnl['Gross_Profit'] - cat_pnl['Ad_Spend']
print("\nCategory Level P&L (Gross Profit - Ad Spend):")
print(cat_pnl)

# Check worst campaigns (highest spend, lowest conversion)
print("\nWorst 10 Campaigns by CPA (spend > $1000):")
print(campaigns[campaigns['spend'] > 1000].sort_values(by='cpa', ascending=False)[['campaign_id', 'date', 'channel', 'category', 'spend', 'conversions', 'cpa']].head(10))
