from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ExpenseBase(BaseModel):
    category: str = Field(..., min_length=2, max_length=50)
    amount: float = Field(..., gt=0)
    expense_date: datetime
    is_recurring: Optional[bool] = False
    recurrence_rule: Optional[str] = None  # monthly, weekly, etc.

class ExpenseCreate(ExpenseBase):
    pass

class ExpenseOut(ExpenseBase):
    id: str
    user_id: str
    month: datetime
    created_at: datetime

    class Config:
        from_attributes = True
