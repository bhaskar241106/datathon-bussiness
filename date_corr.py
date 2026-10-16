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

# Check date overlap with inventory
tx_inv = tx.merge(inventory, on=['product_id', 'date'], how='left')
print(f"Transactions matched directly to daily inventory record: {tx_inv['stockout_flag'].notna().sum()} / {len(tx)}")

# In inventory records where stockout_flag == 1, what happens to transactions on that date?
matched_stockout = tx_inv[tx_inv['stockout_flag'] == 1]
print("Transaction statuses when stockout_flag == 1 on that date:")
print(matched_stockout['status'].value_counts(normalize=True))

# Check supplier_lead_days vs cancellation
print("\nCancellation rate by supplier_lead_days bins:")
tx['lead_time_bin'] = pd.qcut(tx['supplier_lead_days'], 4)
print(tx.groupby('lead_time_bin')['status'].value_counts(normalize=True).unstack())

# Check discount_pct vs return / cancel
print("\nDiscount vs status:")
print(tx.groupby('status')['discount_pct'].describe())

# Check quantity vs status
print("\nQuantity vs status:")
print(tx.groupby('status')['quantity'].describe())

# Check unit_price vs status
print("\nUnit Price vs status:")
print(tx.groupby('status')['unit_price'].describe())

# Check customer repeat orders
cust_tx_count = tx.groupby('customer_id').size().value_counts().sort_index()
print("\nOrders per customer distribution:")
print(cust_tx_count.head(10))

# Check if campaigns daily category spend correlates with transactions
daily_tx = tx[tx['status'] == 'Completed'].groupby(['date', 'category']).agg(
    daily_sales=('net_revenue', 'sum'),
    daily_units=('quantity', 'sum'),
    daily_orders=('transaction_id', 'count')
).reset_index()

daily_camp = campaigns.groupby(['date', 'category']).agg(
    daily_spend=('spend', 'sum'),
    daily_clicks=('clicks', 'sum'),
    daily_conv=('conversions', 'sum')
).reset_index()

daily_merged = daily_tx.merge(daily_camp, on=['date', 'category'], how='outer').fillna(0)
print(f"\nDaily category sales vs campaign correlation:")
print(daily_merged[['daily_sales', 'daily_spend', 'daily_clicks', 'daily_conv']].corr())
