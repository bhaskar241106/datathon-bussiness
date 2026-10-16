import numpy as np
import pandas as pd

def simulate_interventions(data, levers):
    """
    Simulates business performance under user-selected strategic levers.
    levers dict contains:
      - 'reprice_negative_skus': bool (Reprice negative margin SKUs to Cost / 0.75 for 25% margin)
      - 'delist_negative_skus': bool (Delist negative margin SKUs completely)
      - 'cap_discounts': bool (Cap transaction discounts at 10%)
      - 'forbid_discount_low_margin': bool (Forbid discounts if base margin < 20%)
      - 'pause_high_cpa_ads': bool (Pause campaigns with CPA > $40)
      - 'fix_stockouts_top20': bool (Implement safety stock on top 20 stockout SKUs)
      - 'reduce_returns_top_skus': bool (Target 35% return reduction on top 19 high-return SKUs)
    """
    tx = data['transactions'].copy()
    camp = data['campaigns'].copy()
    inv = data['inventory'].copy()
    prod = data['products'].copy()

    completed = tx[tx['status'] == 'Completed'].copy()
    returned = tx[tx['status'] == 'Returned'].copy()

    # Baseline numbers
    baseline_revenue = completed['net_revenue'].sum()
    baseline_gp = completed['gross_profit'].sum()
    baseline_ad_spend = camp['spend'].sum()
    baseline_return_handling = returned['return_handling_cost'].sum()
    baseline_net_contrib = baseline_gp - baseline_ad_spend - baseline_return_handling

    # Running recoveries
    delta_pricing = 0.0
    delta_discount = 0.0
    delta_ad_spend = 0.0
    delta_inventory = 0.0
    delta_returns = 0.0

    # 1. Pricing / Delist Lever
    if levers.get('reprice_negative_skus', False):
        # Reprice: increase realized price to unit_cost / 0.75 (25% margin)
        neg_mask = completed['unit_cost'] > completed['list_price']
        neg_orders = completed[neg_mask]
        # Target net revenue per unit = unit_cost / 0.75
        target_unit_price = neg_orders['unit_cost'] / 0.75
        recovered_margin = (target_unit_price * neg_orders['quantity'] - neg_orders['cogs']).sum() - neg_orders['gross_profit'].sum()
        delta_pricing += max(recovered_margin, 0)
    elif levers.get('delist_negative_skus', False):
        # Delist: eliminate the negative gross profit losses
        neg_loss = completed[completed['gross_profit'] < 0]['gross_profit'].sum()
        delta_pricing += abs(neg_loss)

    # 2. Discount Levers
    if levers.get('cap_discounts', False):
        # Cap discount at 10%
        high_disc_mask = completed['discount_pct'] > 0.10
        excess_discount_pct = completed.loc[high_disc_mask, 'discount_pct'] - 0.10
        saved_discount = (completed.loc[high_disc_mask, 'gross_revenue'] * excess_discount_pct).sum()
        delta_discount += saved_discount

    if levers.get('forbid_discount_low_margin', False):
        # Eliminate discount on products where base margin < 20%
        low_margin_prods = prod[prod['base_margin_pct'] < 0.20]['product_id']
        low_margin_orders = completed[completed['product_id'].isin(low_margin_prods)]
        saved_low_margin_disc = low_margin_orders['discount_amount'].sum()
        delta_discount += saved_low_margin_disc

    # 3. Ad Spend Lever
    if levers.get('pause_high_cpa_ads', False):
        # Cut campaigns with CPA > $40
        bleeding_camps = camp[camp['cpa'] > 40]
        saved_ad_spend = bleeding_camps['spend'].sum()
        delta_ad_spend += saved_ad_spend

    # 4. Inventory Stockout Lever
    if levers.get('fix_stockouts_top20', False):
        # Reclaim lost gross profit from top 20 stockout SKUs
        product_daily_sales = completed.groupby(['product_id', 'date'])['quantity'].sum().reset_index()
        avg_daily = product_daily_sales.groupby('product_id')['quantity'].mean().reset_index(name='avg_daily')
        top_stockout_prods = inv.groupby('product_id')['stockout_flag'].sum().sort_values(ascending=False).head(20).reset_index()
        top_stockout_data = top_stockout_prods.merge(avg_daily, on='product_id', how='left').merge(prod, on='product_id', how='left')
        top_stockout_data['unit_margin'] = top_stockout_data['list_price'] - top_stockout_data['unit_cost']
        top_stockout_data['positive_unit_margin'] = top_stockout_data['unit_margin'].clip(lower=0)
        # Recover 80% of lost sales
        recovered_stockout_gp = (top_stockout_data['stockout_flag'] * top_stockout_data['avg_daily'].fillna(1.5) * top_stockout_data['positive_unit_margin'] * 0.80).sum()
        delta_inventory += recovered_stockout_gp

    # 5. Return Reduction Lever
    if levers.get('reduce_returns_top_skus', False):
        # Target 35% return reduction on top 19 high-return SKUs
        prod_ret = tx.groupby(['product_id']).agg(
            total_orders=('transaction_id', 'count'),
            returned_orders=('status', lambda s: (s == 'Returned').sum()),
            returned_val=('net_revenue', lambda v: v[tx.loc[v.index, 'status'] == 'Returned'].sum())
        ).reset_index()
        prod_ret['return_rate'] = prod_ret['returned_orders'] / prod_ret['total_orders']
        high_ret_ids = prod_ret[prod_ret['return_rate'] > 0.12]['product_id']

        high_ret_orders = returned[returned['product_id'].isin(high_ret_ids)]
        # Reclaimed value = 35% of gross margin on returned items + handling fee saved
        reclaimed_value = (high_ret_orders['gross_revenue'] * 0.35 * 0.25).sum() + (high_ret_orders['return_handling_cost'] * 0.35).sum()
        delta_returns += reclaimed_value

    # Simulated Totals
    total_recovered = delta_pricing + delta_discount + delta_ad_spend + delta_inventory + delta_returns
    simulated_net_contrib = baseline_net_contrib + total_recovered

    return {
        'baseline_net_contrib': baseline_net_contrib,
        'simulated_net_contrib': simulated_net_contrib,
        'total_recovered': total_recovered,
        'breakdown': {
            'Pricing Optimization': delta_pricing,
            'Discount Rationalization': delta_discount,
            'Ad Spend Pruning': delta_ad_spend,
            'Inventory Availability': delta_inventory,
            'Return Rate Mitigation': delta_returns
        }
    }

def get_action_playbook_cards():
    """
    Returns structured prescriptive decision cards answering:
    1. What is going wrong?
    2. What evidence supports this?
    3. What action should the manager take?
    4. Estimated financial impact.
    5. Department owner.
    """
    return [
        {
            'id': 'LEAK-01',
            'severity': 'CRITICAL',
            'title': 'The Negative Margin Trap: Upside-Down Product Pricing',
            'what_going_wrong': '76 catalog products (30.4% of catalog) have unit costs higher than their list price. Selling these products loses money on every completed order.',
            'evidence': '5,315 completed transactions (38.1% of all sales) generated a cumulative gross profit loss of -$1,214,115.50. Products like PR0192, PR0163, PR0210 lose up to $20k+ each.',
            'recommended_action': 'Implement an automated pricing floor rule: Minimum List Price = Unit Cost * 1.35. For SKUs where market price elasticity prohibits price increases, immediately delist or renegotiate supplier COGS.',
            'financial_impact': '+$1,170,000 to +$1,214,000 Gross Margin Recovery',
            'owner': 'Merchandising & Pricing Strategy Team',
            'urgency': 'Immediate (Week 1)'
        },
        {
            'id': 'LEAK-02',
            'severity': 'HIGH',
            'title': 'Runaway Ad Spend & Extreme CPA Outliers',
            'what_going_wrong': 'Total marketing ad spend ($4.81M) exceeds total completed gross profit ($1.97M) by 2.44x. Campaigns are operating with zero profitability gating.',
            'evidence': '56 campaigns have Cost Per Acquisition (CPA) exceeding $50, with worst-case campaigns reaching $1,979 CPA. Categories like Beauty spent $870K on ads to produce only $66K in gross margin.',
            'recommended_action': 'Establish an automated campaign kill-switch: pause any ad set where 7-day rolling CPA exceeds $40 or ROAS falls below 1.2x. Shift 30% of budget from Store/Social channels into high-converting App/Email campaigns.',
            'financial_impact': '+$297,000 to +$500,000 Direct Ad Spend Saved',
            'owner': 'Performance Marketing & Growth Lead',
            'urgency': 'Immediate (Week 1)'
        },
        {
            'id': 'LEAK-03',
            'severity': 'HIGH',
            'title': 'Unmitigated Discounting on Margin-Sensitive SKUs',
            'what_going_wrong': 'Sales channels layer discounts up to 25% on top of pre-discounted transaction unit prices, eroding profit even on healthy margin SKUs.',
            'evidence': '$773,420.66 was given in explicit discounts. Transactions show average discounts of 8.3%, with 4,500+ orders receiving 15%-25% discounts even on low-margin items.',
            'recommended_action': 'Establish dynamic discount gating: cap sitewide promotional discounts at 10% maximum, and set a hard rule prohibiting promotional discounts on any product with a baseline gross margin below 20%.',
            'financial_impact': '+$250,000 to +$380,000 Retained Revenue',
            'owner': 'Sales & Promotional Strategy Team',
            'urgency': 'Near-Term (Week 2)'
        },
        {
            'id': 'LEAK-04',
            'severity': 'MEDIUM',
            'title': 'Ghost Demand & Stockouts on Top Velocity SKUs',
            'what_going_wrong': 'High-velocity SKUs experience frequent stockouts while marketing campaigns continue driving traffic to those categories, forfeiting high-margin sales.',
            'evidence': '760 inventory stockout days recorded. Top sellers like PR0218, PR0068, PR0220 face 6-7 stockout days with supplier lead delays averaging 10-12 days, forfeiting ~$508K in lost gross demand.',
            'recommended_action': 'Recalibrate Safety Stock and Reorder Points (ROP) using lead-time demand variability. Set automated low-stock pauses on ad campaigns when inventory falls below 5 days of supply.',
            'financial_impact': '+$180,000 to +$250,000 Reclaimed Gross Profit',
            'owner': 'Supply Chain & Inventory Operations',
            'urgency': 'Mid-Term (Month 1)'
        },
        {
            'id': 'LEAK-05',
            'severity': 'MEDIUM',
            'title': 'High-Return SKU Defect & Misalignment Sink',
            'what_going_wrong': '19 SKUs exhibit abnormal return rates (up to 16%, double the 8% benchmark), incurring product devaluation and reverse logistics handling costs.',
            'evidence': '1,431 returned orders wiped out $760K in net sales plus ~$17K in reverse handling costs. Top return SKUs include PR0198 (Sports, 16.0%), PR0184 (Electronics, 14.9%), PR0066 (Electronics, 16.1%).',
            'recommended_action': 'Conduct quality audit with suppliers for PR0198 and PR0184. Review product page specifications, sizing charts, and customer imagery to eliminate buyer expectation mismatches.',
            'financial_impact': '+$150,000 to +$228,000 in Saved Margin & Freight',
            'owner': 'Quality Assurance & Customer Experience',
            'urgency': 'Mid-Term (Month 1)'
        }
    ]
