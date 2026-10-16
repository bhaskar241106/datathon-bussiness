import os
import json
import numpy as np
import pandas as pd
from data_loader import load_all_data
from analytics_engine import (
    calculate_executive_kpis,
    get_negative_margin_analysis,
    get_return_cancellation_analysis,
    get_inventory_stockout_analysis,
    get_marketing_campaign_analysis,
    run_customer_segmentation
)
from decision_playbook import get_action_playbook_cards, simulate_interventions
from ml_engine import MoneyLeakMLEngine

def main():
    print("Loading datasets...")
    DATA = load_all_data()
    KPIS = calculate_executive_kpis(DATA)
    MARGIN_AUDIT = get_negative_margin_analysis(DATA)
    RETURN_AUDIT = get_return_cancellation_analysis(DATA)
    INV_AUDIT = get_inventory_stockout_analysis(DATA)
    MKT_AUDIT = get_marketing_campaign_analysis(DATA)
    RFM_AUDIT = run_customer_segmentation(DATA)
    ML_ENGINE = MoneyLeakMLEngine(DATA)

    os.makedirs('api', exist_ok=True)
    os.makedirs('api/ml', exist_ok=True)
    os.makedirs('api/sku-dossier', exist_ok=True)

    # 1. Overview
    overview_data = {
        "kpis": {
            "total_gross_rev": float(KPIS['total_gross_rev']),
            "total_discounts": float(KPIS['total_discounts']),
            "total_net_rev": float(KPIS['total_net_rev']),
            "completed_net_rev": float(KPIS['completed_net_rev']),
            "completed_cogs": float(KPIS['completed_cogs']),
            "completed_gp": float(KPIS['completed_gp']),
            "completed_margin_pct": round(float(KPIS['completed_margin_pct']), 1),
            "total_ad_spend": float(KPIS['total_ad_spend']),
            "total_return_handling": float(KPIS['total_return_handling']),
            "net_contribution": float(KPIS['net_contribution']),
            "negative_margin_loss": float(KPIS['negative_margin_loss']),
            "negative_margin_order_count": int(KPIS['negative_margin_order_count']),
            "cancelled_rev": float(KPIS['cancelled_rev']),
            "returned_rev": float(KPIS['returned_rev']),
            "friction_lost_rev": float(KPIS['friction_lost_rev']),
            "inefficient_ad_spend": float(KPIS['inefficient_ad_spend']),
            "estimated_stockout_lost_rev": float(KPIS['estimated_stockout_lost_rev']),
            "estimated_stockout_lost_gp": float(KPIS['estimated_stockout_lost_gp']),
            "total_quantified_leak": float(KPIS['total_quantified_leak'])
        },
        "waterfall": [
            {"step": "Gross Revenue", "amount": float(KPIS['total_gross_rev']), "type": "positive"},
            {"step": "Promotional Discounts", "amount": -float(KPIS['total_discounts']), "type": "negative"},
            {"step": "Cancelled Orders", "amount": -float(KPIS['cancelled_rev']), "type": "negative"},
            {"step": "Returned Orders", "amount": -float(KPIS['returned_rev']), "type": "negative"},
            {"step": "Standard Product COGS", "amount": -float(KPIS['completed_cogs'] - KPIS['negative_margin_loss']), "type": "negative"},
            {"step": "Upside-Down Pricing Loss", "amount": -float(KPIS['negative_margin_loss']), "type": "negative"},
            {"step": "Marketing Ad Spend", "amount": -float(KPIS['total_ad_spend']), "type": "negative"},
            {"step": "Net Operating Deficit", "amount": float(KPIS['net_contribution']), "type": "total"}
        ]
    }
    with open('api/overview.json', 'w') as f:
        json.dump(overview_data, f, indent=2)

    # 2. Margins
    all_prods = MARGIN_AUDIT['all_products'].copy()
    neg_prods = MARGIN_AUDIT['negative_margin_products'].copy()
    scatter = []
    for _, row in all_prods.iterrows():
        scatter.append({
            "product_id": row['product_id'],
            "category": row['category'],
            "unit_cost": round(float(row['unit_cost']), 2),
            "list_price": round(float(row['list_price']), 2),
            "is_negative": bool(row['is_negative_margin']),
            "gross_profit": round(float(row['gross_profit']), 2),
            "orders": int(row['orders'])
        })
    table_data = []
    for _, row in neg_prods.head(25).iterrows():
        table_data.append({
            "product_id": row['product_id'],
            "category": row['category'],
            "unit_cost": round(float(row['unit_cost']), 2),
            "list_price": round(float(row['list_price']), 2),
            "orders": int(row['orders']),
            "units_sold": int(row['units_sold']),
            "net_revenue": round(float(row['net_revenue']), 2),
            "cogs": round(float(row['cogs']), 2),
            "gross_profit": round(float(row['gross_profit']), 2),
            "recommended_list_price": round(float(row['recommended_list_price']), 2),
            "price_hike": round(float(row['recommended_price_hike']), 2)
        })
    margins_data = {
        "total_skus": len(all_prods),
        "negative_margin_count": int(MARGIN_AUDIT['negative_count']),
        "negative_margin_loss": round(float(MARGIN_AUDIT['total_loss']), 2),
        "scatter": scatter,
        "loss_table": table_data
    }
    with open('api/margins.json', 'w') as f:
        json.dump(margins_data, f, indent=2)

    # 3. Returns
    by_cat = RETURN_AUDIT['by_category'].to_dict(orient="records")
    by_chan = RETURN_AUDIT['by_channel'].to_dict(orient="records")
    by_pay = RETURN_AUDIT['by_payment'].to_dict(orient="records")
    high_skus = []
    for _, row in RETURN_AUDIT['high_return_skus'].iterrows():
        high_skus.append({
            "product_id": row['product_id'],
            "category": row['category'],
            "total_orders": int(row['total_orders']),
            "returned_orders": int(row['returned_orders']),
            "return_rate": round(float(row['return_rate']), 2),
            "return_zscore": round(float(row['return_zscore']), 2),
            "returned_value": round(float(row['returned_value']), 2)
        })
    returns_data = {
        "cancelled_count": 1689,
        "cancelled_rev": round(float(KPIS['cancelled_rev']), 2),
        "returned_count": 1431,
        "returned_rev": round(float(KPIS['returned_rev']), 2),
        "reverse_logistics_cost": round(float(KPIS['total_return_handling']), 2),
        "by_category": by_cat,
        "by_channel": by_chan,
        "by_payment": by_pay,
        "high_return_skus": high_skus
    }
    with open('api/returns.json', 'w') as f:
        json.dump(returns_data, f, indent=2)

    # 4. Inventory
    inv_summary = INV_AUDIT['inventory_summary']
    top_stockouts = []
    for _, row in INV_AUDIT['top_stockout_products'].iterrows():
        top_stockouts.append({
            "product_id": row['product_id'],
            "category": row['category'],
            "stockout_days": int(row['stockout_days']),
            "stockout_pct": round(float(row['stockout_pct']), 1),
            "avg_stock": round(float(row['avg_stock_on_hand']), 0),
            "threshold": round(float(row['avg_reorder_threshold']), 0),
            "recommended_rop": round(float(row['recommended_rop']), 0),
            "rop_deficit": round(float(row['rop_deficit']), 0),
            "lost_revenue": round(float(row['estimated_lost_revenue']), 2),
            "lost_margin": round(float(row['estimated_lost_margin']), 2)
        })
    cat_loss = inv_summary.groupby('category').agg(
        stockouts=('stockout_days', 'sum'),
        lost_rev=('estimated_lost_revenue', 'sum'),
        lost_margin=('estimated_lost_margin', 'sum')
    ).reset_index().to_dict(orient="records")
    inventory_data = {
        "stockout_incidents": int(INV_AUDIT['total_stockout_incidents']),
        "lost_revenue": round(float(INV_AUDIT['total_estimated_lost_rev']), 2),
        "lost_margin": round(float(INV_AUDIT['total_estimated_lost_margin']), 2),
        "top_stockouts": top_stockouts,
        "category_loss": cat_loss
    }
    with open('api/inventory.json', 'w') as f:
        json.dump(inventory_data, f, indent=2)

    # 5. Marketing
    cat_pnl = MKT_AUDIT['category_pnl'].to_dict(orient="records")
    tiers = MKT_AUDIT['tier_summary'].to_dict(orient="records")
    bleeding = []
    for _, row in MKT_AUDIT['bleeding_campaigns'].head(20).iterrows():
        bleeding.append({
            "campaign_id": row['campaign_id'],
            "date": str(row['date'].strftime('%Y-%m-%d')),
            "channel": row['channel'],
            "category": row['category'],
            "spend": round(float(row['spend']), 2),
            "clicks": int(row['clicks']),
            "conversions": int(row['conversions']),
            "cpa": round(float(row['cpa']), 2)
        })
    marketing_data = {
        "total_spend": round(float(KPIS['total_ad_spend']), 2),
        "bleeding_spend": round(float(MKT_AUDIT['total_bleeding_spend']), 2),
        "category_pnl": cat_pnl,
        "tier_summary": tiers,
        "bleeding_campaigns": bleeding
    }
    with open('api/marketing.json', 'w') as f:
        json.dump(marketing_data, f, indent=2)

    # 6. Customers
    counts = RFM_AUDIT['value_tier'].value_counts().to_dict()
    profit_by_tier = RFM_AUDIT.groupby('value_tier')['gross_profit'].sum().round(2).to_dict()
    customers_data = {
        "tier_counts": counts,
        "profit_by_tier": profit_by_tier,
        "total_customers": len(RFM_AUDIT)
    }
    with open('api/customers.json', 'w') as f:
        json.dump(customers_data, f, indent=2)

    # 7. Action cards
    cards = get_action_playbook_cards()
    with open('api/action-cards.json', 'w') as f:
        json.dump(cards, f, indent=2)

    # 8. ML endpoints
    with open('api/ml/feature-importance.json', 'w') as f:
        json.dump(ML_ENGINE.feature_importances, f, indent=2)
    with open('api/ml/stockout-risks.json', 'w') as f:
        json.dump(ML_ENGINE.get_stockout_probabilities(), f, indent=2)
    with open('api/ml/anomalies.json', 'w') as f:
        json.dump(ML_ENGINE.get_top_anomalies(), f, indent=2)

    # 9. Default simulation
    default_sim = simulate_interventions(DATA, {
        'reprice_negative_skus': True,
        'delist_negative_skus': False,
        'cap_discounts': True,
        'forbid_discount_low_margin': True,
        'pause_high_cpa_ads': True,
        'fix_stockouts_top20': True,
        'reduce_returns_top_skus': True
    })
    sim_data = {
        "baseline_net_contrib": round(float(default_sim['baseline_net_contrib']), 2),
        "simulated_net_contrib": round(float(default_sim['simulated_net_contrib']), 2),
        "total_recovered": round(float(default_sim['total_recovered']), 2),
        "breakdown": {k: round(float(v), 2) for k, v in default_sim['breakdown'].items()}
    }
    with open('api/simulate.json', 'w') as f:
        json.dump(sim_data, f, indent=2)

    # 10. SKU dossiers for all products
    prod_df = DATA['products']
    tx_df = DATA['transactions']
    inv_df = DATA['inventory']
    for _, p in prod_df.iterrows():
        p_id = p['product_id']
        p_tx = tx_df[tx_df['product_id'] == p_id]
        completed = p_tx[p_tx['status'] == 'Completed']
        p_inv = inv_df[inv_df['product_id'] == p_id]
        
        dossier = {
            "product_id": p_id,
            "category": p['category'],
            "unit_cost": float(p['unit_cost']),
            "list_price": float(p['list_price']),
            "base_unit_margin": float(p['base_unit_margin']),
            "is_negative_margin": bool(p['is_negative_margin']),
            "supplier_lead_days": int(p['supplier_lead_days']),
            "total_orders": len(p_tx),
            "completed_orders": len(completed),
            "returned_orders": int((p_tx['status'] == 'Returned').sum()),
            "cancelled_orders": int((p_tx['status'] == 'Cancelled').sum()),
            "return_rate": round(float((p_tx['status'] == 'Returned').sum() / max(len(p_tx), 1) * 100), 2),
            "total_units_sold": int(completed['quantity'].sum()),
            "net_revenue": round(float(completed['net_revenue'].sum()), 2),
            "gross_profit": round(float(completed['gross_profit'].sum()), 2),
            "stockout_days": int(p_inv['stockout_flag'].sum()) if not p_inv.empty else 0,
            "avg_supplier_delay": round(float(p_inv['supplier_delay_days'].mean()), 1) if not p_inv.empty else 0
        }
        with open(f'api/sku-dossier/{p_id}.json', 'w') as f:
            json.dump(dossier, f, indent=2)

    print("All static API datasets exported successfully!")

if __name__ == '__main__':
    main()
