"""
WellFinanced — Data Loader Utility
Handles loading, cleaning, and preprocessing all CSV datasets.
"""

import pandas as pd
import numpy as np
import os

# Default data directory (relative to project root)
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def _resolve_path(filename: str) -> str:
    """Resolve file path — check data/ folder first, then project root."""
    data_path = os.path.join(DATA_DIR, filename)
    if os.path.exists(data_path):
        return data_path
    root_path = os.path.join(os.path.dirname(DATA_DIR), filename)
    if os.path.exists(root_path):
        return root_path
    raise FileNotFoundError(f"Could not find {filename} in {DATA_DIR} or project root.")


# ──────────────────────────────────────────────
# Raw Loaders
# ──────────────────────────────────────────────

def load_users() -> pd.DataFrame:
    """Load users dataset."""
    df = pd.read_csv(_resolve_path("users.csv"))
    df["joined_at"] = pd.to_datetime(df["joined_at"])
    return df


def load_income() -> pd.DataFrame:
    """Load income dataset with date parsing."""
    df = pd.read_csv(_resolve_path("income.csv"))
    df["received_at"] = pd.to_datetime(df["received_at"])
    df["month"] = pd.to_datetime(df["month"])
    return df


def load_expenses() -> pd.DataFrame:
    """Load expenses dataset."""
    df = pd.read_csv(_resolve_path("expenses.csv"))
    df["expense_date"] = pd.to_datetime(df["expense_date"])
    df["month"] = df["expense_date"].dt.to_period("M").dt.to_timestamp()
    return df


def load_debts() -> pd.DataFrame:
    """Load debts dataset."""
    df = pd.read_csv(_resolve_path("debts.csv"))
    df["due_date"] = pd.to_datetime(df["due_date"])
    return df


def load_savings_goals() -> pd.DataFrame:
    """Load savings goals dataset."""
    df = pd.read_csv(_resolve_path("savings_goals.csv"))
    df["deadline"] = pd.to_datetime(df["deadline"])
    return df


# ──────────────────────────────────────────────
# Aggregated / Preprocessed Data
# ──────────────────────────────────────────────

def get_monthly_income(user_id: str) -> pd.DataFrame:
    """
    Get monthly aggregated income for a specific user.
    Returns DataFrame with columns: [month, total_income, num_projects, num_platforms]
    Missing months are filled with 0.
    """
    income = load_income()
    user_income = income[income["user_id"] == user_id].copy()

    if user_income.empty:
        return pd.DataFrame(columns=["month", "total_income", "num_projects", "num_platforms"])

    monthly = user_income.groupby("month").agg(
        total_income=("amount", "sum"),
        num_projects=("amount", "count"),
        num_platforms=("platform", "nunique"),
    ).reset_index()

    # Fill missing months with 0
    full_range = pd.date_range(
        start=monthly["month"].min(),
        end=monthly["month"].max(),
        freq="MS"  # Month Start
    )
    monthly = monthly.set_index("month").reindex(full_range, fill_value=0).reset_index()
    monthly.rename(columns={"index": "month"}, inplace=True)

    # Cap outliers at 3× median (as per implementation plan)
    non_zero = monthly[monthly["total_income"] > 0]["total_income"]
    if len(non_zero) > 0:
        median_income = non_zero.median()
        cap = median_income * 3
        monthly["total_income"] = monthly["total_income"].clip(upper=cap)

    return monthly


def get_monthly_expenses(user_id: str) -> pd.DataFrame:
    """
    Get monthly aggregated expenses for a specific user.
    Returns DataFrame with columns: [month, total_expenses, recurring_total, non_recurring_total]
    """
    expenses = load_expenses()
    user_exp = expenses[expenses["user_id"] == user_id].copy()

    if user_exp.empty:
        return pd.DataFrame(columns=["month", "total_expenses", "recurring_total", "non_recurring_total"])

    monthly = user_exp.groupby("month").agg(
        total_expenses=("amount", "sum"),
        recurring_total=("amount", lambda x: x[user_exp.loc[x.index, "is_recurring"] == True].sum()),
        non_recurring_total=("amount", lambda x: x[user_exp.loc[x.index, "is_recurring"] == False].sum()),
    ).reset_index()

    return monthly


def get_expense_breakdown(user_id: str) -> pd.DataFrame:
    """
    Get expense breakdown by category for a user.
    Returns DataFrame with columns: [category, total, avg_monthly, is_recurring, count]
    """
    expenses = load_expenses()
    user_exp = expenses[expenses["user_id"] == user_id].copy()

    if user_exp.empty:
        return pd.DataFrame(columns=["category", "total", "avg_monthly", "is_recurring", "count"])

    n_months = user_exp["month"].nunique()
    if n_months == 0:
        n_months = 1

    breakdown = user_exp.groupby("category").agg(
        total=("amount", "sum"),
        count=("amount", "count"),
        is_recurring=("is_recurring", "first"),
    ).reset_index()

    breakdown["avg_monthly"] = breakdown["total"] / n_months
    return breakdown.sort_values("total", ascending=False)


def get_user_debts(user_id: str) -> pd.DataFrame:
    """Get all debts for a specific user, sorted by priority."""
    debts = load_debts()
    user_debts = debts[debts["user_id"] == user_id].sort_values("priority")
    return user_debts


def get_user_savings(user_id: str) -> pd.DataFrame:
    """Get all savings goals for a specific user."""
    savings = load_savings_goals()
    return savings[savings["user_id"] == user_id]


def get_user_profile(user_id: str) -> dict:
    """Get complete user profile as a dictionary."""
    users = load_users()
    user = users[users["user_id"] == user_id]
    if user.empty:
        raise ValueError(f"User {user_id} not found.")
    return user.iloc[0].to_dict()


def get_income_stats(user_id: str) -> dict:
    """Get summary statistics for a user's income."""
    monthly = get_monthly_income(user_id)
    if monthly.empty or monthly["total_income"].sum() == 0:
        return {"avg": 0, "median": 0, "std": 0, "min": 0, "max": 0, "cv": 0, "months": 0}

    income_vals = monthly[monthly["total_income"] > 0]["total_income"]
    avg = income_vals.mean()
    return {
        "avg": round(avg, 2),
        "median": round(income_vals.median(), 2),
        "std": round(income_vals.std(), 2),
        "min": round(income_vals.min(), 2),
        "max": round(income_vals.max(), 2),
        "cv": round(income_vals.std() / avg, 2) if avg > 0 else 0,  # Coefficient of variation
        "months": len(monthly),
    }


def get_expense_stats(user_id: str) -> dict:
    """Get summary statistics for a user's expenses."""
    monthly = get_monthly_expenses(user_id)
    if monthly.empty:
        return {"avg": 0, "recurring_avg": 0, "non_recurring_avg": 0, "months": 0}

    return {
        "avg": round(monthly["total_expenses"].mean(), 2),
        "recurring_avg": round(monthly["recurring_total"].mean(), 2),
        "non_recurring_avg": round(monthly["non_recurring_total"].mean(), 2),
        "months": len(monthly),
    }


# ──────────────────────────────────────────────
# Schema-Aligned Loaders (Account, Counterparty, Asset)
# ──────────────────────────────────────────────

def load_accounts() -> pd.DataFrame:
    """Load accounts dataset — maps to schema's Account entity."""
    df = pd.read_csv(_resolve_path("accounts.csv"))
    return df


def load_assets() -> pd.DataFrame:
    """Load assets dataset — maps to schema's Asset entity."""
    df = pd.read_csv(_resolve_path("assets.csv"))
    return df


def load_counterparties() -> pd.DataFrame:
    """Load counterparties dataset — maps to schema's Counterparty entity."""
    df = pd.read_csv(_resolve_path("counterparties.csv"))
    return df


# ──────────────────────────────────────────────
# Schema-Aware Context Builders
# ──────────────────────────────────────────────

def get_debt_info(user_id: str) -> dict:
    """Get debt summary matching schema's FinancialFlow + Installment entities."""
    debts = get_user_debts(user_id)
    if debts.empty:
        return {"total_debt": 0, "num_debts": 0, "debts": [], "monthly_obligations": 0}

    total = debts["remaining_amount"].sum()
    monthly = debts["monthly_payment"].sum()
    debt_list = []
    for _, d in debts.iterrows():
        debt_list.append({
            "name": d["debt_name"],
            "remaining": round(d["remaining_amount"], 2),
            "interest_rate": d["interest_rate"],
            "monthly_payment": round(d["monthly_payment"], 2),
            "due_date": str(d["due_date"].date()) if hasattr(d["due_date"], "date") else str(d["due_date"]),
            "priority": d["priority"],
        })
    return {
        "total_debt": round(total, 2),
        "num_debts": len(debts),
        "debts": debt_list,
        "monthly_obligations": round(monthly, 2),
    }


def get_savings_info(user_id: str) -> dict:
    """Get savings goals summary — maps to schema's saving_goal FinancialFlowCategory."""
    savings = get_user_savings(user_id)
    if savings.empty:
        return {"num_goals": 0, "total_target": 0, "total_saved": 0, "goals": [], "overall_progress_pct": 0}

    total_target = savings["target_amount"].sum()
    total_saved = savings["saved_amount"].sum()
    overall_pct = round(total_saved / total_target * 100, 1) if total_target > 0 else 0

    goals = []
    for _, g in savings.iterrows():
        progress = round(g["saved_amount"] / g["target_amount"] * 100, 1) if g["target_amount"] > 0 else 0
        remaining = g["target_amount"] - g["saved_amount"]
        months_left = max(1, (g["deadline"] - pd.Timestamp.now()).days / 30)
        required_monthly = remaining / months_left if months_left > 0 else remaining

        goals.append({
            "name": g["goal_name"],
            "target": round(g["target_amount"], 2),
            "saved": round(g["saved_amount"], 2),
            "progress_pct": progress,
            "monthly_contribution": round(g["monthly_contribution"], 2),
            "required_monthly": round(required_monthly, 2),
            "on_track": g["monthly_contribution"] >= required_monthly * 0.9,
            "deadline": g["deadline"].strftime("%Y-%m-%d"),
        })

    return {
        "num_goals": len(savings),
        "total_target": round(total_target, 2),
        "total_saved": round(total_saved, 2),
        "goals": goals,
        "overall_progress_pct": overall_pct,
    }


def get_account_summary(user_id: str) -> dict:
    """Summarize account balances — maps to schema's Account entity."""
    try:
        accounts = load_accounts()
    except FileNotFoundError:
        return {"total_balance": 0, "num_accounts": 0, "by_category": {}, "accounts": []}

    user_accounts = accounts[accounts["user_id"] == user_id]
    if user_accounts.empty:
        return {"total_balance": 0, "num_accounts": 0, "by_category": {}, "accounts": []}

    total = user_accounts["current_balance"].sum()

    # Group by category
    by_category = {}
    for cat, group in user_accounts.groupby("category"):
        by_category[cat] = {
            "count": len(group),
            "total_balance": round(group["current_balance"].sum(), 2),
        }

    account_list = []
    for _, acc in user_accounts.iterrows():
        account_list.append({
            "label": acc["label"],
            "institution": acc.get("institution", ""),
            "category": acc["category"],
            "balance": round(acc["current_balance"], 2),
            "currency": acc.get("currency", "EGP"),
            "status": acc.get("status", "active"),
        })

    return {
        "total_balance": round(total, 2),
        "num_accounts": len(user_accounts),
        "by_category": by_category,
        "accounts": account_list,
    }
