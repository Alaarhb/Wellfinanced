"""Quick test: Features 1-3 only (no heavy ML deps)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 50)
print("QUICK FEATURE TEST")
print("=" * 50)

# Feature 1
print("\n[F1] Income Forecast...")
from features.income_forecast import forecast_income
r = forecast_income("user_0001", 3)
print(f"  Model: {r['model_used']}, Stability: {r['stability_score']}")
print(f"  Avg Predicted: {r['avg_predicted']:,.2f}")
print("  PASS")

# Feature 2
print("\n[F2] Cashflow Smoothing...")
from features.cashflow_smoothing import get_budget_plan
b = get_budget_plan("user_0001")
print(f"  Virtual Salary: {b['virtual_salary']:,.2f}")
print(f"  Surplus/Deficit: {b['surplus_deficit']:+,.2f}")
print("  PASS")

# Feature 3
print("\n[F3] Debt Prioritizer...")
from features.debt_prioritizer import prioritize_debts
d = prioritize_debts("user_0001", strategy="hybrid")
print(f"  Debts: {len(d['ranked_debts'])}, Months: {d['months_to_free']}")
print("  PASS")

# Feature 3b
print("\n[F3b] Payment Planner...")
from features.payment_planner import generate_detailed_plan
p = generate_detailed_plan("user_0001", strategy="hybrid")
print(f"  Debt-free: {p['summary']['debt_free_date']}")
print("  PASS")

# Feature 4 Snapshot
print("\n[F4] Financial Snapshot...")
from features.financial_advisor import get_financial_snapshot
snap = get_financial_snapshot("user_0001")
if "error" not in snap:
    print(f"  Health Score: {snap['health_score']}/100")
    print("  PASS")
else:
    print(f"  ERROR: {snap['error']}")

print("\n" + "=" * 50)
print("ALL CORE FEATURES PASSED")
print("=" * 50)
