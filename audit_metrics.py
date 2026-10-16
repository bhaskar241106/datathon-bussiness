import os
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "04_business_money_leak (2)", "04_business_money_leak")

customers = pd.read_csv(os.path.join(DATA_DIR, "customers.csv"))
products = pd.read_csv(os.path.join(DATA_DIR, "products.csv"))
transactions = pd.read_csv(os.path.join(DATA_DIR, "transactions.csv"))
inventory = pd.read_csv(os.path.join(DATA_DIR, "inventory.csv"))
campaigns = pd.read_csv(os.path.join(DATA_DIR, "campaigns.csv"))

transactions['timestamp'] = pd.to_datetime(transactions['timestamp'])
transactions['date'] = transactions['timestamp'].dt.date
tx = transactions.merge(products, on='product_id', how='left').merge(customers, on='customer_id', how='left')

tx['gross_revenue'] = tx['quantity'] * tx['unit_price']
tx['discount_amount'] = tx['gross_revenue'] * tx['discount_pct']
tx['net_revenue'] = tx['gross_revenue'] - tx['discount_amount']
tx['cogs'] = tx['quantity'] * tx['unit_cost']
tx['gross_profit'] = tx['net_revenue'] - tx['cogs']

print("--- CUSTOMER SEGMENT PROFITABILITY ---")
print(tx[tx['status'] == 'Completed'].groupby('customer_segment').agg(
    orders=('transaction_id', 'count'),
    net_revenue=('net_revenue', 'sum'),
    gross_profit=('gross_profit', 'sum'),
    avg_discount=('discount_pct', 'mean')
))

print("\n--- CHANNEL PROFITABILITY ---")
print(tx[tx['status'] == 'Completed'].groupby('channel').agg(
    orders=('transaction_id', 'count'),
    net_revenue=('net_revenue', 'sum'),
    gross_profit=('gross_profit', 'sum'),
    avg_order_value=('net_revenue', 'mean')
))

print("\n--- REGION PROFITABILITY ---")
print(tx[tx['status'] == 'Completed'].groupby('region').agg(
    orders=('transaction_id', 'count'),
    net_revenue=('net_revenue', 'sum'),
    gross_profit=('gross_profit', 'sum')
))

# Campaign ROAS calculation
# Campaign conversions vs spend
campaigns['cpa'] = campaigns['spend'] / campaigns['conversions'].replace(0, np.nan)
print("\n--- CAMPAIGN EFFICIENCY TIERS ---")
# Let's see CPA distribution
print(campaigns['cpa'].describe(percentiles=[0.1, 0.25, 0.5, 0.75, 0.9, 0.95]))

# Campaigns with CPA > $50
high_cpa = campaigns[campaigns['cpa'] > 50]
print(f"Campaigns with CPA > $50: {len(high_cpa)} / {len(campaigns)}")
print(f"Total spend on CPA > $50 campaigns: ${high_cpa['spend'].sum():,.2f}")
print(f"Total conversions from CPA > $50 campaigns: {high_cpa['conversions'].sum():,}")

# What if we eliminate campaigns with CPA > $50?
print(f"If eliminated, savings = ${high_cpa['spend'].sum():,.2f} for loss of only {high_cpa['conversions'].sum():,} conversions!")

# Inventory stockout: What is daily demand per product?
product_daily_sales = tx[tx['status'] == 'Completed'].groupby(['product_id', 'date'])['quantity'].sum().reset_index()
avg_daily_demand = product_daily_sales.groupby('product_id')['quantity'].mean().reset_index(name='avg_daily_units')

stockout_events = inventory[inventory['stockout_flag'] == 1].merge(avg_daily_demand, on='product_id', how='left').merge(products, on='product_id', how='left')
stockout_events['lost_units'] = stockout_events['avg_daily_units'].fillna(1)
stockout_events['lost_revenue'] = stockout_events['lost_units'] * stockout_events['list_price']
stockout_events['lost_profit'] = stockout_events['lost_units'] * (stockout_events['list_price'] - stockout_events['unit_cost'])
print(f"\n--- ESTIMATED STOCKOUT IMPACT ---")
print(f"Total Stockout Incidents: {len(stockout_events)}")
print(f"Estimated Lost Gross Revenue: ${stockout_events['lost_revenue'].sum():,.2f}")
print(f"Estimated Lost Potential Gross Margin (on positive margin products): ${stockout_events[stockout_events['lost_profit'] > 0]['lost_profit'].sum():,.2f}")
