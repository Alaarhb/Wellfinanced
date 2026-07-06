"""
WellFinanced — Expense Analyzer (Feature 2 Helper)
Uses Unsupervised ML (K-Means) to analyze spending patterns, 
cluster expenses into Needs/Wants, and detect trends.
"""

import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings("ignore")

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.data_loader import load_expenses, get_expense_breakdown, get_monthly_expenses

def analyze_expenses(user_id: str) -> dict:
    """
    Full expense analysis using K-Means clustering.
    """
    expenses = load_expenses()
    user_exp = expenses[expenses["user_id"] == user_id].copy()

    if user_exp.empty:
        return _empty_analysis()

    # --- NEW: Outlier Detection (IQR Method) ---
    # We filter out extreme outliers (e.g., one-time massive purchases) 
    # to ensure the K-Means clusters represent typical behavior.
    Q1 = user_exp['amount'].quantile(0.25)
    Q3 = user_exp['amount'].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 3.0 * IQR # Conservative bound (3x IQR)
    upper_bound = Q3 + 3.0 * IQR
    
    # Keep track of cleaned data for clustering logic
    user_exp_cleaned = user_exp[(user_exp['amount'] >= lower_bound) & (user_exp['amount'] <= upper_bound)].copy()
    # -------------------------------------------

    n_months = user_exp["month"].nunique()
    if n_months == 0: n_months = 1

    # Feature Extraction for Clustering (Using cleaned data)
    cat_features = []
    for cat, group in user_exp_cleaned.groupby('category'):
        freq = group['month'].nunique() / n_months
        monthly_totals = group.groupby(group['month'].dt.to_period('M'))['amount'].sum()
        avg_monthly = monthly_totals.mean()
        std_monthly = monthly_totals.std()
        
        if pd.isna(std_monthly):
            std_monthly = 0.0
            
        volatility = std_monthly / avg_monthly if avg_monthly > 0 else 0
        total_spent = group['amount'].sum()
        
        cat_features.append({
            'category': cat,
            'frequency': freq,
            'volatility': volatility,
            'avg_monthly': avg_monthly,
            'total_spent': total_spent
        })

    feat_df = pd.DataFrame(cat_features)
    
    # ML Clustering (K-Means)
    needs_total = 0.0
    wants_total = 0.0
    
    if len(feat_df) >= 2:
        X = feat_df[['frequency', 'volatility', 'avg_monthly']]
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        kmeans = KMeans(n_clusters=2, random_state=42, n_init=10)
        feat_df['cluster'] = kmeans.fit_predict(X_scaled)
        
        # Calculate Silhouette Score to evaluate clustering quality
        try:
            sil_score = silhouette_score(X_scaled, feat_df['cluster'])
        except ValueError:
            sil_score = 0.0

        cluster_0_freq = feat_df[feat_df['cluster'] == 0]['frequency'].mean()
        cluster_1_freq = feat_df[feat_df['cluster'] == 1]['frequency'].mean()

        needs_cluster_id = 0 if cluster_0_freq > cluster_1_freq else 1
        feat_df['type'] = feat_df['cluster'].apply(lambda c: 'Need' if c == needs_cluster_id else 'Want')
    else:
        # Fallback if user only has 1 category
        feat_df['type'] = 'Need'
        feat_df['cluster'] = 0
        sil_score = 0.0

    category_breakdown = []
    total_expenses = feat_df['total_spent'].sum()
    
    for _, row in feat_df.iterrows():
        cat_type = row['type']
        if cat_type == 'Need':
            needs_total += row['avg_monthly']
        else:
            wants_total += row['avg_monthly']
            
        category_breakdown.append({
            "category": row["category"],
            "type": cat_type,
            "total": round(row["total_spent"], 2),
            "avg_monthly": round(row["avg_monthly"], 2),
            "pct": round(row["total_spent"] / total_expenses * 100, 1) if total_expenses > 0 else 0,
            "frequency": round(row["frequency"], 2),
            "volatility": round(row["volatility"], 2)
        })

    monthly_avg = needs_total + wants_total

    # Spending trends
    spending_trends = _calculate_trends(user_exp)

    # Top spending categories
    top_spending = feat_df.sort_values(by='avg_monthly', ascending=False).head(3)["category"].tolist()

    monthly = get_monthly_expenses(user_id)
    monthly_data = [
        {"month": row["month"].strftime("%Y-%m"), "amount": round(row["total_expenses"], 2)}
        for _, row in monthly.iterrows()
    ]

    return {
        "monthly_avg": round(monthly_avg, 2),
        "recurring_avg": round(needs_total, 2),  # Kept for backward compatibility
        "non_recurring_avg": round(wants_total, 2), # Kept for backward compatibility
        "category_breakdown": category_breakdown,
        "needs_total": round(needs_total, 2),
        "wants_total": round(wants_total, 2),
        "needs_pct": round(needs_total / monthly_avg * 100, 1) if monthly_avg > 0 else 0,
        "wants_pct": round(wants_total / monthly_avg * 100, 1) if monthly_avg > 0 else 0,
        "spending_trends": spending_trends,
        "top_spending": top_spending,
        "monthly_data": monthly_data,
        "clustering_score": round(sil_score, 4),
    }

def _calculate_trends(user_exp: pd.DataFrame) -> list:
    user_exp = user_exp.copy()
    months_sorted = sorted(user_exp["month"].unique())

    if len(months_sorted) < 6:
        return []

    recent_3 = months_sorted[-3:]
    prev_3 = months_sorted[-6:-3]

    recent = user_exp[user_exp["month"].isin(recent_3)]
    prev = user_exp[user_exp["month"].isin(prev_3)]

    recent_by_cat = recent.groupby("category")["amount"].sum()
    prev_by_cat = prev.groupby("category")["amount"].sum()

    trends = []
    all_cats = set(recent_by_cat.index) | set(prev_by_cat.index)
    for cat in all_cats:
        r = recent_by_cat.get(cat, 0)
        p = prev_by_cat.get(cat, 0)
        if p > 0:
            change = ((r - p) / p) * 100
        elif r > 0:
            change = 100.0
        else:
            change = 0.0

        if abs(change) > 10:
            trends.append({
                "category": cat,
                "trend": "increasing" if change > 0 else "decreasing",
                "change_pct": round(change, 1),
            })

    return sorted(trends, key=lambda x: abs(x["change_pct"]), reverse=True)

def _empty_analysis() -> dict:
    return {
        "monthly_avg": 0, "recurring_avg": 0, "non_recurring_avg": 0,
        "category_breakdown": [], "needs_total": 0, "wants_total": 0,
        "needs_pct": 0, "wants_pct": 0, "spending_trends": [],
        "top_spending": [], "monthly_data": [], "clustering_score": 0.0
    }

if __name__ == "__main__":
    print("Testing ML Expense Analyzer (K-Means)...")
    result = analyze_expenses("user_0001")
    print(f"Monthly Avg Expenses: {result['monthly_avg']:,.2f}")
    print(f"Needs (AI Classified): {result['needs_total']:,.2f} ({result['needs_pct']}%)")
    print(f"Wants (AI Classified): {result['wants_total']:,.2f} ({result['wants_pct']}%)")
    print(f"K-Means Confidence (Silhouette): {result['clustering_score']}")
    
    print("\nCategorization Breakdown:")
    for c in result['category_breakdown']:
        print(f"  {c['category']:15s} | Type: {c['type']:5s} | Freq: {c['frequency']:.2f} | Volatility: {c['volatility']:.2f}")
