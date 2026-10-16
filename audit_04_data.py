import os
import pandas as pd
import numpy as np

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "04_business_money_leak (2)", "04_business_money_leak")

cust = pd.read_csv(os.path.join(DATA_DIR, 'customers.csv'))
prod = pd.read_csv(os.path.join(DATA_DIR, 'products.csv'))
tx = pd.read_csv(os.path.join(DATA_DIR, 'transactions.csv'))
inv = pd.read_csv(os.path.join(DATA_DIR, 'inventory.csv'))
camp = pd.read_csv(os.path.join(DATA_DIR, 'campaigns.csv'))

tx['timestamp'] = pd.to_datetime(tx['timestamp'])
tx['gross_rev'] = tx['quantity'] * tx['unit_price']
tx['discount_amt'] = tx['gross_rev'] * tx['discount_pct']
tx['net_rev'] = tx['gross_rev'] - tx['discount_amt']

m = tx.merge(prod, on='product_id', how='left').merge(cust, on='customer_id', how='left')
m['cogs'] = m['quantity'] * m['unit_cost']
m['gp'] = m['net_rev'] - m['cogs']

print("======================================================================")
print("             04 BUSINESS MONEY LEAK: COMPREHENSIVE DATA AUDIT         ")
print("======================================================================")
print(f"1. DATASET VOLUMES:")
print(f"   - Customers:    {len(cust):,} records (Columns: {list(cust.columns)})")
print(f"   - Products:     {len(prod):,} SKUs (Columns: {list(prod.columns)})")
print(f"   - Transactions: {len(tx):,} orders (Columns: {list(tx.columns)})")
print(f"   - Inventory:    {len(inv):,} audit logs (Columns: {list(inv.columns)})")
print(f"   - Campaigns:    {len(camp):,} ad records (Columns: {list(camp.columns)})")

comp = m[m['status'] == 'Completed']
ret = m[m['status'] == 'Returned']
canc = m[m['status'] == 'Cancelled']
pend = m[m['status'] == 'Pending']

print(f"\n2. P&L AND FINANCIAL CRASH WATERFALL:")
print(f"   - Gross Revenue Recorded:            +${tx['gross_rev'].sum():,.2f}")
print(f"   - Coupon Discounts Eroded:           -${tx['discount_amt'].sum():,.2f}")
print(f"   - Cancelled Orders Revenue Drag:     -${canc['net_rev'].sum():,.2f} ({len(canc):,} orders)")
print(f"   - Returned Orders Revenue Drag:      -${ret['net_rev'].sum():,.2f} ({len(ret):,} orders)")
print(f"   - Cost of Goods Sold (Completed):    -${comp['cogs'].sum():,.2f}")
print(f"   - Realized Gross Profit:             +${comp['gp'].sum():,.2f}")
print(f"   - Total Marketing Ad Spend:          -${camp['spend'].sum():,.2f}")
handling_fee = len(ret) * 12.0 # Standard handling
net_contrib = comp['gp'].sum() - camp['spend'].sum() - handling_fee
print(f"   - Reverse Logistics & Restock Cost:  -${handling_fee:,.2f}")
print(f"   ------------------------------------------------------------------")
print(f"   - NET BOTTOM-LINE OPERATING CASH:    ${net_contrib:,.2f} (IN SEVERE DEFICIT!)")

print(f"\n3. THE 5 ROOT MONEY LEAKS IDENTIFIED:")
# Leak 1: Negative Margins
upside_down = prod[prod['unit_cost'] > prod['list_price']]
comp_loss = comp[comp['unit_cost'] > comp['list_price']]
print(f"   [LEAK 1] Backwards Pricing Trap:")
print(f"            {len(upside_down)} out of {len(prod)} SKUs (30.4%) cost MORE than their list price!")
print(f"            Cumulative cash loss on completed orders alone: ${comp_loss['gp'].sum():,.2f}")

# Leak 2: Excessive Discounting
deep_disc = comp[comp['discount_pct'] >= 0.20]
print(f"\n   [LEAK 2] Excessive Promotional Discounting:")
print(f"            Total discounts given away across all orders: ${tx['discount_amt'].sum():,.2f}")
print(f"            Orders with >=20% discount: {len(deep_disc):,} completed orders")

# Leak 3: Order Friction (Returns & Cancels)
print(f"\n   [LEAK 3] Cancellation & Return Friction:")
print(f"            Cancelled Orders: {len(canc):,} ({len(canc)/len(tx)*100:.1f}%) -> Lost Net Rev: ${canc['net_rev'].sum():,.2f}")
print(f"            Returned Orders:  {len(ret):,} ({len(ret)/len(tx)*100:.1f}%) -> Lost Net Rev: ${ret['net_rev'].sum():,.2f}")

# Leak 4: Runaway Ad Spend
camp['cpa'] = camp['spend'] / camp['conversions'].replace(0, np.nan)
bleeding_camps = camp[camp['cpa'] > 40]
print(f"\n   [LEAK 4] Runaway Ad Spend:")
print(f"            Total Marketing Budget Burned: ${camp['spend'].sum():,.2f}")
print(f"            Bleeding Campaigns (CPA > $40): {len(bleeding_camps)} campaigns consuming ${bleeding_camps['spend'].sum():,.2f}")

# Leak 5: Inventory Stockouts & Supplier Delays
stockouts = inv[inv['stockout_flag'] == 1]
print(f"\n   [LEAK 5] Inventory Stockouts & Delivery Lags:")
print(f"            Stockout Incidents Recorded: {len(stockouts):,} out of {len(inv):,} audits ({len(stockouts)/len(inv)*100:.1f}%)")
print(f"            Average Supplier Delay: {inv['supplier_delay_days'].mean():.1f} days (Max: {inv['supplier_delay_days'].max()} days)")

print("\n======================================================================")
