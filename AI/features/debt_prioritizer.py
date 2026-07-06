"""
WellFinanced — Feature 3: Autonomous Debt & Bill Prioritization
Scores and ranks debts using ML (XGBoost) and generates detailed payment plans.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import os
import sys
from sklearn.model_selection import train_test_split
import xgboost as xgb

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.data_loader import get_user_debts

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

def _load_csv(filename):
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame()

def _get_financial_context():
    """Calculate monthly surplus for all users to enrich debt data."""
    income_df = _load_csv("income.csv")
    expenses_df = _load_csv("expenses.csv")
    
    if income_df.empty or expenses_df.empty:
        return {}

    # Use actual month count per user instead of hardcoded 12
    income_months = income_df.groupby('user_id')['month'].nunique()
    avg_income = income_df.groupby('user_id')['amount'].sum() / income_months

    expenses_df['month'] = pd.to_datetime(expenses_df['expense_date']).dt.to_period('M')
    expense_months = expenses_df.groupby('user_id')['month'].nunique()
    avg_expenses = expenses_df.groupby('user_id')['amount'].sum() / expense_months

    surplus = (avg_income - avg_expenses).to_dict()
    return surplus

def score_debts_ml(user_id: str) -> pd.DataFrame:
    """
    Score and rank debts using an XGBoost model trained on global debt data.
    """
    debts = get_user_debts(user_id)
    all_debts = _load_csv("debts.csv")
    surplus_map = _get_financial_context()

    if debts.empty or all_debts.empty:
        return debts

    def prepare_features(df):
        df = df.copy()
        df['due_date'] = pd.to_datetime(df['due_date'])
        now = pd.Timestamp.now()
        df['days_until_due'] = (df['due_date'] - now).dt.days.clip(lower=1)
        df['remaining_ratio'] = df['remaining_amount'] / df['total_amount']
        df['monthly_surplus'] = df['user_id'].map(surplus_map).fillna(0)
        return df

    # 1. Train Model on all debts
    train_data = prepare_features(all_debts)
    
    # Target Synthesis (mimic the logic in the notebook)
    def synthesize_risk(row):
        risk = row['interest_rate'] * 2.5 + (150 / (row['days_until_due'] + 1)) + (row['remaining_ratio'] * 20)
        risk -= (row['monthly_surplus'] / 1000)
        return np.clip(risk + np.random.normal(0, 2), 0, 100)

    np.random.seed(42)
    train_data['target_risk'] = train_data.apply(synthesize_risk, axis=1)
    
    features = ['interest_rate', 'days_until_due', 'remaining_ratio', 'monthly_surplus', 'priority']
    X = train_data[features]
    y = train_data['target_risk']
    
    model = xgb.XGBRegressor(n_estimators=50, max_depth=3, learning_rate=0.1, random_state=42)
    model.fit(X, y)

    # 2. Predict for target user
    user_debts_proc = prepare_features(debts)
    user_debts_proc['urgency_score'] = model.predict(user_debts_proc[features])
    
    # Normalize 0-1
    s_min = user_debts_proc['urgency_score'].min()
    s_max = user_debts_proc['urgency_score'].max()
    if s_max != s_min:
        user_debts_proc['urgency_score'] = (user_debts_proc['urgency_score'] - s_min) / (s_max - s_min)
    else:
        user_debts_proc['urgency_score'] = 0.5

    user_debts_proc = user_debts_proc.sort_values('urgency_score', ascending=False)
    user_debts_proc['rank'] = range(1, len(user_debts_proc) + 1)
    
    return user_debts_proc

def prioritize_debts(user_id: str, strategy: str = "hybrid", monthly_budget: float = None) -> dict:
    """
    Main API: Prioritize debts and generate payment plan.
    """
    scored = score_debts_ml(user_id)

    if scored.empty:
        return {"ranked_debts": [], "payment_schedule": [], "months_to_free": 0}

    if monthly_budget is None:
        # Default: Sum of minimums + 20%
        monthly_budget = scored["monthly_payment"].sum() * 1.2

    # Simulation Logic
    def simulate(df, strat):
        temp_df = df.copy()
        if strat == 'avalanche':
            temp_df = temp_df.sort_values('interest_rate', ascending=False)
        elif strat == 'snowball':
            temp_df = temp_df.sort_values('remaining_amount', ascending=True)
        else: # hybrid
            temp_df = temp_df.sort_values('urgency_score', ascending=False)
        
        debt_names = temp_df['debt_name'].tolist()
        balances = temp_df['remaining_amount'].values.astype(float)
        rates = temp_df['interest_rate'].values / 100 / 12
        mins = temp_df['monthly_payment'].values
        
        total_interest = 0
        months = 0
        total_paid = 0
        schedule = []
        payoff_dates = {}
        
        while any(balances > 0.01) and months < 120:
            months += 1
            rem_budget = monthly_budget
            month_interest = 0
            month_payments = {name: 0 for name in debt_names}
            
            for i in range(len(balances)):
                if balances[i] <= 0: continue
                interest = balances[i] * rates[i]
                balances[i] += interest
                month_interest += interest
                p = min(balances[i], mins[i], max(0, rem_budget))
                balances[i] -= p
                rem_budget -= p
                total_paid += p
                month_payments[debt_names[i]] += p
            
            if rem_budget > 0:
                for i in range(len(balances)):
                    if balances[i] <= 0: continue
                    extra = min(balances[i], rem_budget)
                    balances[i] -= extra
                    rem_budget -= extra
                    total_paid += extra
                    month_payments[debt_names[i]] += extra
                    if rem_budget <= 0: break
            
            for i in range(len(balances)):
                if balances[i] <= 0.01 and debt_names[i] not in payoff_dates:
                    payoff_dates[debt_names[i]] = months
            
            total_interest += month_interest
            schedule.append({"month": months, "payments": month_payments})
            
        return months, total_interest, total_paid, schedule, payoff_dates

    # Run for target strategy
    m, i, t, sched, pod = simulate(scored, strategy)
    
    # Comparison
    comparison = []
    for s in ["avalanche", "snowball", "hybrid"]:
        sm, si, st, _, _ = simulate(scored, s)
        comparison.append({"strategy": s, "months": sm, "interest": si, "total": st})

    return {
        "ranked_debts": scored[['debt_name', 'remaining_amount', 'interest_rate', 'urgency_score', 'rank']].to_dict('records'),
        "strategy": strategy,
        "payment_schedule": sched,
        "payoff_dates": pod,
        "total_interest": round(i, 2),
        "months_to_free": m,
        "total_paid": round(t, 2),
        "strategy_comparison": comparison
    }

if __name__ == "__main__":
    res = prioritize_debts("user_0004")
    print(f"Goal: Debt-free in {res['months_to_free']} months using {res['strategy']}")
    print(f"Ranked Debts: {len(res['ranked_debts'])}")
    print(f"Total Interest: {res['total_interest']}")
