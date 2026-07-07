from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class IncomeBase(BaseModel):
    source_name: str = Field(..., min_length=2, max_length=100)
    amount: float = Field(..., gt=0)
    currency: Optional[str] = "EGP"
    date: datetime
    status: Optional[str] = "received"  # received, expected
    platform: Optional[str] = None  # Upwork, Fiverr, Direct, etc.

class IncomeCreate(IncomeBase):
    pass

class IncomeOut(IncomeBase):
    id: str
    user_id: str
    month: datetime
    created_at: datetime

    class Config:
        from_attributes = True
