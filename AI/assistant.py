from enum import StrEnum

import dspy
from pydantic import BaseModel


class FlowType(StrEnum):
    INCOME = "income"
    CAPITAL_CONVERSION = "capital_conversion"
    TRANSFERS_SUPPORT = "transfers_support"
    LIABILITY_INFLOW = "liability_inflow"
    INTERNAL_TRANSFER = "internal_transfer"
    REFUND_REVERSAL = "refund_reversal"


class Predictability(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    VERY_LOW = "very_low"


class Recurrence(StrEnum):
    RECURRING = "recurring"
    PERIODIC = "periodic"
    ONE_OFF = "one_off"
    IRREGULAR = "irregular"


class ObligationBasis(StrEnum):
    CONTRACTUAL = "contractual"
    ELIGIBILITY_BASED = "eligibility_based"
    DISCRETIONARY = "discretionary"
    REPAIDABLE = "repayable"
    NONE = "none"


class CashflowRole(StrEnum):
    INFLOW = "inflow"
    OUTFLOW = "outflow"
    NEUTRAL = "neutral"


class NetWorthEffect(StrEnum):
    INCREASES_NET_WORTH = "increases_net_worth"
    NEUTRAL = "neutral"
    SHIFTS_ASSET_FORM = "shifts_asset_form"
    CREATES_LIABILITY = "creates_liability"

############################################
class FinancialRecord(BaseModel):
	"""
	Represents a past financial event for context.
	"""

	description: str = dspy.InputField(desc="User description of the past financial event")
	flow_type: FlowType = dspy.InputField(desc="Inferred flow type of the past event")
	amount: float = dspy.InputField(desc="Amount of the past event")
	date: str = dspy.InputField(desc="Date of the past event in YYYY-MM-DD format")

class ClassifyFlow(dspy.Signature):
    """
    Classify a financial event into structured financial flow types.
    """

    user_text: str = dspy.InputField(desc="User description of the financial event")
    history: list[FinancialRecord] = dspy.InputField(desc="Optional past financial context")

    flow_type: FlowType = dspy.OutputField()
    subtype: str = dspy.OutputField()
    source_bucket: str = dspy.OutputField()

    predictability: Predictability = dspy.OutputField()
    recurrence: Recurrence = dspy.OutputField()
    obligation_basis: ObligationBasis = dspy.OutputField()

    income_flag: bool = dspy.OutputField()
    windfall_flag: bool = dspy.OutputField()

    cashflow_role: CashflowRole = dspy.OutputField()
    net_worth_effect: NetWorthEffect = dspy.OutputField()

    needs_follow_up: bool = dspy.OutputField()


    subtype: str = dspy.OutputField(
        desc="More specific label (e.g. salary, loan, asset_sale)"
    )
    source_bucket: str = dspy.OutputField(desc="Human-friendly source category")
    predictability: str = dspy.OutputField(desc="high | medium | low | very_low")
    recurrence: str = dspy.OutputField(
        desc="recurring | periodic | one_off | irregular"
    )
    obligation_basis: str = dspy.OutputField(
        desc="contractual | eligibility_based | discretionary | repayable | none"
    )

    income_flag: bool = dspy.OutputField(
        desc="Whether it counts as income in financial reporting"
    )
    windfall_flag: bool = dspy.OutputField(
        desc="Whether it is unexpected / irregular / non-structural"
    )

    cashflow_role: str = dspy.OutputField(desc="inflow | outflow | neutral")
    net_worth_effect: str = dspy.OutputField(
        desc="increases_net_worth | neutral | shifts_asset_form | creates_liability"
    )

    needs_follow_up: bool = dspy.OutputField(desc="Whether clarification is needed")

















class GenerateAdvice(dspy.Signature):
    """
    Generate concise financial advice based on a classified financial flow.
    """

    user_text: str = dspy.InputField()
    classification: str = dspy.InputField(
        desc="Structured classification output from previous step"
    )

    summary: str = dspy.OutputField(desc="One-line plain English explanation")
    advice: str = dspy.OutputField(desc="Concise actionable guidance")
    follow_up_question: str = dspy.OutputField(
        desc="Only if necessary, otherwise empty string"
    )


class FinancialFlowClassifier(dspy.Module):
    def __init__(self):
        self.classify = dspy.ChainOfThought(ClassifyFlow)

    def forward(self, user_text, history=""):
        return self.classify(user_text=user_text, history=history)


class FinancialAdvisor(dspy.Module):
    def __init__(self):
        self.classifier = FinancialFlowClassifier()
        self.advisor = dspy.ChainOfThought(GenerateAdvice)

    def forward(self, user_text, history=""):
        classification = self.classifier(user_text, history)

        # serialize classification into structured text for second stage
        classification_str = str(classification)

        advice = self.advisor(user_text=user_text, classification=classification_str)

        return {"classification": classification, "advice": advice}


lm = dspy.LM("openai/gpt-4o-mini", api_key="YOUR_API_KEY")
dspy.configure(lm=lm)

advisor = FinancialAdvisor()

result = advisor(
    user_text="I sold some Ethereum and moved the money to my bank account.",
    history="Held crypto for 2 years",
)

print(result["classification"])
print(result["advice"])


'''
Yes — and you *should*. In DSPy this is exactly how you reduce classification drift and make evaluation/optimization stable.

Below is a **clean enum-based redesign** of your signatures.

---

# ✅ 1. Define Enums (core financial ontology)

```python id="enum_core"
from enum import Enum
```

## Flow Type

```python id="enum_flow"
class FlowType(StrEnum):
    INCOME = "income"
    CAPITAL_CONVERSION = "capital_conversion"
    TRANSFERS_SUPPORT = "transfers_support"
    LIABILITY_INFLOW = "liability_inflow"
    INTERNAL_TRANSFER = "internal_transfer"
    REFUND_REVERSAL = "refund_reversal"
```

---

## Predictability

```python id="enum_pred"
class Predictability(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    VERY_LOW = "very_low"
```

---

## Recurrence

```python id="enum_rec"
class Recurrence(StrEnum):
    RECURRING = "recurring"
    PERIODIC = "periodic"
    ONE_OFF = "one_off"
    IRREGULAR = "irregular"
```

---

## Obligation Basis

```python id="enum_obl"
class ObligationBasis(StrEnum):
    CONTRACTUAL = "contractual"
    ELIGIBILITY_BASED = "eligibility_based"
    DISCRETIONARY = "discretionary"
    REPAIDABLE = "repayable"
    NONE = "none"
```

---

## Cashflow Role

```python id="enum_cash"
class CashflowRole(StrEnum):
    INFLOW = "inflow"
    OUTFLOW = "outflow"
    NEUTRAL = "neutral"
```

---

## Net Worth Effect

```python id="enum_nw"
class NetWorthEffect(StrEnum):
    INCREASES_NET_WORTH = "increases_net_worth"
    NEUTRAL = "neutral"
    SHIFTS_ASSET_FORM = "shifts_asset_form"
    CREATES_LIABILITY = "creates_liability"
```

---

# ✅ 2. DSPy Signature (NOW TYPE-SAFE)

This is the corrected version of your classification signature:

```python id="sig_enum_1"
import dspy


class ClassifyFlow(dspy.Signature):
    """
    Classify a financial event into structured financial flow types.
    """

    user_text: str = dspy.InputField()
    history: str = dspy.InputField()

    flow_type: FlowType = dspy.OutputField()
    subtype: str = dspy.OutputField()
    source_bucket: str = dspy.OutputField()

    predictability: Predictability = dspy.OutputField()
    recurrence: Recurrence = dspy.OutputField()
    obligation_basis: ObligationBasis = dspy.OutputField()

    income_flag: bool = dspy.OutputField()
    windfall_flag: bool = dspy.OutputField()

    cashflow_role: CashflowRole = dspy.OutputField()
    net_worth_effect: NetWorthEffect = dspy.OutputField()

    needs_follow_up: bool = dspy.OutputField()
```

---

# ✅ 3. Advice Signature (unchanged enums optional)

Advice usually stays free-text, but we can still keep structure:

```python id="sig_enum_2"
class GenerateAdvice(dspy.Signature):
    """
    Generate financial advice from classification output.
    """

    user_text: str = dspy.InputField()
    classification: str = dspy.InputField()

    summary: str = dspy.OutputField()
    advice: str = dspy.OutputField()
    follow_up_question: str = dspy.OutputField()
```

---

# ✅ 4. Why this matters (important)

## Without enums:

* LLM outputs: `"high"`, `"High"`, `"HIGH"`, `"very low"` → messy
* evaluation becomes unreliable
* DSPy optimizers struggle

---

## With enums:

* constrained output space
* stable optimization targets
* better few-shot learning efficiency
* easier scoring + metrics

---

# ⚠️ Important DSPy nuance

DSPy does **NOT strictly enforce enum validation at runtime**.

So you should optionally add:

### Post-validation layer

```python id="validate"
def validate_enum(value, enum_cls):
    try:
        return enum_cls(value)
    except ValueError:
        return None
```

or stricter:

* retry generation if invalid
* or use `choices=` constraints in prompt engineering layer

---

# 🚀 Optional upgrade (high value)

If you want to go *full production-grade DSPy*, next step is:

### ✔ Add metric-based optimization

* misclassification penalty for:

  * loans classified as income ❌
  * capital conversion misclassified as income ❌

### ✔ Use `dspy.MIPRO`

to automatically optimize:

* prompt structure
* few-shot selection
* reasoning chain depth

---

If you want, I can next build you a **fully optimized DSPy training loop with evaluation dataset + automatic financial correctness scoring (this is where it becomes a real fintech-grade system).**
'''


'''
Fair pushback — the previous version skipped the *actual DSPy idiomatic structure*. Let’s do this properly with **real `dspy.Signature`, modular decomposition, and a clean pipeline design**.

Below is a **correct, production-style DSPy implementation** of your financial flow classifier + advisor.

---

# ✅ 1. Core DSPy Signatures

We split this into two steps (this is how DSPy is meant to be used properly):

### Step 1: Classification

```python id="dspy_sig_1"
import dspy


class ClassifyFlow(dspy.Signature):
    """
    Classify a financial event into a structured financial flow type.
    """

    user_text: str = dspy.InputField(desc="User description of the financial event")
    history: str = dspy.InputField(desc="Optional past financial context")

    flow_type: str = dspy.OutputField(
        desc="income | capital_conversion | transfers_support | liability_inflow | internal_transfer | refund_reversal"
    )

    subtype: str = dspy.OutputField(desc="More specific label (e.g. salary, loan, asset_sale)")
    source_bucket: str = dspy.OutputField(desc="Human-friendly source category")
    predictability: str = dspy.OutputField(desc="high | medium | low | very_low")
    recurrence: str = dspy.OutputField(desc="recurring | periodic | one_off | irregular")
    obligation_basis: str = dspy.OutputField(
        desc="contractual | eligibility_based | discretionary | repayable | none"
    )

    income_flag: bool = dspy.OutputField(desc="Whether it counts as income in financial reporting")
    windfall_flag: bool = dspy.OutputField(desc="Whether it is unexpected / irregular / non-structural")

    cashflow_role: str = dspy.OutputField(desc="inflow | outflow | neutral")
    net_worth_effect: str = dspy.OutputField(
        desc="increases_net_worth | neutral | shifts_asset_form | creates_liability"
    )

    needs_follow_up: bool = dspy.OutputField(desc="Whether clarification is needed")
```

---

### Step 2: Advice Generation

```python id="dspy_sig_2"
class GenerateAdvice(dspy.Signature):
    """
    Generate concise financial advice based on a classified financial flow.
    """

    user_text: str = dspy.InputField()
    classification: str = dspy.InputField(desc="Structured classification output from previous step")

    summary: str = dspy.OutputField(desc="One-line plain English explanation")
    advice: str = dspy.OutputField(desc="Concise actionable guidance")
    follow_up_question: str = dspy.OutputField(desc="Only if necessary, otherwise empty string")
```

---

# ✅ 2. DSPy Modules (Proper Pipeline)

```python id="dspy_module_1"
class FinancialFlowClassifier(dspy.Module):
    def __init__(self):
        self.classify = dspy.ChainOfThought(ClassifyFlow)

    def forward(self, user_text, history=""):
        return self.classify(user_text=user_text, history=history)
```

---

```python id="dspy_module_2"
class FinancialAdvisor(dspy.Module):
    def __init__(self):
        self.classifier = FinancialFlowClassifier()
        self.advisor = dspy.ChainOfThought(GenerateAdvice)

    def forward(self, user_text, history=""):
        classification = self.classifier(user_text, history)

        # serialize classification into structured text for second stage
        classification_str = str(classification)

        advice = self.advisor(
            user_text=user_text,
            classification=classification_str
        )

        return {
            "classification": classification,
            "advice": advice
        }
```

---

# ✅ 3. Setup DSPy LM

```python id="dspy_setup"
lm = dspy.LM("openai/gpt-4o-mini", api_key="YOUR_API_KEY")
dspy.configure(lm=lm)
```

---

# ✅ 4. Run Example

```python id="dspy_run"
advisor = FinancialAdvisor()

result = advisor(
    user_text="I sold some Ethereum and moved the money to my bank account.",
    history="Held crypto for 2 years"
)

print(result["classification"])
print(result["advice"])
```

---

# 🔥 5. Why THIS version is correct (important)

This fixes what was missing before:

### ✔ Uses real `dspy.Signature`

Not pseudo-schema — actual DSPy structure.

### ✔ Multi-stage reasoning (core DSPy pattern)

* Step 1: structured classification
* Step 2: grounded advice generation

### ✔ Separation of concerns

* classification ≠ reasoning output
* avoids hallucinated mixing of logic + advice

### ✔ Composable architecture

You can now extend:

* add risk scoring module
* add cashflow forecasting module
* add anomaly detection module

---

# ⚠️ Important design note (expert-level insight)

You should NOT collapse classification + advice into one signature long-term.

Why?

Because:

* classification needs determinism
* advice needs natural language flexibility
* mixing them reduces evaluation quality in DSPy optimizers

---

# If you want next level

I can extend this into a **fully DSPy-optimized system with**:

* `dspy.MIPRO` optimizer setup
* evaluation dataset for financial correctness
* automatic calibration of “income vs capital conversion misclassification rate”
* multi-agent financial reasoning pipeline

That’s where this becomes production-grade fintech AI.

'''


"""
Below is a complete DSPy example built around your financial-flow taxonomy. In DSPy, signatures declare the input/output behavior of a task, `dspy.ChainOfThought` is a module that reasons step by step over that signature, and you typically configure the model with `dspy.LM(...)` plus `dspy.configure(lm=lm)`. `dspy.Example` objects are dict-like datapoints, `with_inputs()` marks which fields are inputs, and modules return `Prediction` objects. ([DSPy][1])

```python
import dspy


# -----------------------------
# 1) Configure the language model
# -----------------------------
# Replace with your provider/model of choice.
# The DSPy docs show configuring a model via dspy.LM(...) and dspy.configure(lm=lm).
lm = dspy.LM("openai/gpt-4o-mini", api_key="YOUR_OPENAI_API_KEY")
dspy.configure(lm=lm)


# -----------------------------
# 2) Define the signature
# -----------------------------
# This is the contract for the module:
# inputs: user_text, history
# outputs: structured financial-flow classification + concise advice
FLOW_SIG = (
    "user_text, history -> "
    "summary, flow_type, subtype, source_bucket, predictability, recurrence, "
    "obligation_basis, windfall_flag: bool, income_flag: bool, "
    "cashflow_role, net_worth_effect, needs_follow_up: bool, "
    "follow_up_question, advice"
)


# -----------------------------
# 3) Define the DSPy module
# -----------------------------
# ChainOfThought adds a reasoning field internally and predicts the requested outputs.
class FinancialFlowAdvisor(dspy.Module):
    def __init__(self):
        super().__init__()
        self.classify = dspy.ChainOfThought(FLOW_SIG)

    def forward(self, user_text: str, history: str = ""):
        return self.classify(user_text=user_text, history=history)


advisor = FinancialFlowAdvisor()


# -----------------------------
# 4) Optional few-shot examples
# -----------------------------
# dspy.Example is the core datapoint type for training/dev/test.
# with_inputs(...) marks which fields are inputs.
trainset = [
    dspy.Example(
        user_text="My mom sends me $200 every month.",
        history="This has been happening for 8 months.",
        summary="Recurring family support.",
        flow_type="transfers_support",
        subtype="family_support",
        source_bucket="family_friends",
        predictability="medium",
        recurrence="recurring",
        obligation_basis="discretionary",
        windfall_flag=False,
        income_flag=True,
        cashflow_role="inflow",
        net_worth_effect="increases_net_worth",
        needs_follow_up=False,
        follow_up_question="",
        advice="Include it in cashflow planning, but do not treat it as salary-level baseline income."
    ).with_inputs("user_text", "history"),

    dspy.Example(
        user_text="I sold some Tesla shares and moved the money to my bank.",
        history="Held the shares for years.",
        summary="Capital conversion from an asset sale.",
        flow_type="capital_conversion",
        subtype="asset_sale",
        source_bucket="asset_sale_cash_out",
        predictability="low",
        recurrence="one_off",
        obligation_basis="none",
        windfall_flag=False,
        income_flag=False,
        cashflow_role="inflow",
        net_worth_effect="shifts_asset_form",
        needs_follow_up=False,
        follow_up_question="",
        advice="Do not count this as income. Track realized gain separately if you want investment performance reporting."
    ).with_inputs("user_text", "history"),

    dspy.Example(
        user_text="I got a bank loan for $10,000.",
        history="Repayment starts next month.",
        summary="Liability inflow.",
        flow_type="liability_inflow",
        subtype="loan",
        source_bucket="borrowing_credit",
        predictability="medium",
        recurrence="one_off",
        obligation_basis="repayable",
        windfall_flag=False,
        income_flag=False,
        cashflow_role="inflow",
        net_worth_effect="creates_liability",
        needs_follow_up=False,
        follow_up_question="",
        advice="Cash increases now, but debt increases too. Keep this out of income metrics."
    ).with_inputs("user_text", "history"),

    dspy.Example(
        user_text="My insurance company paid me after a car accident.",
        history="Claim was approved last week.",
        summary="One-off compensation event.",
        flow_type="transfers_support",
        subtype="insurance_compensation",
        source_bucket="insurance_compensation",
        predictability="low",
        recurrence="one_off",
        obligation_basis="event_based",
        windfall_flag=True,
        income_flag=True,
        cashflow_role="inflow",
        net_worth_effect="increases_net_worth",
        needs_follow_up=False,
        follow_up_question="",
        advice="Treat this as a windfall-like transfer, not baseline income."
    ).with_inputs("user_text", "history"),

    dspy.Example(
        user_text="I moved money from my savings account to checking.",
        history="Both accounts belong to me.",
        summary="Internal transfer.",
        flow_type="internal_transfer",
        subtype="own_account_transfer",
        source_bucket="own_account_transfer",
        predictability="high",
        recurrence="irregular",
        obligation_basis="none",
        windfall_flag=False,
        income_flag=False,
        cashflow_role="neutral",
        net_worth_effect="neutral",
        needs_follow_up=False,
        follow_up_question="",
        advice="Do not treat this as income or expense; it is only a movement between your own accounts."
    ).with_inputs("user_text", "history"),
]


# -----------------------------
# 5) Run the advisor on a live example
# -----------------------------
result = advisor(
    user_text="I got $1,500 from a freelance client for a website redesign.",
    history="One-off project completed this week."
)

print("SUMMARY:", result.summary)
print("FLOW TYPE:", result.flow_type)
print("SUBTYPE:", result.subtype)
print("SOURCE BUCKET:", result.source_bucket)
print("PREDICTABILITY:", result.predictability)
print("RECURRENCE:", result.recurrence)
print("OBLIGATION BASIS:", result.obligation_basis)
print("WINDFALL FLAG:", result.windfall_flag)
print("INCOME FLAG:", result.income_flag)
print("CASHFLOW ROLE:", result.cashflow_role)
print("NET WORTH EFFECT:", result.net_worth_effect)
print("NEEDS FOLLOW-UP:", result.needs_follow_up)
print("FOLLOW-UP QUESTION:", result.follow_up_question)
print("ADVICE:", result.advice)


# -----------------------------
# 6) Optional helper for UI display
# -----------------------------
def as_dict(pred):
    return {
        "summary": pred.summary,
        "flow_type": pred.flow_type,
        "subtype": pred.subtype,
        "source_bucket": pred.source_bucket,
        "predictability": pred.predictability,
        "recurrence": pred.recurrence,
        "obligation_basis": pred.obligation_basis,
        "windfall_flag": pred.windfall_flag,
        "income_flag": pred.income_flag,
        "cashflow_role": pred.cashflow_role,
        "net_worth_effect": pred.net_worth_effect,
        "needs_follow_up": pred.needs_follow_up,
        "follow_up_question": pred.follow_up_question,
        "advice": pred.advice,
    }

print(as_dict(result))
```

The key idea is that the signature declares the classification contract, the module handles the reasoning, and the examples give your agent concrete labeled cases to imitate and later optimize against. DSPy modules are designed to be composed into larger programs, so this same pattern can be extended into a multi-step pipeline later. ([DSPy][1])

If useful, I can turn this into a version with a separate `classify` step and `advise` step, so the agent first labels the flow and then generates user-facing guidance from that label.

[1]: https://dspy.ai/learn/programming/signatures/ "Signatures - DSPy"

"""


"""
Absolutely — here is a tighter version you can drop into an agent framework.

## 1) System Prompt

```text
You are a Financial Flow Advisor for a personal finance application.

Your job is to help users understand, classify, and act on money-in and money-out events with high precision, while keeping the experience simple and human.

You must:
- Infer the real financial mechanism behind a transaction or planned flow.
- Preserve financial correctness even when the user uses informal language.
- Ask clarifying questions only when the classification materially affects advice, reporting, budgeting, cashflow, debt, or net worth.
- Give concise, practical, high-signal guidance.

Core flow types:
1. Income
   - Money created through work, business activity, or recurring yield.
   - Examples: salary, freelance payments, business revenue, rent, dividends, interest.

2. Capital Conversion
   - Money received by converting an owned asset into cash.
   - Examples: selling stocks, selling a car, cashing out crypto, withdrawing from investments, asset liquidation.
   - This is not income.

3. Transfers & Support
   - Money received through social, institutional, or assistance-based transfers that are not direct market exchange.
   - Examples: government benefits, financial aid, scholarships, stipends, NGO support, family allowance, gifts, insurance payouts, legal settlements, reparations.
   - This may be recurring or one-off, expected or unexpected.

4. Liability Inflow
   - Money received that creates a repayment obligation.
   - Examples: loans, credit line draws, BNPL, borrowed money.
   - This is not income.

5. Internal Transfer
   - Movement between the user’s own accounts.
   - Not income and not expense.

6. Refund / Reversal
   - A correction linked to a prior expense or transaction.
   - Do not treat as ordinary income unless the user explicitly wants a different reporting view.

Windfall handling:
- Windfall is not a top-level bucket.
- Treat it as an attribute for unexpected, irregular, non-structural inflows.
- Windfall-like events may occur within Transfers & Support.
- Common windfall-like events: insurance payouts, legal settlements, prizes, sudden gifts.

For every flow, infer these attributes when possible:
- predictability: high / medium / low / very low
- recurrence: recurring / periodic / one-off / irregular
- obligation basis: contractual / eligibility-based / discretionary / repayable / none
- cashflow role: inflow / outflow / neutral
- income flag: yes / no
- windfall flag: yes / no
- net worth effect: increases net worth / neutral / shifts asset form / creates liability
- needs follow-up: yes / no

User-facing source buckets for receive-from flows:
- Employer / Salary
- Freelance Client
- Business / Passive Revenue
- Government / Public Institution
- NGO / Charity
- Family & Friends
- Insurance / Compensation
- Borrowing / Credit
- Asset Sale / Cash Out
- Own Account Transfer

These are friendly labels only. Internally classify by flow type and attributes.

Clarification rule:
Ask a question only when one or more of these is true:
- The event could reasonably belong to multiple flow types and the distinction changes advice or reporting.
- The event may be income vs capital conversion vs liability.
- The event may be a refund or reversal of a prior transaction.
- The event may be an internal transfer.
- The answer would materially affect baseline income, cashflow forecasting, debt, or net worth.

If clarification is not critical, make a best-effort classification and state the assumption briefly.

Response behavior:
- Start with a plain-English summary.
- Then give classification, reasoning, impact, and advice.
- Keep it concise.
- Prefer correct classification over user-pleasant simplification.
- Never treat loans as income.
- Never treat asset sales or brokerage withdrawals as income.
- Never treat internal transfers as income or expense.
- Link refunds to the original expense whenever possible.
```

## 2) Developer Prompt

```text
You are the product-facing Financial Flow Advisor inside a personal finance system.

Goal:
Translate messy financial events into clean, useful guidance that supports budgeting, forecasting, debt tracking, and net worth tracking.

Design priorities:
1. Correct financial classification.
2. Minimal but critical clarification questions.
3. Concise, practical advice.
4. Stable outputs that can be stored and reused.

Behavior rules:
- Classify the event first, then advise.
- Preserve distinctions between earned income, support, capital conversion, liability, internal transfer, and refund/reversal.
- Do not over-taxonomize in user-facing language.
- Use the user's own wording when possible, but correct the accounting meaning internally.
- When the user provides history, use it to assess recurrence, predictability, and reliability.
- When the event is ambiguous, ask the minimum number of questions needed to resolve the ambiguity.

Recommended reasoning sequence:
1. Identify the source and mechanism.
2. Determine whether the event is:
   - income
   - capital conversion
   - transfers & support
   - liability inflow
   - internal transfer
   - refund / reversal
3. Assign attributes:
   - predictability
   - recurrence
   - obligation basis
   - windfall flag
   - income flag
   - net worth effect
4. Determine the accounting impact:
   - baseline income
   - cashflow
   - debt
   - net worth
   - budget relevance
5. Return a concise summary and a recommendation.

Clarification policy:
Ask only when it changes classification or materially changes advice.
Examples:
- Was this money borrowed, earned, gifted, refunded, or received from your own account?
- Was this from selling something you already owned?
- Is this recurring or one-time?
- Do you expect repayment?

Advice policy:
- Explain implications, not just labels.
- Tell the user what this means for income, savings rate, debt, or forecasting.
- When something is low predictability, warn against using it as baseline income.
- When something is liability inflow, warn that cash increases but debt increases too.
- When something is capital conversion, warn that it is not true earnings.

Tone:
- Concise
- Clear
- Non-technical unless needed
- Precise
- Confident but honest about uncertainty

Never:
- classify loans as income
- classify asset sales as income
- classify internal transfers as income
- bury a material ambiguity without asking
- pretend windfall is a top-level flow type
```

## 3) Output Schema

```json
{
  "summary": "Plain-English description of the financial flow.",
  "classification": {
    "flow_type": "income | capital_conversion | transfers_support | liability_inflow | internal_transfer | refund_reversal",
    "subtype": "string",
    "source_bucket": "employer_salary | freelance_client | business_passive_revenue | government_public_institution | ngo_charity | family_friends | insurance_compensation | borrowing_credit | asset_sale_cash_out | own_account_transfer | unknown",
    "predictability": "high | medium | low | very_low",
    "recurrence": "recurring | periodic | one_off | irregular",
    "obligation_basis": "contractual | eligibility_based | discretionary | repayable | none",
    "windfall_flag": true,
    "income_flag": true,
    "cashflow_role": "inflow | outflow | neutral",
    "net_worth_effect": "increases_net_worth | neutral | shifts_asset_form | creates_liability",
    "needs_follow_up": false
  },
  "reasoning": [
    "Short explanation of why this classification was chosen.",
    "Short explanation of any important distinction."
  ],
  "impact": {
    "affects_income_metrics": true,
    "affects_cashflow": true,
    "affects_debt": false,
    "affects_net_worth": false,
    "suitable_for_baseline_income": false,
    "suitable_for_budget_forecast": true
  },
  "advice": "Concise practical recommendation or caution.",
  "follow_up_question": null
}
```

## 4) Clarification Template

```text
I can classify this more accurately if you tell me one thing: was this money earned, borrowed, refunded, transferred from your own account, or received as support/gift?
```

## 5) Example Behavior

### Example 1

User: “I sold some Tesla shares and moved the money to my bank.”

```json
{
  "summary": "This is a capital conversion, not income.",
  "classification": {
    "flow_type": "capital_conversion",
    "subtype": "asset_sale",
    "source_bucket": "asset_sale_cash_out",
    "predictability": "low",
    "recurrence": "one_off",
    "obligation_basis": "none",
    "windfall_flag": false,
    "income_flag": false,
    "cashflow_role": "inflow",
    "net_worth_effect": "shifts_asset_form",
    "needs_follow_up": false
  },
  "reasoning": [
    "You converted an owned asset into cash.",
    "This increases liquidity but does not represent new earned value."
  ],
  "impact": {
    "affects_income_metrics": false,
    "affects_cashflow": true,
    "affects_debt": false,
    "affects_net_worth": false,
    "suitable_for_baseline_income": false,
    "suitable_for_budget_forecast": false
  },
  "advice": "Do not count this as income. Track any realized gain separately if you need investment performance reporting.",
  "follow_up_question": null
}
```

### Example 2

User: “My mom sends me money every month.”

```json
{
  "summary": "This is recurring family support.",
  "classification": {
    "flow_type": "transfers_support",
    "subtype": "family_support",
    "source_bucket": "family_friends",
    "predictability": "medium",
    "recurrence": "recurring",
    "obligation_basis": "discretionary",
    "windfall_flag": false,
    "income_flag": true,
    "cashflow_role": "inflow",
    "net_worth_effect": "increases_net_worth",
    "needs_follow_up": false
  },
  "reasoning": [
    "The source is personal network support rather than earned income.",
    "The recurring pattern makes it usable for cashflow planning, but not the same as salary."
  ],
  "impact": {
    "affects_income_metrics": true,
    "affects_cashflow": true,
    "affects_debt": false,
    "affects_net_worth": true,
    "suitable_for_baseline_income": false,
    "suitable_for_budget_forecast": true
  },
  "advice": "You can include it in cashflow planning, but avoid relying on it as high-confidence baseline income unless the pattern remains stable.",
  "follow_up_question": null
}
```

## 6) Optional compact decision rule

```text
If money came from work or business output → Income.
If money came from selling something you already owned → Capital Conversion.
If money came from family, government, charity, or compensation systems without market exchange → Transfers & Support.
If money came with repayment obligation → Liability Inflow.
If money moved between your own accounts → Internal Transfer.
If money corrects a prior expense → Refund / Reversal.
If it is surprising and irregular, set windfall_flag=true.
```

I can also turn this into a stricter JSON Schema or a tool-ready function spec next.
"""
