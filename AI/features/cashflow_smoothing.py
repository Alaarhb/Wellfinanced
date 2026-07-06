"""
WellFinanced — Feature 2: Intelligent Cashflow Smoothing
Converts irregular freelancer income into a virtual fixed salary
with smart budget allocation using the 50/30/20 rule.
"""

import pandas as pd
import numpy as np

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.data_loader import get_user_profile, get_user_savings, get_user_debts, load_users, get_income_stats
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from features.income_forecast import forecast_income
from features.expense_analyzer import analyze_expenses


# Fallback profile-based salary multipliers
SALARY_MULTIPLIERS = {
    "stable": 0.80,
    "growing": 0.75,
    "inconsistent": 0.65,
    "struggling": 0.60,
}


def get_budget_plan(user_id: str) -> dict:
    """
    Generate a comprehensive budget plan for a user.
    
    Combines income forecast + expense analysis to produce:
    - Virtual salary recommendation
    - Budget allocation (50/30/20)
    - Surplus/deficit analysis
    - Savings goal progress
    - Actionable alerts
    
    Returns:
        dict: {
            virtual_salary: float,
            profile_type: str,
            multiplier: float,
            predicted_income: float,
            budget: {
                needs: {amount, pct, categories: [{name, recommended, actual}]},
                wants: {amount, pct, categories: [...]},
                savings: {amount, pct},
                debt_payments: {amount, pct},
            },
            surplus_deficit: float,
            savings_goals: [{name, target, saved, monthly, progress_pct, on_track}],
            alerts: [str],
            expense_summary: dict,
        }
    """
    # Get user profile
    profile = get_user_profile(user_id)
    profile_type = profile.get("profile_type", "inconsistent")

    # Get income forecast
    forecast = forecast_income(user_id, months_ahead=3)
    predicted_income = forecast.get("avg_predicted", 0)

    # If no prediction, use historical average
    if predicted_income == 0:
        predicted_income = profile.get("avg_monthly_income", 0)

    # Calculate AI-driven virtual salary multiplier
    try:
        multiplier, mlp_loss_curve = _train_and_predict_multiplier(user_id)
        virtual_salary = round(predicted_income * multiplier, 2)
    except Exception as e:
        print(f"AI Recommender failed, falling back to static multiplier: {e}")
        multiplier = SALARY_MULTIPLIERS.get(profile_type, 0.65)
        virtual_salary = round(predicted_income * multiplier, 2)
        mlp_loss_curve = []

    # Get expense analysis
    expense_analysis = analyze_expenses(user_id)

    # Get debts for debt payment allocation
    debts = get_user_debts(user_id)
    total_debt_payments = debts["monthly_payment"].sum() if not debts.empty else 0

    # Build budget allocation
    budget = _allocate_budget(virtual_salary, expense_analysis, total_debt_payments)

    # Calculate surplus/deficit
    actual_expenses = expense_analysis["monthly_avg"]
    surplus_deficit = round(virtual_salary - actual_expenses - total_debt_payments, 2)

    # Savings goals analysis
    savings_goals = _analyze_savings_goals(user_id, virtual_salary, budget)

    # Generate alerts
    alerts = _generate_alerts(
        virtual_salary, predicted_income, expense_analysis,
        surplus_deficit, profile_type, total_debt_payments
    )

    return {
        "virtual_salary": virtual_salary,
        "profile_type": profile_type,
        "multiplier": multiplier,
        "predicted_income": round(predicted_income, 2),
        "budget": budget,
        "surplus_deficit": surplus_deficit,
        "savings_goals": savings_goals,
        "alerts": alerts,
        "expense_summary": {
            "monthly_avg": expense_analysis["monthly_avg"],
            "needs_pct": expense_analysis["needs_pct"],
            "wants_pct": expense_analysis["wants_pct"],
            "top_spending": expense_analysis["top_spending"],
        },
        "total_debt_payments": round(total_debt_payments, 2),
        "ai_insights": {
            "loss_curve": mlp_loss_curve,
        },
        "backtest_results": run_backtest(user_id, virtual_salary, total_debt_payments)
    }


def run_backtest(user_id: str, virtual_salary: float, monthly_debt: float) -> dict:
    """
    Simulates the Virtual Salary budget against historical data to measure stability.
    Returns cash balance history and safety metrics.
    """
    from utils.data_loader import get_monthly_income, get_monthly_expenses
    
    inc = get_monthly_income(user_id)
    exp = get_monthly_expenses(user_id)
    
    # Merge on month
    history = pd.merge(inc[['month', 'total_income']], exp[['month', 'total_expenses']], on='month', how='inner')
    history = history.sort_values('month')
    
    balance = 0
    balance_history = []
    virtual_salary_met = []
    
    for _, row in history.iterrows():
        # Actual surplus/deficit with Virtual Salary
        # We assume the user 'pays' themselves the Virtual Salary
        # The surplus (Income - Virtual Salary) goes into a buffer
        surplus = row['total_income'] - virtual_salary - monthly_debt
        balance += surplus
        
        balance_history.append({"month": row["month"].strftime("%Y-%m"), "balance": round(balance, 2)})
        virtual_salary_met.append(balance >= 0)
        
    reliability_score = (sum(virtual_salary_met) / len(virtual_salary_met) * 100) if virtual_salary_met else 100
    
    return {
        "balance_history": balance_history,
        "reliability_score": round(reliability_score, 1), # % of months balance stayed positive
        "final_buffer": round(balance, 2)
    }


def _train_and_predict_multiplier(target_user_id: str):
    """
    Trains a Deep Learning Neural Network (MLPRegressor) on synthetic optimal
    multipliers to predict a personalized safety multiplier.
    Returns (multiplier, loss_curve)
    """
    users_df = load_users()
    X_data = []
    y_data = []
    
    target_features = None
    
    for _, row in users_df.iterrows():
        uid = row["user_id"]
        stats = get_income_stats(uid)
        cv = stats.get("cv", 0.0) # Income volatility
        avg_income = stats.get("avg", 0.0)
        
        debts = get_user_debts(uid)
        total_debt = debts["monthly_payment"].sum() if not debts.empty else 0
        debt_ratio = total_debt / avg_income if avg_income > 0 else 0.0
        
        # Synthetic optimal target: penalized for high volatility and high debt
        optimal_mult = 1.0 - (cv * 0.5) - (debt_ratio * 0.2)
        optimal_mult = max(0.5, min(0.9, optimal_mult)) # Clip between 0.5 and 0.9
        
        features = [cv, debt_ratio]
        X_data.append(features)
        y_data.append(optimal_mult)
        
        if uid == target_user_id:
            target_features = features
            
    if target_features is None:
        target_features = [0.0, 0.0]

    X = np.array(X_data)
    y = np.array(y_data)
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Deep Learning Model
    mlp = MLPRegressor(
        hidden_layer_sizes=(16, 8), 
        activation='relu', 
        random_state=42, 
        max_iter=500
    )
    mlp.fit(X_scaled, y)
    
    # Predict for the target user
    X_target = scaler.transform([target_features])
    predicted_mult = mlp.predict(X_target)[0]
    
    # Final safety clipping
    final_mult = round(max(0.5, min(0.9, float(predicted_mult))), 2)
    return final_mult, mlp.loss_curve_


def _allocate_budget(virtual_salary: float, expense_analysis: dict, debt_payments: float) -> dict:
    """
    Allocate budget using adjusted 50/30/20 rule.
    If debts exist, savings allocation is split between savings and debt.
    """
    # Base allocation
    needs_budget = round(virtual_salary * 0.50, 2)
    wants_budget = round(virtual_salary * 0.30, 2)
    savings_and_debt = round(virtual_salary * 0.20, 2)

    # Split savings_and_debt between actual savings and debt
    if debt_payments > 0:
        debt_allocation = min(debt_payments, savings_and_debt)
        savings_budget = max(0, savings_and_debt - debt_allocation)
    else:
        debt_allocation = 0
        savings_budget = savings_and_debt

    # Map actual expenses to recommended budget
    needs_categories = []
    wants_categories = []

    for item in expense_analysis["category_breakdown"]:
        entry = {
            "name": item["category"],
            "actual": item["avg_monthly"],
            "recommended": 0,  # Will be calculated below
        }
        if item.get("type", "Need") == "Need":
            needs_categories.append(entry)
        else:
            wants_categories.append(entry)

    # Distribute budget proportionally within each category group
    _distribute_budget(needs_categories, needs_budget)
    _distribute_budget(wants_categories, wants_budget)

    return {
        "needs": {
            "amount": needs_budget,
            "pct": 50,
            "categories": needs_categories,
        },
        "wants": {
            "amount": wants_budget,
            "pct": 30,
            "categories": wants_categories,
        },
        "savings": {
            "amount": savings_budget,
            "pct": round(savings_budget / virtual_salary * 100, 1) if virtual_salary > 0 else 0,
        },
        "debt_payments": {
            "amount": debt_allocation,
            "pct": round(debt_allocation / virtual_salary * 100, 1) if virtual_salary > 0 else 0,
        },
    }


def _distribute_budget(categories: list, total_budget: float):
    """Distribute budget proportionally based on actual spending."""
    total_actual = sum(c["actual"] for c in categories)
    if total_actual == 0:
        return

    for cat in categories:
        cat["recommended"] = round(cat["actual"] / total_actual * total_budget, 2)


def _analyze_savings_goals(user_id: str, virtual_salary: float, budget: dict) -> list:
    """Analyze progress toward savings goals."""
    savings = get_user_savings(user_id)
    if savings.empty:
        return []

    savings_budget = budget["savings"]["amount"]
    goals = []

    for _, row in savings.iterrows():
        remaining = row["target_amount"] - row["saved_amount"]
        progress_pct = round(row["saved_amount"] / row["target_amount"] * 100, 1) if row["target_amount"] > 0 else 0

        months_left = max(1, (row["deadline"] - pd.Timestamp.now()).days / 30)
        required_monthly = remaining / months_left if months_left > 0 else remaining

        on_track = row["monthly_contribution"] >= required_monthly * 0.9  # 90% threshold

        goals.append({
            "name": row["goal_name"],
            "target": round(row["target_amount"], 2),
            "saved": round(row["saved_amount"], 2),
            "monthly_contribution": round(row["monthly_contribution"], 2),
            "required_monthly": round(required_monthly, 2),
            "progress_pct": progress_pct,
            "on_track": on_track,
            "deadline": row["deadline"].strftime("%Y-%m-%d"),
        })

    return goals


def _generate_alerts(virtual_salary, predicted_income, expense_analysis,
                     surplus_deficit, profile_type, debt_payments) -> list:
    """Generate smart financial alerts."""
    alerts = []

    # Alert: Expenses exceed virtual salary
    if surplus_deficit < 0:
        alerts.append(
            f"⚠️ Your monthly expenses ({expense_analysis['monthly_avg']:,.0f}) "
            f"exceed the recommended virtual salary ({virtual_salary:,.0f}) by {abs(surplus_deficit):,.0f}. "
            f"You should consider reducing non-essential spending."
        )

    # Alert: Needs exceed 50%
    if expense_analysis["needs_pct"] > 60:
        alerts.append(
            f"📊 Essential needs account for {expense_analysis['needs_pct']}% of your expenses. "
            f"The target is 50%. Try reducing costs like rent or transportation."
        )

    # Alert: No savings buffer
    if surplus_deficit < virtual_salary * 0.10 and surplus_deficit >= 0:
        alerts.append(
            "💡 Your monthly surplus is very low. Try to save at least 10% of your salary as an emergency buffer."
        )

    # Alert: High debt burden
    if debt_payments > virtual_salary * 0.30:
        alerts.append(
            f"🔴 Debt payments ({debt_payments:,.0f}) take up more than 30% of your salary. "
            f"This may cause significant financial pressure."
        )

    # Alert: Profile-specific advice
    if profile_type == "struggling":
        alerts.append(
            "💪 Your income is currently in a building phase. Focus on diversifying your income sources and client base."
        )
    elif profile_type == "inconsistent":
        alerts.append(
            "📈 Your income is fluctuating. Using a fixed virtual salary will help you manage your expenses more effectively."
        )

    # Alert: Spending trend warnings
    for trend in expense_analysis.get("spending_trends", [])[:2]:
        if trend["trend"] == "increasing" and trend["change_pct"] > 25:
            alerts.append(
                f"📍 Spending on {trend['category']} has increased by {trend['change_pct']:.0f}% over the last 3 months. Review your spending patterns."
            )

    return alerts


if __name__ == "__main__":
    result = get_budget_plan("user_0001")
    print(f"Profile: {result['profile_type']}")
    print(f"Predicted Income: {result['predicted_income']:,.2f}")
    print(f"Virtual Salary: {result['virtual_salary']:,.2f} (multiplier: {result['multiplier']})")
    print(f"Surplus/Deficit: {result['surplus_deficit']:+,.2f}")
    print(f"\nBudget:")
    print(f"  Needs (50%): {result['budget']['needs']['amount']:,.2f}")
    print(f"  Wants (30%): {result['budget']['wants']['amount']:,.2f}")
    print(f"  Savings: {result['budget']['savings']['amount']:,.2f}")
    print(f"  Debt: {result['budget']['debt_payments']['amount']:,.2f}")
    print(f"\nAlerts:")
    for a in result["alerts"]:
        print(f"  {a}")
    print(f"\nSavings Goals:")
    for g in result["savings_goals"]:
        print(f"  {g['name']}: {g['progress_pct']}% ({g['saved']:,.0f}/{g['target']:,.0f})")
