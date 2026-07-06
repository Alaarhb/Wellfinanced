"""
WellFinanced — Feature 4: Behavioral Financial Advisor (RAG + LLM)
AI chatbot that answers financial questions using the user's real data
combined with a curated knowledge base via RAG.
"""

import os
import sys
import warnings
from dotenv import load_dotenv

load_dotenv(override=True) 

# Fix TF/Keras 3 compatibility before any imports
os.environ["TF_USE_LEGACY_KERAS"] = "1"
os.environ["TRANSFORMERS_NO_TF"] = "1"

warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.data_loader import (
    get_user_profile, get_income_stats, get_expense_stats,
    get_debt_info, get_savings_info, get_account_summary,
)
from utils.rag_engine import get_relevant_context, build_knowledge_base
from utils.prompts import (
    SYSTEM_PROMPT,
    build_user_context,
    format_chat_prompt,
)
from features.income_forecast import forecast_income
from features.cashflow_smoothing import get_budget_plan
from features.debt_prioritizer import prioritize_debts


# ──────────────────────────────────────────────
# Context Builder (Schema-Aligned)
# ──────────────────────────────────────────────

def build_context(user_id: str) -> dict:
    """
    Gather all schema-aligned financial data for a user.
    Maps to the plan's Step 2: build comprehensive context.

    Returns:
        dict with keys: income_summary, expense_summary, debt_summary,
        savings_summary, account_summary, forecast, budget
    """
    return {
        "income_summary": get_income_stats(user_id),
        "expense_summary": get_expense_stats(user_id),
        "debt_summary": get_debt_info(user_id),
        "savings_summary": get_savings_info(user_id),
        "account_summary": get_account_summary(user_id),
        "forecast": forecast_income(user_id, months_ahead=3),
        "budget": get_budget_plan(user_id),
    }


# ──────────────────────────────────────────────
# Specialized Analysis Functions
# ──────────────────────────────────────────────

def can_i_afford(user_id: str, item_cost: float) -> dict:
    """
    Check if a user can afford a specific purchase.
    Uses surplus analysis and the affordability framework from knowledge base.

    Args:
        user_id: User identifier
        item_cost: Cost of the item in EGP

    Returns:
        dict with affordability analysis
    """
    budget = get_budget_plan(user_id)
    account_sum = get_account_summary(user_id)
    debt_info = get_debt_info(user_id)

    surplus = budget.get("surplus_deficit", 0)
    virtual_salary = budget.get("virtual_salary", 0)
    total_balance = account_sum.get("total_balance", 0)

    # Emergency fund threshold: 2 months of expenses
    avg_expenses = budget.get("expense_summary", {}).get("monthly_avg", 0)
    emergency_fund = avg_expenses * 2
    available_cash = max(0, total_balance - emergency_fund)

    # Determine affordability
    if item_cost <= surplus:
        verdict = "affordable"
        method = "You can buy this from your monthly surplus."
        months_to_save = 0
    elif item_cost <= available_cash:
        verdict = "affordable_from_savings"
        method = "You can afford this from your available balance (after emergency fund)."
        months_to_save = 0
    elif surplus > 0:
        verdict = "save_first"
        months_to_save = int(item_cost / surplus) + 1
        method = f"Save for {months_to_save} month(s) from your monthly surplus."
    else:
        verdict = "not_affordable"
        months_to_save = -1
        method = "You currently have a deficit. Focus on reducing expenses first."

    return {
        "item_cost": item_cost,
        "verdict": verdict,
        "method": method,
        "months_to_save": months_to_save,
        "monthly_surplus": round(surplus, 2),
        "available_cash": round(available_cash, 2),
        "total_balance": round(total_balance, 2),
        "emergency_fund_needed": round(emergency_fund, 2),
        "debt_obligations": round(debt_info.get("monthly_obligations", 0), 2),
    }


def installment_impact(user_id: str, monthly_amount: float, months: int) -> dict:
    """
    Simulate the impact of adding a new installment.

    Args:
        user_id: User identifier
        monthly_amount: Monthly installment payment in EGP
        months: Number of installment months

    Returns:
        dict with impact analysis
    """
    budget = get_budget_plan(user_id)
    debt_info = get_debt_info(user_id)
    income_stats = get_income_stats(user_id)

    surplus = budget.get("surplus_deficit", 0)
    virtual_salary = budget.get("virtual_salary", 0)
    avg_income = income_stats.get("avg", 0)
    current_obligations = debt_info.get("monthly_obligations", 0)

    # New financial state after adding installment
    new_surplus = surplus - monthly_amount
    new_total_obligations = current_obligations + monthly_amount
    new_debt_ratio = (new_total_obligations / avg_income * 100) if avg_income > 0 else 100
    total_cost = monthly_amount * months

    # Affordability checks (from installment_guide.md rules)
    surplus_ok = surplus >= monthly_amount * 1.5
    debt_ratio_ok = new_debt_ratio < 35
    savings_ok = new_surplus > (avg_income * 0.10)  # Still saving 10%

    affordable = surplus_ok and debt_ratio_ok
    risk_level = "low" if (surplus_ok and debt_ratio_ok and savings_ok) else \
                 "medium" if (surplus_ok or debt_ratio_ok) else "high"

    warnings_list = []
    if not surplus_ok:
        warnings_list.append(f"Monthly surplus ({surplus:,.0f}) should be >= 1.5× installment ({monthly_amount * 1.5:,.0f})")
    if not debt_ratio_ok:
        warnings_list.append(f"New debt-to-income ratio ({new_debt_ratio:.1f}%) exceeds 35% threshold")
    if not savings_ok:
        warnings_list.append("You won't be able to maintain 10% savings after this installment")
    if debt_info.get("num_debts", 0) >= 2:
        warnings_list.append(f"You already have {debt_info['num_debts']} active debts")

    return {
        "monthly_amount": monthly_amount,
        "months": months,
        "total_cost": round(total_cost, 2),
        "affordable": affordable,
        "risk_level": risk_level,
        "current_surplus": round(surplus, 2),
        "new_surplus": round(new_surplus, 2),
        "current_debt_ratio": round((current_obligations / avg_income * 100) if avg_income > 0 else 0, 1),
        "new_debt_ratio": round(new_debt_ratio, 1),
        "warnings": warnings_list,
    }


def savings_plan(user_id: str, goal_name: str, target_amount: float, months: int) -> dict:
    """
    Create a savings plan for a specific goal.

    Args:
        user_id: User identifier
        goal_name: Name of the savings goal
        target_amount: Target amount in EGP
        months: Number of months to save

    Returns:
        dict with savings plan details
    """
    budget = get_budget_plan(user_id)
    income_stats = get_income_stats(user_id)

    surplus = budget.get("surplus_deficit", 0)
    avg_income = income_stats.get("avg", 0)

    monthly_needed = target_amount / months if months > 0 else target_amount
    # Freelancer adjustment: add 20% safety margin
    adjusted_monthly = monthly_needed * 1.2

    feasible = surplus >= monthly_needed
    comfortable = surplus >= adjusted_monthly

    if comfortable:
        verdict = "comfortable"
        recommendation = f"Save {monthly_needed:,.0f}/month. You'll have buffer for low-income months."
    elif feasible:
        verdict = "tight"
        recommendation = f"Possible but tight. Consider extending to {int(target_amount / (surplus * 0.8)) + 1} months."
    else:
        if surplus > 0:
            realistic_months = int(target_amount / surplus) + 1
            verdict = "extend"
            recommendation = f"At your current surplus, you'd need ~{realistic_months} months instead of {months}."
        else:
            verdict = "not_feasible"
            recommendation = "You currently have a deficit. Focus on increasing income or reducing expenses first."

    return {
        "goal_name": goal_name,
        "target_amount": round(target_amount, 2),
        "months": months,
        "monthly_needed": round(monthly_needed, 2),
        "adjusted_monthly": round(adjusted_monthly, 2),
        "current_surplus": round(surplus, 2),
        "verdict": verdict,
        "recommendation": recommendation,
        "savings_pct_of_income": round((monthly_needed / avg_income * 100) if avg_income > 0 else 0, 1),
    }


def which_debt_first(user_id: str) -> dict:
    """
    Wraps Feature 3 output into an advisor-friendly format.
    Tells the user which debt to prioritize and why.

    Returns:
        dict with prioritized debt recommendation
    """
    result = prioritize_debts(user_id, strategy="hybrid")
    ranked = result.get("ranked_debts", [])

    if not ranked:
        return {"recommendation": "You have no active debts! 🎉", "debts": []}

    top_debt = ranked[0]
    comparison = result.get("strategy_comparison", [])

    # Find best strategy
    best_strategy = min(comparison, key=lambda x: x.get("interest", float("inf"))) if comparison else {}

    return {
        "top_priority": {
            "name": top_debt.get("debt_name", top_debt.get("name", "Unknown")),
            "remaining": top_debt.get("remaining_amount", top_debt.get("remaining", 0)),
            "interest_rate": top_debt.get("interest_rate", 0),
            "urgency_score": round(top_debt.get("urgency_score", 0), 2),
        },
        "recommended_strategy": result.get("strategy", "hybrid"),
        "months_to_free": result.get("months_to_free", 0),
        "total_interest_cost": result.get("total_interest", 0),
        "strategy_comparison": comparison,
        "best_strategy_by_interest": best_strategy.get("strategy", "hybrid") if best_strategy else "hybrid",
        "all_debts": ranked,
    }


# ──────────────────────────────────────────────
# Core Chat & Helpers
# ──────────────────────────────────────────────

def _get_gemini_model():
    """
    Initialize the Gemini generative model.
    Requires GEMINI_API_KEY environment variable.
    """
    import google.generativeai as genai

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GEMINI_API_KEY environment variable not set. "
            "Get one from https://aistudio.google.com/apikey"
        )
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")
    return model


def _gather_user_context(user_id: str) -> tuple:
    """
    Gather all financial data for a user from the 3 core features + schema data.

    Returns:
        (profile, forecast, budget, debts_info, account_summary, debt_detail, savings_detail)
    """
    profile = get_user_profile(user_id)
    forecast = forecast_income(user_id, months_ahead=3)
    budget = get_budget_plan(user_id)
    debts_info = prioritize_debts(user_id, strategy="hybrid")
    account_summary = get_account_summary(user_id)
    debt_detail = get_debt_info(user_id)
    savings_detail = get_savings_info(user_id)
    return profile, forecast, budget, debts_info, account_summary, debt_detail, savings_detail


def chat(user_id: str, message: str, history: list = None) -> dict:
    """
    Main API: Chat with the Financial Advisor.

    Args:
        user_id: User identifier
        message: User's question/message
        history: Optional conversation history
                 [{"role": "user"|"assistant", "content": str}, ...]

    Returns:
        dict: {
            response: str,           # AI's answer
            sources: [str],           # Knowledge base sources used
            user_context_used: bool,  # Whether user data was included
            error: str | None,        # Error message if any
        }
    """
    if history is None:
        history = []

    try:
        # 1. Ensure knowledge base is built
        build_knowledge_base()

        # 2. Search knowledge base for relevant content
        knowledge_context = get_relevant_context(message, n_results=3)

        # 3. Gather user's financial data (now schema-aligned)
        try:
            profile, forecast, budget, debts_info, acc_sum, debt_det, sav_det = _gather_user_context(user_id)
            user_context = build_user_context(
                profile, forecast, budget, debts_info,
                account_summary=acc_sum,
                debt_detail=debt_det,
                savings_detail=sav_det,
            )
            user_context_used = True
        except Exception as e:
            user_context = f"[User data unavailable: {str(e)}]"
            user_context_used = False

        # 4. Build full context
        full_context = f"{user_context}\n\n{knowledge_context}"

        # 5. Format prompt
        prompt = format_chat_prompt(
            system=SYSTEM_PROMPT,
            context=full_context,
            history=history,
            user_message=message,
        )

        # 6. Call Gemini
        model = _get_gemini_model()
        response = model.generate_content(prompt)
        response_text = response.text

        # 7. Extract sources used
        sources = _extract_sources(knowledge_context)

        return {
            "response": response_text,
            "sources": sources,
            "user_context_used": user_context_used,
            "error": None,
        }

    except EnvironmentError as e:
        return {
            "response": "",
            "sources": [],
            "user_context_used": False,
            "error": str(e),
        }
    except Exception as e:
        return {
            "response": f"عذراً، حصل خطأ أثناء معالجة سؤالك. حاول تاني.\n\nError: {str(e)}",
            "sources": [],
            "user_context_used": False,
            "error": str(e),
        }


def quick_advice(user_id: str, topic: str) -> dict:
    """
    Generate quick financial advice on a specific topic without chat history.

    Pre-defined topics:
        - "can_i_afford": Can I afford a specific purchase?
        - "debt_strategy": Best debt payment strategy
        - "savings_check": Am I on track with savings?
        - "budget_review": Review my spending habits
        - "income_outlook": Income forecast summary

    Args:
        user_id: User identifier
        topic: One of the pre-defined topics

    Returns:
        dict: Same format as chat()
    """
    topic_prompts = {
        "can_i_afford": (
            "بناءً على وضعي المالي الحالي، أنا عاوز أعرف أقدر أصرف كام في شراء حاجة جديدة "
            "الشهر ده من غير ما أأثر على ميزانيتي. قولي المبلغ المتاح وانصحني."
        ),
        "debt_strategy": (
            "ادرس ديوني وقولي أنهي استراتيجية أحسنلي — الانهيار الجليدي ولا كرة الثلج ولا الهجين. "
            "اشرحلي ليه وقولي هخلص الديون في قد إيه."
        ),
        "savings_check": (
            "راجع أهداف التوفير بتاعتي وقولي هل أنا ماشي صح ولا لأ. "
            "لو في مشكلة، اقترح حلول عملية."
        ),
        "budget_review": (
            "حلل مصاريفي واعملي مراجعة شاملة. فين بصرف أكتر من اللازم؟ "
            "وإيه اللي ممكن أوفره؟ قولي أرقام محددة."
        ),
        "income_outlook": (
            "إيه توقعاتك لدخلي الأشهر الجاية؟ هل فيه حاجة لازم أعملها "
            "عشان أحسن وضعي المالي؟"
        ),
    }

    prompt = topic_prompts.get(
        topic,
        f"اديني نصيحة مالية عامة عن: {topic}"
    )

    return chat(user_id, prompt)


def get_financial_snapshot(user_id: str) -> dict:
    """
    Get a complete financial snapshot without calling the LLM.
    Useful for dashboards and overview screens.

    Args:
        user_id: User identifier

    Returns:
        dict: {
            profile: dict,
            income_forecast: dict,
            budget_plan: dict,
            debt_analysis: dict,
            account_summary: dict,
            debt_info: dict,
            savings_info: dict,
            health_score: float (0-100),
        }
    """
    try:
        profile = get_user_profile(user_id)
        forecast = forecast_income(user_id, months_ahead=3)
        budget = get_budget_plan(user_id)
        debts = prioritize_debts(user_id, strategy="hybrid")
        acc_summary = get_account_summary(user_id)
        debt_det = get_debt_info(user_id)
        savings_det = get_savings_info(user_id)

        # Calculate overall financial health score
        health_score = _calculate_health_score(profile, forecast, budget, debts)

        return {
            "profile": {
                "user_id": user_id,
                "profile_type": profile.get("profile_type", "unknown"),
                "primary_skill": profile.get("primary_skill", "N/A"),
                "avg_monthly_income": profile.get("avg_monthly_income", 0),
            },
            "income_forecast": forecast,
            "budget_plan": budget,
            "debt_analysis": debts,
            "account_summary": acc_summary,
            "debt_info": debt_det,
            "savings_info": savings_det,
            "health_score": health_score,
        }
    except Exception as e:
        return {"error": str(e)}


def _calculate_health_score(profile, forecast, budget, debts) -> float:
    """
    Calculate an overall financial health score (0-100).
    Composite of multiple factors.
    """
    scores = []

    # 1. Income stability (0-25 points)
    stability = forecast.get("stability_score", 0)
    scores.append(stability * 0.25)  # Max 25

    # 2. Budget surplus (0-25 points)
    surplus = budget.get("surplus_deficit", 0)
    virtual_salary = budget.get("virtual_salary", 1)
    if virtual_salary > 0:
        surplus_ratio = surplus / virtual_salary
        surplus_score = max(0, min(25, 25 * (surplus_ratio + 0.2) / 0.4))  # 0-25
    else:
        surplus_score = 0
    scores.append(surplus_score)

    # 3. Debt burden (0-25 points) — less debt = better
    debt_total = budget.get("total_debt_payments", 0)
    if virtual_salary > 0:
        debt_ratio = debt_total / virtual_salary
        debt_score = max(0, 25 * (1 - debt_ratio / 0.5))  # Full score if <5% debt
    else:
        debt_score = 25 if debt_total == 0 else 0
    scores.append(debt_score)

    # 4. Savings progress (0-15 points)
    savings_goals = budget.get("savings_goals", [])
    if savings_goals:
        on_track = sum(1 for g in savings_goals if g["on_track"])
        savings_score = 15 * (on_track / len(savings_goals))
    else:
        savings_score = 7.5  # Neutral if no goals
    scores.append(savings_score)

    # 5. Income diversity (0-10 points)
    diversity = forecast.get("platform_diversity", 0)
    scores.append(diversity * 10)

    total = round(sum(scores), 1)
    return max(0, min(100, total))


def _extract_sources(knowledge_context: str) -> list:
    """Extract source filenames from knowledge context string."""
    sources = []
    for line in knowledge_context.split("\n"):
        if line.startswith("**Source**:"):
            source = line.split("**Source**:")[1].strip()
            source = source.split("(")[0].strip()
            if source not in sources:
                sources.append(source)
    return sources


if __name__ == "__main__":
    import json

    # Test: Financial Snapshot (no LLM needed)
    print("=" * 60)
    print("FINANCIAL SNAPSHOT (no LLM)")
    print("=" * 60)
    snapshot = get_financial_snapshot("user_0001")
    if "error" not in snapshot:
        print(f"Profile: {snapshot['profile']['profile_type']}")
        print(f"Avg Income: {snapshot['profile']['avg_monthly_income']:,.2f}")
        print(f"Health Score: {snapshot['health_score']}/100")
        print(f"Virtual Salary: {snapshot['budget_plan']['virtual_salary']:,.2f}")
        print(f"Surplus/Deficit: {snapshot['budget_plan']['surplus_deficit']:+,.2f}")
        print(f"Debts: {len(snapshot['debt_analysis']['ranked_debts'])}")
        print(f"Accounts: {snapshot['account_summary']['num_accounts']}")
        print(f"  Total Balance: {snapshot['account_summary']['total_balance']:,.2f}")
        print(f"Debt Info: {snapshot['debt_info']['num_debts']} debts, "
              f"{snapshot['debt_info']['monthly_obligations']:,.2f}/month")
        print(f"Savings: {snapshot['savings_info']['num_goals']} goals, "
              f"{snapshot['savings_info']['overall_progress_pct']}% overall")
    else:
        print(f"Error: {snapshot['error']}")

    # Test: Specialized functions
    print("\n" + "=" * 60)
    print("SPECIALIZED FUNCTIONS")
    print("=" * 60)

    print("\n--- can_i_afford(15000) ---")
    afford = can_i_afford("user_0001", 15000)
    print(f"Verdict: {afford['verdict']}")
    print(f"Method: {afford['method']}")
    print(f"Monthly Surplus: {afford['monthly_surplus']:,.2f}")

    print("\n--- installment_impact(500/month, 12 months) ---")
    impact = installment_impact("user_0001", 500, 12)
    print(f"Affordable: {impact['affordable']}")
    print(f"Risk Level: {impact['risk_level']}")
    print(f"New Debt Ratio: {impact['new_debt_ratio']}%")
    if impact['warnings']:
        for w in impact['warnings']:
            print(f"  [!] {w}")

    print("\n--- savings_plan(Apartment, 200000, 36 months) ---")
    plan = savings_plan("user_0001", "Apartment Down Payment", 200000, 36)
    print(f"Verdict: {plan['verdict']}")
    print(f"Monthly Needed: {plan['monthly_needed']:,.2f}")
    print(f"Recommendation: {plan['recommendation']}")

    print("\n--- which_debt_first() ---")
    debt_rec = which_debt_first("user_0001")
    if debt_rec.get("top_priority"):
        tp = debt_rec["top_priority"]
        print(f"Top Priority: {tp['name']} ({tp['remaining']:,.2f} remaining)")
        print(f"Strategy: {debt_rec['recommended_strategy']}")
        print(f"Months to Debt-Free: {debt_rec['months_to_free']}")
    else:
        print(debt_rec.get("recommendation", "No debts"))

    # Test: Chat (requires GEMINI_API_KEY)
    print("\n" + "=" * 60)
    print("CHAT TEST (requires GEMINI_API_KEY)")
    print("=" * 60)
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        result = chat("user_0001", "هل أقدر أشتري لابتوب بـ 15000 جنيه الشهر ده؟")
        print(f"Response: {result['response'][:300]}...")
        print(f"Sources: {result['sources']}")
    else:
        print("GEMINI_API_KEY not set — skipping chat test.")
        print("Set it with: $env:GEMINI_API_KEY='your-key-here'")
