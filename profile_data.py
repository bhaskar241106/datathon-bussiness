import os
import pandas as pd
import numpy as np

DATA_DIR = r"C:\Users\bhaskar\Desktop\datathon\04_business_money_leak (2)\04_business_money_leak"

print("Loading datasets...")
customers = pd.read_csv(os.path.join(DATA_DIR, "customers.csv"))
products = pd.read_csv(os.path.join(DATA_DIR, "products.csv"))
transactions = pd.read_csv(os.path.join(DATA_DIR, "transactions.csv"))
inventory = pd.read_csv(os.path.join(DATA_DIR, "inventory.csv"))
campaigns = pd.read_csv(os.path.join(DATA_DIR, "campaigns.csv"))

print(f"Customers: {customers.shape}")
print(f"Products: {products.shape}")
print(f"Transactions: {transactions.shape}")
print(f"Inventory: {inventory.shape}")
print(f"Campaigns: {campaigns.shape}")

print("\n--- PRODUCTS SUMMARY ---")
print(products.describe())
negative_margin_products = products[products['unit_cost'] > products['list_price']]
print(f"Products with unit_cost > list_price: {len(negative_margin_products)} / {len(products)} ({len(negative_margin_products)/len(products)*100:.1f}%)")

print("\n--- TRANSACTIONS SUMMARY ---")
print(transactions.describe())
print("\nTransaction status value counts:")
print(transactions['status'].value_counts(dropna=False, normalize=True))
print("\nTransaction channel value counts:")
print(transactions['channel'].value_counts(dropna=False))
print("\nPayment method value counts:")
print(transactions['payment_method'].value_counts(dropna=False))

# Check transaction dates
transactions['timestamp'] = pd.to_datetime(transactions['timestamp'])
print(f"\nTransaction date range: {transactions['timestamp'].min()} to {transactions['timestamp'].max()}")

# Merge transactions with products and customers
tx_full = transactions.merge(products, on='product_id', how='left').merge(customers, on='customer_id', how='left')

# Check unit_price vs list_price
tx_full['price_diff'] = tx_full['unit_price'] - tx_full['list_price']
print(f"\nPrice difference (unit_price in tx vs list_price in products) stats:")
print(tx_full['price_diff'].describe())

# Gross revenue, discount amount, net revenue, cost of goods, gross margin
# Note discount_pct
tx_full['gross_revenue'] = tx_full['quantity'] * tx_full['unit_price']
tx_full['discount_amount'] = tx_full['gross_revenue'] * tx_full['discount_pct']
tx_full['net_revenue'] = tx_full['gross_revenue'] - tx_full['discount_amount']
tx_full['cogs'] = tx_full['quantity'] * tx_full['unit_cost']
tx_full['gross_profit'] = tx_full['net_revenue'] - tx_full['cogs']
tx_full['gross_margin_pct'] = tx_full['gross_profit'] / tx_full['net_revenue']

print("\nProfitability overall (all statuses):")
print(f"Total Gross Revenue: ${tx_full['gross_revenue'].sum():,.2f}")
print(f"Total Discount Given: ${tx_full['discount_amount'].sum():,.2f}")
print(f"Total Net Revenue: ${tx_full['net_revenue'].sum():,.2f}")
print(f"Total COGS: ${tx_full['cogs'].sum():,.2f}")
print(f"Total Gross Profit: ${tx_full['gross_profit'].sum():,.2f}")

print("\nProfitability by Status:")
print(tx_full.groupby('status').agg(
    count=('transaction_id', 'count'),
    net_revenue=('net_revenue', 'sum'),
    gross_profit=('gross_profit', 'sum'),
    discount_sum=('discount_amount', 'sum'),
    avg_discount=('discount_pct', 'mean')
))

print("\n--- INVENTORY SUMMARY ---")
print(inventory.describe())
print(f"Stockout flag counts:\n{inventory['stockout_flag'].value_counts(dropna=False)}")
inventory['date'] = pd.to_datetime(inventory['date'])
print(f"Inventory date range: {inventory['date'].min()} to {inventory['date'].max()}")

print("\n--- CAMPAIGNS SUMMARY ---")
print(campaigns.describe())
campaigns['date'] = pd.to_datetime(campaigns['date'])
print(f"Campaign date range: {campaigns['date'].min()} to {campaigns['date'].max()}")
campaigns['cpc'] = campaigns['spend'] / campaigns['clicks'].replace(0, np.nan)
campaigns['cpa'] = campaigns['spend'] / campaigns['conversions'].replace(0, np.nan)
campaigns['ctr'] = campaigns['clicks'] / campaigns['impressions'].replace(0, np.nan)
campaigns['cvr'] = campaigns['conversions'] / campaigns['clicks'].replace(0, np.nan)
print(f"Total Ad Spend: ${campaigns['spend'].sum():,.2f}")
print(f"Spend by Channel:\n{campaigns.groupby('channel')['spend'].sum()}")
print(f"Spend by Category:\n{campaigns.groupby('category')['spend'].sum()}")

print("\nAnalysis complete.")
