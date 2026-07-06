"""
WellFinanced — End-to-end test
Tests all 4 AI features with a sample user.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("WELLFINANCED AI — END-TO-END TEST")
print("=" * 60)

TEST_USER = "user_0001"

# ──────────────────────────────────────────────
# Feature 1: Income Forecasting
# ──────────────────────────────────────────────
print("\n[Feature 1] Income Forecasting")
print("-" * 40)
from features.income_forecast import forecast_income
f1 = forecast_income(TEST_USER, months_ahead=3)
print(f"  Model: {f1['model_used']}")
print(f"  Stability Score: {f1['stability_score']}/100")
print(f"  Platform Diversity: {f1['platform_diversity']}")
print(f"  Avg Predicted: {f1['avg_predicted']:,.2f}")
for p in f1["predicted_income"]:
    print(f"    {p['month']}: {p['amount']:,.2f} ({p['lower_bound']:,.2f} - {p['upper_bound']:,.2f})")
print("  ✅ Feature 1 PASSED")

# ──────────────────────────────────────────────
# Feature 2: Cashflow Smoothing
# ──────────────────────────────────────────────
print("\n[Feature 2] Cashflow Smoothing")
print("-" * 40)
from features.cashflow_smoothing import get_budget_plan
f2 = get_budget_plan(TEST_USER)
print(f"  Profile: {f2['profile_type']}")
print(f"  Predicted Income: {f2['predicted_income']:,.2f}")
print(f"  Virtual Salary: {f2['virtual_salary']:,.2f} (x{f2['multiplier']})")
print(f"  Needs: {f2['budget']['needs']['amount']:,.2f}")
print(f"  Wants: {f2['budget']['wants']['amount']:,.2f}")
print(f"  Savings: {f2['budget']['savings']['amount']:,.2f}")
print(f"  Debt Payments: {f2['budget']['debt_payments']['amount']:,.2f}")
print(f"  Surplus/Deficit: {f2['surplus_deficit']:+,.2f}")
print(f"  Alerts: {len(f2['alerts'])}")
for a in f2["alerts"]:
    print(f"    {a}")
print(f"  Savings Goals: {len(f2['savings_goals'])}")
for g in f2["savings_goals"]:
    print(f"    {g['name']}: {g['progress_pct']}% ({'✅' if g['on_track'] else '⚠️'})")
print("  ✅ Feature 2 PASSED")

# ──────────────────────────────────────────────
# Feature 3: Debt Prioritization
# ──────────────────────────────────────────────
print("\n[Feature 3] Debt Prioritization")
print("-" * 40)
from features.debt_prioritizer import prioritize_debts
f3 = prioritize_debts(TEST_USER, strategy="hybrid")
print(f"  Strategy: {f3['strategy']}")
print(f"  Months to Debt-Free: {f3['months_to_free']}")
print(f"  Total Interest: {f3['total_interest']:,.2f}")
print(f"  Total Paid: {f3['total_paid']:,.2f}")
for d in f3["ranked_debts"]:
    print(f"    #{d['rank']} {d['debt_name']}: {d['remaining_amount']:,.2f} @ {d['interest_rate']}%")
print("  Strategy Comparison:")
for c in f3["strategy_comparison"]:
    print(f"    {c['strategy']}: {c['months']}m, interest={c['interest']:,.2f}")
print("  ✅ Feature 3 PASSED")

# ──────────────────────────────────────────────
# Feature 3b: Payment Planner
# ──────────────────────────────────────────────
print("\n[Feature 3b] Payment Planner")
print("-" * 40)
from features.payment_planner import generate_detailed_plan
f3b = generate_detailed_plan(TEST_USER, strategy="hybrid")
s = f3b["summary"]
print(f"  Debt-Free Date: {s['debt_free_date']}")
print(f"  Total Months: {s['total_months']}")
print(f"  Total Paid: {s['total_paid']:,.2f}")
print(f"  Total Interest: {s['total_interest']:,.2f}")
print(f"  Interest Saved vs Minimum: {s['interest_saved_vs_minimum']:,.2f}")
for d in f3b["debts"]:
    print(f"    {d['name']}: payoff {d['payoff_date']} (interest: {d['total_interest_paid']:,.2f})")
print("  ✅ Feature 3b PASSED")

# ──────────────────────────────────────────────
# Feature 4: Financial Advisor (snapshot only — no LLM)
# ──────────────────────────────────────────────
print("\n[Feature 4] Financial Advisor — Snapshot")
print("-" * 40)
from features.financial_advisor import get_financial_snapshot
f4 = get_financial_snapshot(TEST_USER)
if "error" not in f4:
    print(f"  Profile: {f4['profile']['profile_type']}")
    print(f"  Health Score: {f4['health_score']}/100")
    print(f"  Income forecast available: {'Yes' if f4['income_forecast']['predicted_income'] else 'No'}")
    print(f"  Budget plan available: {'Yes' if f4['budget_plan']['virtual_salary'] > 0 else 'No'}")
    print(f"  Debts analyzed: {len(f4['debt_analysis']['ranked_debts'])}")
    print("  ✅ Feature 4 Snapshot PASSED")
else:
    print(f"  ❌ Error: {f4['error']}")

# ──────────────────────────────────────────────
# Feature 4: RAG (Chat requires GEMINI_API_KEY)
# ──────────────────────────────────────────────
print("\n[Feature 4] RAG Knowledge Base")
print("-" * 40)
try:
    from utils.rag_engine import build_knowledge_base, search_knowledge
    result = build_knowledge_base(force_rebuild=True)
    print(f"  KB Status: {result['status']}")
    print(f"  Documents: {result['documents_processed']}")
    print(f"  Chunks: {result['total_chunks']}")
    
    results = search_knowledge("How to budget as a freelancer?", n_results=2)
    for r in results:
        print(f"    [{r['source']}] score={r['relevance_score']:.3f}: {r['content'][:60]}...")
    print("  ✅ RAG Engine PASSED")
except ImportError as e:
    print(f"  ⚠️ RAG dependencies not installed: {e}")
    print("  Install with: pip install chromadb sentence-transformers")

# ──────────────────────────────────────────────
# Chat test (optional)
# ──────────────────────────────────────────────
api_key = os.environ.get("GEMINI_API_KEY")
if api_key:
    print("\n[Feature 4] Chat Test")
    print("-" * 40)
    from features.financial_advisor import chat
    result = chat(TEST_USER, "هل أقدر أشتري لابتوب بـ 15000 جنيه الشهر ده؟")
    if result["error"]:
        print(f"  ❌ Error: {result['error']}")
    else:
        print(f"  Response: {result['response'][:200]}...")
        print(f"  Sources: {result['sources']}")
        print("  ✅ Chat PASSED")
else:
    print("\n[Feature 4] Chat Test — SKIPPED (no GEMINI_API_KEY)")
    print("  Set with: $env:GEMINI_API_KEY='your-key'")

print("\n" + "=" * 60)
print("ALL TESTS COMPLETE")
print("=" * 60)
