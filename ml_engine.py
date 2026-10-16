import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.preprocessing import OneHotEncoder
from scipy.stats import norm
import joblib
import os

class MoneyLeakMLEngine:
    def __init__(self, data):
        self.data = data
        self.model = None
        self.feature_names = None
        self.feature_importances = None
        self.iso_forest = None
        self.encoder = None
        self.categories = sorted(data['products']['category'].unique().tolist())
        self.channels = sorted(data['transactions']['channel'].unique().tolist())
        self.payment_methods = sorted(data['transactions']['payment_method'].unique().tolist())
        self.regions = sorted(data['customers']['region'].unique().tolist())
        self.train_models()

    def train_models(self):
        print("Training ML models on 18,000 transactions...")
        tx = self.data['transactions'].copy()
        
        # Problematic target: Cancelled or Returned
        tx['target'] = tx['status'].isin(['Cancelled', 'Returned']).astype(int)

        feature_cols = [
            'quantity', 'unit_price', 'discount_pct', 'supplier_lead_days',
            'category', 'channel', 'payment_method', 'region'
        ]

        # One hot encode categoricals
        cat_cols = ['category', 'channel', 'payment_method', 'region']
        num_cols = ['quantity', 'unit_price', 'discount_pct', 'supplier_lead_days']

        X_cat = pd.get_dummies(tx[cat_cols], drop_first=False)
        X = pd.concat([tx[num_cols], X_cat], axis=1)
        y = tx['target']

        self.feature_names = list(X.columns)

        # Train Random Forest Classifier with balanced class weights
        self.model = RandomForestClassifier(
            n_estimators=120,
            max_depth=7,
            class_weight='balanced',
            random_state=42,
            n_jobs=-1
        )
        self.model.fit(X, y)

        # Extract feature importances
        importances = pd.Series(self.model.feature_importances_, index=self.feature_names).sort_values(ascending=False)
        self.feature_importances = [
            {"feature": feat, "importance": round(float(val) * 100, 2)}
            for feat, val in importances.head(10).items()
        ]

        # Train Isolation Forest on completed order unit margins
        completed = tx[tx['status'] == 'Completed'].copy()
        iso_features = ['quantity', 'unit_price', 'discount_pct', 'unit_cost', 'gross_profit']
        self.iso_forest = IsolationForest(contamination=0.03, random_state=42)
        completed['anomaly_score'] = self.iso_forest.fit_predict(completed[iso_features])
        self.anomalies_df = completed[completed['anomaly_score'] == -1].sort_values(by='gross_profit', ascending=True)

        print("ML Models trained successfully!")

    def predict_order_risk(self, order_dict):
        """
        Live inference: predicts cancellation or return risk for an order.
        order_dict: {
            quantity: int,
            unit_price: float,
            discount_pct: float,
            supplier_lead_days: int,
            category: str,
            channel: str,
            payment_method: str,
            region: str
        }
        """
        row = {feat: 0 for feat in self.feature_names}

        # Numeric values
        row['quantity'] = order_dict.get('quantity', 2)
        row['unit_price'] = order_dict.get('unit_price', 150.0)
        row['discount_pct'] = order_dict.get('discount_pct', 0.10)
        row['supplier_lead_days'] = order_dict.get('supplier_lead_days', 14)

        # One hot encoded flags
        cat_key = f"category_{order_dict.get('category', 'Electronics')}"
        chan_key = f"channel_{order_dict.get('channel', 'Web')}"
        pay_key = f"payment_method_{order_dict.get('payment_method', 'Card')}"
        reg_key = f"region_{order_dict.get('region', 'West')}"

        if cat_key in row: row[cat_key] = 1
        if chan_key in row: row[chan_key] = 1
        if pay_key in row: row[pay_key] = 1
        if reg_key in row: row[reg_key] = 1

        df_input = pd.DataFrame([row])
        prob = float(self.model.predict_proba(df_input)[0][1])

        # Risk classification
        if prob >= 0.65:
            risk_level = "CRITICAL RISK"
            risk_color = "rose"
            intervention = "Flag order for phone/SMS confirmation before dispatch. Require signature on delivery."
        elif prob >= 0.50:
            risk_level = "HIGH RISK"
            risk_color = "orange"
            intervention = "Send automated sizing/compatibility check email. Verify shipping address."
        elif prob >= 0.35:
            risk_level = "MEDIUM RISK"
            risk_color = "yellow"
            intervention = "Standard automated processing with post-purchase setup instructions."
        else:
            risk_level = "LOW RISK"
            risk_color = "emerald"
            intervention = "Fast-track fulfillment. Low probability of friction."

        # Risk drivers explanation
        drivers = []
        if order_dict.get('discount_pct', 0) >= 0.20:
            drivers.append("High discount (>=20%) attracts promo churners")
        if order_dict.get('supplier_lead_days', 0) > 18:
            drivers.append("Extended delivery lead time (>18 days) increases cancellation impulse")
        if order_dict.get('channel') == 'Web' and order_dict.get('payment_method') == 'Card':
            drivers.append("Web + Card checkout cohort shows higher chargeback/cancellation propensity")
        if order_dict.get('unit_price', 0) > 280:
            drivers.append("High ticket value increases buyer remorse risk")
        if not drivers:
            drivers.append("Standard balanced operational signals")

        return {
            "risk_probability": round(prob * 100, 1),
            "risk_level": risk_level,
            "risk_color": risk_color,
            "prescribed_intervention": intervention,
            "risk_drivers": drivers
        }

    def get_stockout_probabilities(self):
        """
        Computes probabilistic stockout risk for each SKU using lead-time demand modeling:
        P(Stockout) = 1 - CDF(Stock on Hand; mean_L, std_L)
        """
        inv = self.data['inventory'].copy()
        tx = self.data['transactions'].copy()
        prod = self.data['products'].copy()

        # Daily sales stats per SKU
        completed = tx[tx['status'] == 'Completed']
        daily = completed.groupby(['product_id', 'date'])['quantity'].sum().reset_index()
        stats = daily.groupby('product_id').agg(
            mean_d=('quantity', 'mean'),
            std_d=('quantity', 'std')
        ).reset_index()
        stats['std_d'] = stats['std_d'].fillna(stats['mean_d'] * 0.35)

        # Inventory snapshot (latest per product)
        inv_latest = inv.sort_values(by='date').groupby('product_id').last().reset_index()
        inv_merged = inv_latest.merge(stats, on='product_id', how='left').merge(prod, on='product_id', how='left')

        inv_merged['mean_d'] = inv_merged['mean_d'].fillna(1.0)
        inv_merged['std_d'] = inv_merged['std_d'].fillna(0.4)

        effective_L = inv_merged['supplier_lead_days'] + inv_merged['supplier_delay_days']
        inv_merged['lead_time_mean_demand'] = inv_merged['mean_d'] * effective_L
        inv_merged['lead_time_std_demand'] = inv_merged['std_d'] * np.sqrt(effective_L)

        # Probability that demand exceeds current stock on hand
        z_scores = (inv_merged['stock_on_hand'] - inv_merged['lead_time_mean_demand']) / inv_merged['lead_time_std_demand'].replace(0, 1)
        # 1 - norm.cdf(z)
        inv_merged['stockout_probability_pct'] = ((1 - norm.cdf(z_scores)) * 100).round(1)

        high_risk_stockouts = inv_merged.sort_values(by='stockout_probability_pct', ascending=False).head(20)

        results = []
        for _, r in high_risk_stockouts.iterrows():
            results.append({
                "product_id": r['product_id'],
                "category": r['category'],
                "stock_on_hand": int(r['stock_on_hand']),
                "lead_time_days": int(effective_L.loc[_]),
                "expected_demand": round(float(r['lead_time_mean_demand']), 1),
                "stockout_probability": float(r['stockout_probability_pct']),
                "list_price": round(float(r['list_price']), 2)
            })

        return results

    def get_top_anomalies(self):
        """
        Returns top 15 Isolation Forest order anomalies with human-readable explanations.
        """
        anom_list = []
        for _, row in self.anomalies_df.head(15).iterrows():
            anom_list.append({
                "transaction_id": row['transaction_id'],
                "product_id": row['product_id'],
                "category": row['category'],
                "quantity": int(row['quantity']),
                "unit_price": round(float(row['unit_price']), 2),
                "discount_pct": round(float(row['discount_pct']) * 100, 1),
                "unit_cost": round(float(row['unit_cost']), 2),
                "net_revenue": round(float(row['net_revenue']), 2),
                "gross_profit": round(float(row['gross_profit']), 2),
                "reason": f"Bought for ${row['unit_cost']:.2f}, sold for ${row['unit_price']*(1-row['discount_pct']):.2f} after {int(row['discount_pct']*100)}% discount!"
            })
        return anom_list
