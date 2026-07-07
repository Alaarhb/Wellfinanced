from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .models.user import User
from .models.income import IncomeEntry
from .models.expense import Expense
from .models.debt import Debt
from .models.account import Account
from .models.savings_goal import SavingsGoal
from .routers import auth

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="WellFinanced Backend API",
    description="The backend server for the WellFinanced Freelancer AI Engine",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)

@app.get("/")
def read_root():
    return {
        "message": "Welcome to WellFinanced API",
        "docs_url": "/docs"
    }
