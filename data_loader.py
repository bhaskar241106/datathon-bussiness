import os
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "04_business_money_leak (2)", "04_business_money_leak")

def load_all_data(data_dir=DATA_DIR):
    """
    Loads and preprocesses all 5 datasets:
    customers, products, transactions, inventory, campaigns.
    """
    customers = pd.read_csv(os.path.join(data_dir, "customers.csv"))
    products = pd.read_csv(os.path.join(data_dir, "products.csv"))
    transactions = pd.read_csv(os.path.join(data_dir, "transactions.csv"))
    inventory = pd.read_csv(os.path.join(data_dir, "inventory.csv"))
    campaigns = pd.read_csv(os.path.join(data_dir, "campaigns.csv"))

    # Convert dates
    customers['signup_date'] = pd.to_datetime(customers['signup_date'])
    transactions['timestamp'] = pd.to_datetime(transactions['timestamp'])
    transactions['date'] = pd.to_datetime(transactions['timestamp'].dt.date)
    inventory['date'] = pd.to_datetime(inventory['date'])
    campaigns['date'] = pd.to_datetime(campaigns['date'])

    # Products enrichment
    products['base_unit_margin'] = products['list_price'] - products['unit_cost']
    products['base_margin_pct'] = products['base_unit_margin'] / products['list_price']
    products['is_negative_margin'] = products['base_unit_margin'] < 0

    # Transactions enrichment
    tx = transactions.merge(products, on='product_id', how='left')
    tx = tx.merge(customers, on='customer_id', how='left')

    tx['gross_revenue'] = tx['quantity'] * tx['unit_price']
    tx['discount_amount'] = tx['gross_revenue'] * tx['discount_pct']
    tx['net_revenue'] = tx['gross_revenue'] - tx['discount_amount']
    tx['cogs'] = tx['quantity'] * tx['unit_cost']
    tx['gross_profit'] = tx['net_revenue'] - tx['cogs']
    tx['gross_margin_pct'] = np.where(tx['net_revenue'] > 0, tx['gross_profit'] / tx['net_revenue'], 0)
    tx['is_loss_making'] = tx['gross_profit'] < 0
    tx['effective_unit_price'] = tx['unit_price'] * (1 - tx['discount_pct'])
    tx['unit_profit'] = tx['effective_unit_price'] - tx['unit_cost']

    # Reverse logistics estimated cost (shipping + handling for returned items, e.g. $12/order)
    tx['return_handling_cost'] = np.where(tx['status'] == 'Returned', 12.0 * tx['quantity'], 0.0)

    # Campaigns enrichment
    campaigns['cpc'] = campaigns['spend'] / campaigns['clicks'].replace(0, np.nan)
    campaigns['cpa'] = campaigns['spend'] / campaigns['conversions'].replace(0, np.nan)
    campaigns['ctr'] = (campaigns['clicks'] / campaigns['impressions'].replace(0, np.nan)) * 100
    campaigns['cvr'] = (campaigns['conversions'] / campaigns['clicks'].replace(0, np.nan)) * 100

    return {
        'customers': customers,
        'products': products,
        'transactions': tx,
        'inventory': inventory,
        'campaigns': campaigns
    }

if __name__ == '__main__':
    data = load_all_data()
    print("Data loaded successfully!")
    print(f"Transactions enriched: {data['transactions'].shape}")
    print(f"Products enriched: {data['products'].shape}")
