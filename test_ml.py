import os
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.preprocessing import OneHotEncoder

DATA_DIR = r"C:\Users\bhaskar\Desktop\datathon\04_business_money_leak (2)\04_business_money_leak"

customers = pd.read_csv(os.path.join(DATA_DIR, "customers.csv"))
products = pd.read_csv(os.path.join(DATA_DIR, "products.csv"))
transactions = pd.read_csv(os.path.join(DATA_DIR, "transactions.csv"))

tx = transactions.merge(products, on='product_id', how='left').merge(customers, on='customer_id', how='left')

# Create binary targets: is_returned, is_cancelled, is_problematic (cancelled or returned)
tx['is_problematic'] = tx['status'].isin(['Cancelled', 'Returned']).astype(int)
tx['is_returned'] = (tx['status'] == 'Returned').astype(int)
tx['is_cancelled'] = (tx['status'] == 'Cancelled').astype(int)

# Feature engineering
tx['unit_margin'] = tx['unit_price'] - tx['unit_cost']
tx['is_upside_down'] = (tx['unit_cost'] > tx['list_price']).astype(int)
tx['price_discount_amount'] = tx['unit_price'] * tx['discount_pct']
tx['effective_price'] = tx['unit_price'] * (1 - tx['discount_pct'])
tx['lead_time'] = tx['supplier_lead_days']

features = [
    'quantity', 'unit_price', 'discount_pct', 'unit_cost', 'unit_margin',
    'is_upside_down', 'effective_price', 'supplier_lead_days',
    'category', 'channel', 'payment_method', 'region', 'customer_segment'
]

X = pd.get_dummies(tx[features], drop_first=True)
y = tx['is_problematic']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

rf = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42, n_jobs=-1)
rf.fit(X_train, y_train)

preds = rf.predict(X_test)
probs = rf.predict_proba(X_test)[:, 1]

print("Model Evaluation (Problematic Orders: Cancelled or Returned):")
print(classification_report(y_test, preds, zero_division=0))
print(f"ROC-AUC: {roc_auc_score(y_test, probs):.4f}")

# Feature importances
importances = pd.Series(rf.feature_importances_, index=X.columns).sort_values(ascending=False)
print("\nTop 10 Feature Importances:")
print(importances.head(10))
