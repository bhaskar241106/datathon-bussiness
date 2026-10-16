import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel
import pandas as pd
import numpy as np

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
from decision_playbook import simulate_interventions, get_action_playbook_cards
from ml_engine import MoneyLeakMLEngine

app = FastAPI(title="The Money Leak API", description="Decision Support Engine API")

# Enable CORS for modern web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load data on startup
print("Loading and caching Datathon datasets...")
DATA = load_all_data()
KPIS = calculate_executive_kpis(DATA)
MARGIN_AUDIT = get_negative_margin_analysis(DATA)
RETURN_AUDIT = get_return_cancellation_analysis(DATA)
INV_AUDIT = get_inventory_stockout_analysis(DATA)
MKT_AUDIT = get_marketing_campaign_analysis(DATA)
RFM_AUDIT = run_customer_segmentation(DATA)
ML_ENGINE = MoneyLeakMLEngine(DATA)
print("Data and ML models precomputed and ready for high-speed queries!")

class SimulationRequest(BaseModel):
    reprice_negative_skus: bool = True
    delist_negative_skus: bool = False
    cap_discounts: bool = True
    forbid_discount_low_margin: bool = True
    pause_high_cpa_ads: bool = True
    fix_stockouts_top20: bool = True
    reduce_returns_top_skus: bool = True
    target_margin_pct: float = 25.0
    cpa_threshold: float = 40.0

@app.get("/api/overview")
def get_overview():
    return {
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

@app.get("/api/margins")
def get_margins():
    all_prods = MARGIN_AUDIT['all_products'].copy()
    neg_prods = MARGIN_AUDIT['negative_margin_products'].copy()
    
    # Scatter points sample / complete
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

    # Loss table top 25
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

    return {
        "total_skus": len(all_prods),
        "negative_margin_count": int(MARGIN_AUDIT['negative_count']),
        "negative_margin_loss": round(float(MARGIN_AUDIT['total_loss']), 2),
        "scatter": scatter,
        "loss_table": table_data
    }

@app.get("/api/returns")
def get_returns():
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

    return {
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

@app.get("/api/inventory")
def get_inventory():
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

    return {
        "stockout_incidents": int(INV_AUDIT['total_stockout_incidents']),
        "lost_revenue": round(float(INV_AUDIT['total_estimated_lost_rev']), 2),
        "lost_margin": round(float(INV_AUDIT['total_estimated_lost_margin']), 2),
        "top_stockouts": top_stockouts,
        "category_loss": cat_loss
    }

@app.get("/api/marketing")
def get_marketing():
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

    return {
        "total_spend": round(float(KPIS['total_ad_spend']), 2),
        "bleeding_spend": round(float(MKT_AUDIT['total_bleeding_spend']), 2),
        "category_pnl": cat_pnl,
        "tier_summary": tiers,
        "bleeding_campaigns": bleeding
    }

@app.get("/api/customers")
def get_customers():
    counts = RFM_AUDIT['value_tier'].value_counts().to_dict()
    profit_by_tier = RFM_AUDIT.groupby('value_tier')['gross_profit'].sum().round(2).to_dict()
    
    return {
        "tier_counts": counts,
        "profit_by_tier": profit_by_tier,
        "total_customers": len(RFM_AUDIT)
    }

@app.post("/api/simulate")
def run_simulation(req: SimulationRequest):
    levers = {
        'reprice_negative_skus': req.reprice_negative_skus,
        'delist_negative_skus': req.delist_negative_skus,
        'cap_discounts': req.cap_discounts,
        'forbid_discount_low_margin': req.forbid_discount_low_margin,
        'pause_high_cpa_ads': req.pause_high_cpa_ads,
        'fix_stockouts_top20': req.fix_stockouts_top20,
        'reduce_returns_top_skus': req.reduce_returns_top_skus
    }
    res = simulate_interventions(DATA, levers)
    
    return {
        "baseline_net_contrib": round(float(res['baseline_net_contrib']), 2),
        "simulated_net_contrib": round(float(res['simulated_net_contrib']), 2),
        "total_recovered": round(float(res['total_recovered']), 2),
        "breakdown": {k: round(float(v), 2) for k, v in res['breakdown'].items()}
    }

@app.get("/api/action-cards")
def get_action_cards():
    return get_action_playbook_cards()

@app.get("/api/sku-dossier/{product_id}")
def get_sku_dossier(product_id: str):
    prod = DATA['products']
    p_row = prod[prod['product_id'] == product_id]
    if p_row.empty:
        raise HTTPException(status_code=404, detail="Product not found")
    
    p = p_row.iloc[0]
    tx = DATA['transactions']
    p_tx = tx[tx['product_id'] == product_id]
    completed = p_tx[p_tx['status'] == 'Completed']
    
    inv = DATA['inventory']
    p_inv = inv[inv['product_id'] == product_id]
    
    return {
        "product_id": product_id,
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

class OrderPredictRequest(BaseModel):
    category: str = "Electronics"
    channel: str = "Web"
    payment_method: str = "Card"
    region: str = "West"
    quantity: int = 2
    unit_price: float = 180.0
    discount_pct: float = 0.15
    supplier_lead_days: int = 14

@app.post("/api/ml/predict-order")
def predict_order_endpoint(req: OrderPredictRequest):
    return ML_ENGINE.predict_order_risk(req.dict())

@app.get("/api/ml/feature-importance")
def get_feature_importance_endpoint():
    return ML_ENGINE.feature_importances

@app.get("/api/ml/stockout-risks")
def get_stockout_risks_endpoint():
    return ML_ENGINE.get_stockout_probabilities()

@app.get("/api/ml/anomalies")
def get_anomalies_endpoint():
    return ML_ENGINE.get_top_anomalies()

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir, exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def serve_index():
    root_index = os.path.join(os.path.dirname(__file__), "index.html")
    if os.path.exists(root_index):
        return FileResponse(root_index)
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return PlainTextResponse("Static index.html not yet created.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
