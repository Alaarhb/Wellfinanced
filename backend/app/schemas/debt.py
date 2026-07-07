from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class DebtBase(BaseModel):
    debt_name: str = Field(..., min_length=2, max_length=100)
    total_amount: float = Field(..., gt=0)
    remaining_amount: float = Field(..., ge=0)
    monthly_payment: float = Field(..., ge=0)
    interest_rate: Optional[float] = 0.00
    due_date: datetime
    priority: Optional[int] = 1
    status: Optional[str] = "active"  # active, paid, overdue

class DebtCreate(DebtBase):
    pass

class DebtOut(DebtBase):
    id: str
    user_id: str
    created_at: datetime

    class Config:
        from_attributes = True
