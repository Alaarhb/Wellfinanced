from pydantic import BaseModel, Field
from typing import Optional

class AccountBase(BaseModel):
    label: str = Field(..., min_length=2, max_length=100)
    institution: Optional[str] = None
    category: str = Field(..., description="cash, checking, savings, wallet, etc.")
    current_balance: Optional[float] = 0.00
    currency: Optional[str] = "EGP"
    status: Optional[str] = "active"

class AccountCreate(AccountBase):
    pass

class AccountOut(AccountBase):
    id: str
    user_id: str

    class Config:
        from_attributes = True
