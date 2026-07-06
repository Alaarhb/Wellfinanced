"""
Generate simulated data for schema entities: Account, Counterparty, Asset.
These map to the app's ERD and are used by the Financial Advisor for context.
"""

import pandas as pd
import numpy as np
import os

np.random.seed(42)

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
users = pd.read_csv(os.path.join(DATA_DIR, "users.csv"))
user_ids = users["user_id"].tolist()

# ──────────────────────────────────────────────
# 1. ACCOUNTS — Maps to schema: Account entity
# Categories: cash, checking, savings, wallet, investment, receivable, escrow
# Status: active, archived_inactive, closed, frozen, hidden, pending
# ──────────────────────────────────────────────

account_rows = []
account_id = 1

for uid in user_ids:
    user_row = users[users["user_id"] == uid].iloc[0]
    avg_income = user_row["avg_monthly_income"]

    # Every user gets a checking account
    account_rows.append({
        "account_id": f"acc_{account_id:04d}",
        "user_id": uid,
        "label": "Main Bank Account",
        "institution": np.random.choice(["National Bank of Egypt", "Banque Misr", "CIB", "QNB", "HSBC Egypt"]),
        "description": "Primary checking account for daily transactions",
        "currency": "EGP",
        "current_balance": round(np.random.uniform(avg_income * 0.3, avg_income * 2.5), 2),
        "status": "active",
        "category": "checking",
    })
    account_id += 1

    # 80% of users have a savings account
    if np.random.random() < 0.80:
        account_rows.append({
            "account_id": f"acc_{account_id:04d}",
            "user_id": uid,
            "label": "Savings Account",
            "institution": np.random.choice(["National Bank of Egypt", "Banque Misr", "CIB"]),
            "description": "Savings certificate or deposit account",
            "currency": "EGP",
            "current_balance": round(np.random.uniform(avg_income * 0.5, avg_income * 8), 2),
            "status": "active",
            "category": "savings",
        })
        account_id += 1

    # 65% of users have a wallet (Vodafone Cash, etc.)
    if np.random.random() < 0.65:
        account_rows.append({
            "account_id": f"acc_{account_id:04d}",
            "user_id": uid,
            "label": np.random.choice(["Vodafone Cash", "Fawry Wallet", "Orange Cash", "Etisalat Cash"]),
            "institution": "Mobile Wallet",
            "description": "Mobile money wallet",
            "currency": "EGP",
            "current_balance": round(np.random.uniform(100, avg_income * 0.5), 2),
            "status": "active",
            "category": "wallet",
        })
        account_id += 1

    # 30% have cash on hand tracked
    if np.random.random() < 0.30:
        account_rows.append({
            "account_id": f"acc_{account_id:04d}",
            "user_id": uid,
            "label": "Cash on Hand",
            "institution": "",
            "description": "Physical cash",
            "currency": "EGP",
            "current_balance": round(np.random.uniform(200, 3000), 2),
            "status": "active",
            "category": "cash",
        })
        account_id += 1

    # 20% have investment accounts
    if np.random.random() < 0.20:
        account_rows.append({
            "account_id": f"acc_{account_id:04d}",
            "user_id": uid,
            "label": "Investment Account",
            "institution": np.random.choice(["EFG Hermes", "Beltone", "CI Capital", "CIB Wealth"]),
            "description": "Stocks or mutual funds",
            "currency": "EGP",
            "current_balance": round(np.random.uniform(avg_income * 2, avg_income * 15), 2),
            "status": "active",
            "category": "investment",
        })
        account_id += 1

    # 15% have receivable (money owed to them by clients)
    if np.random.random() < 0.15:
        account_rows.append({
            "account_id": f"acc_{account_id:04d}",
            "user_id": uid,
            "label": "Client Receivables",
            "institution": "",
            "description": "Pending payments from clients",
            "currency": np.random.choice(["EGP", "USD"]),
            "current_balance": round(np.random.uniform(1000, avg_income * 2), 2),
            "status": "active",
            "category": "receivable",
        })
        account_id += 1

accounts_df = pd.DataFrame(account_rows)
accounts_df.to_csv(os.path.join(DATA_DIR, "accounts.csv"), index=False)
print(f"Generated {len(accounts_df)} accounts for {len(user_ids)} users")


# ──────────────────────────────────────────────
# 2. COUNTERPARTIES — Maps to schema: Counterparty entity
# Categories: person, service, company, ngo, government
# ──────────────────────────────────────────────

counterparty_rows = []
cp_id = 1

# Platform-based counterparties (companies)
platforms = [
    ("Upwork", "company", "Global freelancing platform"),
    ("Mostaql", "company", "Arabic freelancing platform"),
    ("Khamsat", "company", "Arabic micro-services platform"),
    ("Fiverr", "company", "Global gig marketplace"),
    ("Freelancer.com", "company", "Global freelancing platform"),
    ("Direct Client", "person", "Direct business client"),
]

for name, cat, desc in platforms:
    counterparty_rows.append({
        "counterparty_id": f"cp_{cp_id:04d}",
        "label": name,
        "description": desc,
        "category": cat,
    })
    cp_id += 1

# Service providers (expenses)
services = [
    ("Landlord", "person", "Property owner / rent payment"),
    ("Vodafone", "service", "Telecom provider"),
    ("WE Internet", "service", "Internet service provider"),
    ("Orange", "service", "Telecom provider"),
    ("Cairo Electricity", "service", "Electricity utility"),
    ("Carrefour", "company", "Grocery and retail store"),
    ("Uber Egypt", "service", "Transportation service"),
    ("Netflix", "service", "Streaming subscription"),
    ("Spotify", "service", "Music streaming subscription"),
    ("Adobe Creative Cloud", "service", "Design software subscription"),
    ("GitHub Pro", "service", "Developer tools subscription"),
    ("Pharmacy", "service", "Medical and pharmacy"),
    ("Udemy", "service", "Online education platform"),
    ("Coursera", "service", "Online education platform"),
]

for name, cat, desc in services:
    counterparty_rows.append({
        "counterparty_id": f"cp_{cp_id:04d}",
        "label": name,
        "description": desc,
        "category": cat,
    })
    cp_id += 1

# Financial institutions
banks = [
    ("National Bank of Egypt", "company", "Major Egyptian bank"),
    ("Banque Misr", "company", "Major Egyptian bank"),
    ("CIB", "company", "Commercial International Bank"),
    ("QNB", "company", "Qatar National Bank Egypt"),
    ("Valu", "company", "Buy Now Pay Later service"),
    ("Contact", "company", "Consumer finance company"),
]

for name, cat, desc in banks:
    counterparty_rows.append({
        "counterparty_id": f"cp_{cp_id:04d}",
        "label": name,
        "description": desc,
        "category": cat,
    })
    cp_id += 1

# Government
gov = [
    ("Tax Authority", "government", "Egyptian Tax Authority"),
    ("Social Insurance", "government", "Social insurance contributions"),
]

for name, cat, desc in gov:
    counterparty_rows.append({
        "counterparty_id": f"cp_{cp_id:04d}",
        "label": name,
        "description": desc,
        "category": cat,
    })
    cp_id += 1

# Family/NGO
personal = [
    ("Family Support", "person", "Family member financial support"),
    ("Resala Charity", "ngo", "Egyptian charity organization"),
]

for name, cat, desc in personal:
    counterparty_rows.append({
        "counterparty_id": f"cp_{cp_id:04d}",
        "label": name,
        "description": desc,
        "category": cat,
    })
    cp_id += 1

counterparties_df = pd.DataFrame(counterparty_rows)
counterparties_df.to_csv(os.path.join(DATA_DIR, "counterparties.csv"), index=False)
print(f"Generated {len(counterparties_df)} counterparties")


# ──────────────────────────────────────────────
# 3. ASSETS — Maps to schema: Asset entity
# Categories: stocks, property
# Status: active, idle_reserved, temporarily_unavailable, impaired, disposed_retired, writing_off
# ──────────────────────────────────────────────

asset_rows = []
asset_id = 1

for uid in user_ids:
    user_row = users[users["user_id"] == uid].iloc[0]
    avg_income = user_row["avg_monthly_income"]

    # 40% of users have equipment (laptop, etc.)
    if np.random.random() < 0.40:
        asset_rows.append({
            "asset_id": f"asset_{asset_id:04d}",
            "user_id": uid,
            "label": np.random.choice(["MacBook Pro", "Dell XPS", "Lenovo ThinkPad", "HP Spectre", "ASUS ROG"]),
            "description": "Work laptop for freelancing",
            "estimated_value": round(np.random.uniform(15000, 55000), 2),
            "category": "property",
            "status": "active",
        })
        asset_id += 1

    # 25% have a phone as tracked asset
    if np.random.random() < 0.25:
        asset_rows.append({
            "asset_id": f"asset_{asset_id:04d}",
            "user_id": uid,
            "label": np.random.choice(["iPhone 15 Pro", "Samsung Galaxy S24", "iPhone 14", "Google Pixel 8"]),
            "description": "Personal smartphone",
            "estimated_value": round(np.random.uniform(8000, 45000), 2),
            "category": "property",
            "status": "active",
        })
        asset_id += 1

    # 10% have stocks
    if np.random.random() < 0.10:
        asset_rows.append({
            "asset_id": f"asset_{asset_id:04d}",
            "user_id": uid,
            "label": np.random.choice(["EGX30 ETF", "CIB Shares", "Vodafone Egypt Shares", "Fawry Shares"]),
            "description": "Stock market investment",
            "estimated_value": round(np.random.uniform(5000, avg_income * 10), 2),
            "category": "stocks",
            "status": "active",
        })
        asset_id += 1

    # 5% have disposed assets
    if np.random.random() < 0.05:
        asset_rows.append({
            "asset_id": f"asset_{asset_id:04d}",
            "user_id": uid,
            "label": "Old Laptop",
            "description": "Previously used work laptop — sold",
            "estimated_value": round(np.random.uniform(3000, 8000), 2),
            "category": "property",
            "status": "disposed_retired",
        })
        asset_id += 1

assets_df = pd.DataFrame(asset_rows)
assets_df.to_csv(os.path.join(DATA_DIR, "assets.csv"), index=False)
print(f"Generated {len(assets_df)} assets for {len(user_ids)} users")

print("\n✅ All schema data generated successfully!")
print(f"  - accounts.csv: {len(accounts_df)} rows")
print(f"  - counterparties.csv: {len(counterparties_df)} rows")
print(f"  - assets.csv: {len(assets_df)} rows")
