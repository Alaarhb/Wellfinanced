"""
WellFinanced — LLM Prompt Templates
System prompts and formatting helpers for the Financial Advisor chatbot.
Includes financial flow taxonomy extracted from assistant.py and Source of Money.md.
"""


# ──────────────────────────────────────────────
# Financial Flow Taxonomy (from assistant.py / ERD)
# These constants make the advisor aware of the app's data schema.
# ──────────────────────────────────────────────

INFLOW_CATEGORIES = {
    "income": ["salary_wages", "freelance_contract_payment", "business_revenue",
               "investment_income", "rent_property_income"],
    "transfers_support": ["government_benefits", "scholarship_stipend", "ngo_charity_support",
                          "family_friends_support", "insurance_compensation", "gift_inheritance_prize"],
    "capital_conversion": ["sell_assets_cash_out"],
    "liability_inflow": ["borrowing_credit"],
    "internal_transfer": ["own_account_transfer"],
    "refund_reversal": ["refund", "chargeback"],
}

OUTFLOW_CATEGORIES = {
    "expense": ["consumable", "purchase", "payment", "subscription", "tax_fee"],
    "capital_outflow": ["buy_assets", "investment_deposit"],
    "liability_repayment": ["loan_installment", "credit_card_payment", "bnpl_payment"],
    "transfers_support_out": ["gift_support", "charity_donation"],
    "internal_transfer": ["own_account_transfer"],
}

ACCOUNT_TYPES = ["cash", "checking", "savings", "wallet", "investment", "receivable", "escrow"]

COUNTERPARTY_CATEGORIES = ["person", "service", "company", "ngo", "government"]

ASSET_CATEGORIES = ["property", "stocks"]


# ──────────────────────────────────────────────
# System Prompt
# ──────────────────────────────────────────────

SYSTEM_PROMPT = """You are WellFinanced AI — a personal financial advisor specialized in helping freelancers manage their finances.

## Your Capabilities
- You have access to the user's REAL financial data (income, expenses, debts, savings goals, account balances, assets).
- You can analyze their spending patterns and income trends.
- You provide specific, actionable advice based on actual numbers.
- You understand the unique challenges of freelance/irregular income.

## Financial Flow Awareness
You understand the app's financial classification system:
- **Inflow types**: Income (salary, freelance, business, investment, rent), Transfers & Support (family, government, gifts), Capital Conversion (asset sales), Liability Inflow (loans)
- **Outflow types**: Expenses (consumable, purchase, subscription), Capital Outflow (investments), Liability Repayment (installments, loans), Transfers Out (gifts, charity)
- **Account types**: Cash, Checking, Savings, Wallet, Investment, Receivable, Escrow
- **Key distinction**: Asset sales and loans are NOT income. Internal transfers are neutral. Only true income increases net worth.

## Communication Style
- Be warm, encouraging, but realistic.
- Always reference the user's actual financial numbers when giving advice.
- Respond in the SAME LANGUAGE the user uses (Arabic or English).
- Use simple, clear language — avoid complex financial jargon unless explained.
- When recommending actions, be specific (exact amounts, percentages, timeframes).
- If you don't have enough data to answer, say so honestly.

## Rules
- Never make up financial data. Only reference the context provided.
- If asked about something outside personal finance, politely redirect.
- Prioritize the user's financial safety — discourage risky decisions.
- Consider the Egyptian financial context when relevant (installments, savings certificates, etc.).
- Always consider both short-term needs and long-term financial health.
"""


USER_CONTEXT_TEMPLATE = """
## User Financial Profile
- **Profile Type**: {profile_type}
- **Average Monthly Income**: {avg_monthly_income:,.2f}
- **Income Stability Score**: {stability_score}/100
- **Platform Diversity**: {platform_diversity:.2f}
- **Primary Skills**: {primary_skill}

## Income Overview
- **Predicted Monthly Income (next 3 months)**: {predicted_income:,.2f}
- **Income Trend**: {income_trend}
- **Model Used**: {model_used}

## Account Summary
- **Total Balance (all accounts)**: {total_account_balance:,.2f}
- **Number of Accounts**: {num_accounts}
{account_details}

## Expense Overview
- **Average Monthly Expenses**: {avg_expenses:,.2f}
- **Needs (Essential)**: {needs_total:,.2f} ({needs_pct:.1f}%)
- **Wants (Non-essential)**: {wants_total:,.2f} ({wants_pct:.1f}%)
- **Top Spending Categories**: {top_spending}

## Budget Status
- **Virtual Salary**: {virtual_salary:,.2f}
- **Monthly Surplus/Deficit**: {surplus_deficit:+,.2f}

## Debts & Installments
{debt_summary}

## Savings Goals
{savings_summary}

## Recent Alerts
{alerts}
"""


def build_user_context(profile: dict, forecast: dict, budget: dict,
                       debts_info: dict, account_summary: dict = None,
                       debt_detail: dict = None, savings_detail: dict = None,
                       **kwargs) -> str:
    """
    Build a formatted user context string for the LLM prompt.

    Args:
        profile: User profile dict from data_loader
        forecast: Result from income_forecast.forecast_income()
        budget: Result from cashflow_smoothing.get_budget_plan()
        debts_info: Result from debt_prioritizer.prioritize_debts()
        account_summary: Result from data_loader.get_account_summary() (optional)
        debt_detail: Result from data_loader.get_debt_info() (optional)
        savings_detail: Result from data_loader.get_savings_info() (optional)

    Returns:
        Formatted context string
    """
    # Income trend
    historical = forecast.get("historical", [])
    if len(historical) >= 6:
        recent_avg = sum(h["amount"] for h in historical[-3:]) / 3
        older_avg = sum(h["amount"] for h in historical[-6:-3]) / 3
        if recent_avg > older_avg * 1.1:
            income_trend = "📈 Increasing"
        elif recent_avg < older_avg * 0.9:
            income_trend = "📉 Decreasing"
        else:
            income_trend = "➡️ Stable"
    else:
        income_trend = "❓ Insufficient data"

    # Account details
    if account_summary and account_summary.get("num_accounts", 0) > 0:
        acc_lines = []
        for cat, info in account_summary.get("by_category", {}).items():
            acc_lines.append(f"  - {cat.title()}: {info['total_balance']:,.2f} EGP ({info['count']} account(s))")
        account_details = "\n".join(acc_lines) if acc_lines else "No account data available."
    else:
        account_details = "No account data available."

    # Debt summary — use detailed debt_detail if available, fall back to debts_info
    if debt_detail and debt_detail.get("num_debts", 0) > 0:
        debt_lines = []
        for d in debt_detail["debts"]:
            debt_lines.append(
                f"- {d['name']}: {d['remaining']:,.2f} remaining "
                f"@ {d['interest_rate']}% interest "
                f"(payment: {d['monthly_payment']:,.2f}/month, due: {d['due_date']})"
            )
        debt_summary = "\n".join(debt_lines)
        debt_summary += (
            f"\n- **Total Debt**: {debt_detail['total_debt']:,.2f}"
            f"\n- **Total Monthly Obligations**: {debt_detail['monthly_obligations']:,.2f}/month"
            f"\n- **Recommended Strategy**: {debts_info.get('strategy', 'hybrid')} "
            f"— {debts_info.get('strategy_description', '')}"
            f"\n- **Months to Debt-Free**: {debts_info.get('months_to_free', '?')}"
        )
    else:
        ranked_debts = debts_info.get("ranked_debts", [])
        if ranked_debts:
            debt_lines = []
            for d in ranked_debts:
                debt_lines.append(
                    f"- {d['debt_name'] if 'debt_name' in d else d.get('name', 'Unknown')}: "
                    f"{d['remaining_amount'] if 'remaining_amount' in d else d.get('remaining', 0):,.2f} remaining "
                    f"@ {d['interest_rate']}% interest"
                )
            debt_summary = "\n".join(debt_lines)
            debt_summary += (
                f"\n- **Total Debt Payments**: {budget.get('total_debt_payments', 0):,.2f}/month"
                f"\n- **Recommended Strategy**: {debts_info.get('strategy', 'hybrid')}"
                f"\n- **Months to Debt-Free**: {debts_info.get('months_to_free', '?')}"
            )
        else:
            debt_summary = "No active debts. 🎉"

    # Savings summary — use detailed savings_detail if available
    if savings_detail and savings_detail.get("num_goals", 0) > 0:
        savings_lines = []
        for g in savings_detail["goals"]:
            status = "✅ On track" if g["on_track"] else "⚠️ Behind schedule"
            savings_lines.append(
                f"- {g['name']}: {g['saved']:,.2f}/{g['target']:,.2f} "
                f"({g['progress_pct']}%) — {status} "
                f"(contributing {g['monthly_contribution']:,.2f}/month, need {g['required_monthly']:,.2f}/month)"
            )
        savings_summary = "\n".join(savings_lines)
        savings_summary += f"\n- **Overall Progress**: {savings_detail['overall_progress_pct']}%"
    else:
        savings_goals = budget.get("savings_goals", [])
        if savings_goals:
            savings_lines = []
            for g in savings_goals:
                status = "✅ On track" if g["on_track"] else "⚠️ Behind schedule"
                savings_lines.append(
                    f"- {g['name']}: {g['saved']:,.2f}/{g['target']:,.2f} "
                    f"({g['progress_pct']}%) — {status}"
                )
            savings_summary = "\n".join(savings_lines)
        else:
            savings_summary = "No savings goals set."

    # Alerts
    alerts = budget.get("alerts", [])
    alerts_str = "\n".join(f"- {a}" for a in alerts) if alerts else "No alerts."

    # Top spending
    top_spending = ", ".join(budget.get("expense_summary", {}).get("top_spending", []))

    return USER_CONTEXT_TEMPLATE.format(
        profile_type=profile.get("profile_type", "unknown"),
        avg_monthly_income=profile.get("avg_monthly_income", 0),
        stability_score=forecast.get("stability_score", 0),
        platform_diversity=forecast.get("platform_diversity", 0),
        primary_skill=profile.get("primary_skill", "N/A"),
        predicted_income=forecast.get("avg_predicted", 0),
        income_trend=income_trend,
        model_used=forecast.get("model_used", "N/A"),
        total_account_balance=account_summary.get("total_balance", 0) if account_summary else 0,
        num_accounts=account_summary.get("num_accounts", 0) if account_summary else 0,
        account_details=account_details,
        avg_expenses=budget.get("expense_summary", {}).get("monthly_avg", 0),
        needs_total=budget.get("budget", {}).get("needs", {}).get("amount", 0),
        needs_pct=budget.get("expense_summary", {}).get("needs_pct", 0),
        wants_total=budget.get("budget", {}).get("wants", {}).get("amount", 0),
        wants_pct=budget.get("expense_summary", {}).get("wants_pct", 0),
        top_spending=top_spending or "N/A",
        virtual_salary=budget.get("virtual_salary", 0),
        surplus_deficit=budget.get("surplus_deficit", 0),
        debt_summary=debt_summary,
        savings_summary=savings_summary,
        alerts=alerts_str,
    )


def format_chat_prompt(system: str, context: str, history: list,
                       user_message: str) -> str:
    """
    Format the full prompt for the Gemini API.

    Args:
        system: System prompt
        context: User financial context
        history: List of {"role": "user"|"assistant", "content": str}
        user_message: Current user message

    Returns:
        Formatted prompt string
    """
    parts = [system, "\n---\n", context, "\n---\n"]

    if history:
        parts.append("\n## Conversation History\n")
        for msg in history[-6:]:  # Keep last 6 messages for context window
            role = "المستخدم" if msg["role"] == "user" else "المستشار"
            parts.append(f"**{role}**: {msg['content']}\n")

    parts.append(f"\n## Current Question\n{user_message}")

    return "\n".join(parts)
