"""
WellFinanced — Payment Planner (Feature 3 Helper)
Generates detailed, month-by-month payment timelines with payoff dates
and visualisation-ready data for each debt.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from dateutil.relativedelta import relativedelta

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.data_loader import get_user_debts


def generate_detailed_plan(user_id: str, monthly_budget: float = None,
                           strategy: str = "hybrid") -> dict:
    """
    Generate a detailed month-by-month payment plan with payoff projections.

    Unlike debt_prioritizer (which compares strategies), this module focuses
    on producing a granular payment timeline that the frontend can render
    as a calendar / Gantt chart.

    Args:
        user_id: User identifier
        monthly_budget: Total budget available for debt payments per month.
                       If None, uses sum of all minimum payments × 1.1
        strategy: "avalanche" | "snowball" | "hybrid"

    Returns:
        dict: {
            debts: [{
                name, remaining, interest_rate, monthly_payment,
                payoff_month, payoff_date, total_interest_paid,
                balance_over_time: [{month, balance}]
            }],
            timeline: [{
                month_num, date, payments: [{debt, amount, remaining}],
                total_payment, cumulative_paid
            }],
            summary: {
                total_months, total_paid, total_interest,
                debt_free_date, monthly_budget, interest_saved_vs_minimum
            }
        }
    """
    debts_df = get_user_debts(user_id)

    if debts_df.empty:
        return {
            "debts": [],
            "timeline": [],
            "summary": {
                "total_months": 0, "total_paid": 0, "total_interest": 0,
                "debt_free_date": None, "monthly_budget": 0,
                "interest_saved_vs_minimum": 0
            }
        }

    debts_df = debts_df.copy()

    # Default budget: 110% of total minimums (small extra for faster payoff)
    if monthly_budget is None:
        monthly_budget = debts_df["monthly_payment"].sum() * 1.1

    # Sort by strategy
    if strategy == "avalanche":
        debts_df = debts_df.sort_values("interest_rate", ascending=False)
    elif strategy == "snowball":
        debts_df = debts_df.sort_values("remaining_amount", ascending=True)
    else:  # hybrid — by priority then interest
        debts_df = debts_df.sort_values(
            ["priority", "interest_rate"], ascending=[True, False]
        )

    # Build debt trackers
    trackers = []
    for _, row in debts_df.iterrows():
        trackers.append({
            "name": row["debt_name"],
            "balance": row["remaining_amount"],
            "original_balance": row["remaining_amount"],
            "rate_monthly": row["interest_rate"] / 100 / 12,
            "min_payment": row["monthly_payment"],
            "interest_rate": row["interest_rate"],
            "total_interest": 0.0,
            "payoff_month": None,
            "balance_history": [],
        })

    timeline = []
    month_num = 0
    start_date = datetime.now().replace(day=1)
    max_months = 120
    cumulative_paid = 0

    while any(t["balance"] > 0.01 for t in trackers) and month_num < max_months:
        month_num += 1
        current_date = start_date + relativedelta(months=month_num)
        remaining_budget = monthly_budget
        month_payments = []

        # Apply interest to all active debts
        for t in trackers:
            if t["balance"] <= 0.01:
                continue
            interest = t["balance"] * t["rate_monthly"]
            t["balance"] += interest
            t["total_interest"] += interest

        # Pay minimum on all active debts first
        for t in trackers:
            if t["balance"] <= 0.01:
                continue
            payment = min(t["min_payment"], t["balance"], remaining_budget)
            t["balance"] -= payment
            remaining_budget -= payment
            month_payments.append({
                "debt": t["name"],
                "amount": round(payment, 2),
                "remaining": round(t["balance"], 2),
            })

        # Throw extra at priority debt (first active in sorted order)
        if remaining_budget > 0.01:
            for t in trackers:
                if t["balance"] <= 0.01:
                    continue
                extra = min(remaining_budget, t["balance"])
                t["balance"] -= extra
                remaining_budget -= extra
                # Update payment entry
                for mp in month_payments:
                    if mp["debt"] == t["name"]:
                        mp["amount"] = round(mp["amount"] + extra, 2)
                        mp["remaining"] = round(t["balance"], 2)
                        break
                if remaining_budget <= 0.01:
                    break

        # Record balance snapshots & check payoff
        for t in trackers:
            t["balance_history"].append({
                "month": month_num,
                "balance": round(max(0, t["balance"]), 2),
            })
            if t["balance"] <= 0.01 and t["payoff_month"] is None:
                t["payoff_month"] = month_num
                t["balance"] = 0

        total_payment = sum(mp["amount"] for mp in month_payments)
        cumulative_paid += total_payment

        timeline.append({
            "month_num": month_num,
            "date": current_date.strftime("%Y-%m"),
            "payments": month_payments,
            "total_payment": round(total_payment, 2),
            "cumulative_paid": round(cumulative_paid, 2),
        })

    # ------- Compute minimum-only baseline for comparison -------
    min_only_interest = _simulate_minimum_only(debts_df, max_months)

    # Build output
    debts_output = []
    for t in trackers:
        payoff_date = None
        if t["payoff_month"]:
            payoff_date = (start_date + relativedelta(months=t["payoff_month"])).strftime("%Y-%m")
        debts_output.append({
            "name": t["name"],
            "remaining": round(t["original_balance"], 2),
            "interest_rate": t["interest_rate"],
            "monthly_payment": round(t["min_payment"], 2),
            "payoff_month": t["payoff_month"],
            "payoff_date": payoff_date,
            "total_interest_paid": round(t["total_interest"], 2),
            "balance_over_time": t["balance_history"],
        })

    # Trim timeline for API readability (keep first 12 + last)
    timeline_trimmed = timeline
    if len(timeline) > 14:
        timeline_trimmed = timeline[:12] + [{"...": f"{len(timeline) - 13} months omitted"}] + [timeline[-1]]

    debt_free_date = (start_date + relativedelta(months=month_num)).strftime("%Y-%m")

    return {
        "debts": debts_output,
        "timeline": timeline_trimmed,
        "summary": {
            "total_months": month_num,
            "total_paid": round(cumulative_paid, 2),
            "total_interest": round(sum(t["total_interest"] for t in trackers), 2),
            "debt_free_date": debt_free_date,
            "monthly_budget": round(monthly_budget, 2),
            "interest_saved_vs_minimum": round(min_only_interest - sum(t["total_interest"] for t in trackers), 2),
        }
    }


def _simulate_minimum_only(debts_df: pd.DataFrame, max_months: int) -> float:
    """Simulate paying only minimums to find total interest baseline."""
    total_interest = 0
    balances = debts_df["remaining_amount"].values.copy()
    rates = (debts_df["interest_rate"].values / 100 / 12)
    mins = debts_df["monthly_payment"].values.copy()

    for _ in range(max_months):
        if all(b <= 0.01 for b in balances):
            break
        for i in range(len(balances)):
            if balances[i] <= 0.01:
                continue
            interest = balances[i] * rates[i]
            balances[i] += interest
            total_interest += interest
            payment = min(mins[i], balances[i])
            balances[i] -= payment

    return total_interest


if __name__ == "__main__":
    result = generate_detailed_plan("user_0001", strategy="hybrid")
    s = result["summary"]
    print(f"Strategy: hybrid")
    print(f"Debt-free in: {s['total_months']} months ({s['debt_free_date']})")
    print(f"Total paid: {s['total_paid']:,.2f}")
    print(f"Total interest: {s['total_interest']:,.2f}")
    print(f"Interest saved vs minimum-only: {s['interest_saved_vs_minimum']:,.2f}")
    print(f"\nPer-debt payoff:")
    for d in result["debts"]:
        print(f"  {d['name']}: payoff {d['payoff_date']} "
              f"(interest: {d['total_interest_paid']:,.2f})")
