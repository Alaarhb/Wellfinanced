from pydantic import BaseModel, Field
from datetime import datetime

class SavingsGoalBase(BaseModel):
    goal_name: str = Field(..., min_length=2, max_length=100)
    target_amount: float = Field(..., gt=0)
    saved_amount: float = Field(..., ge=0)
    monthly_contribution: float = Field(..., ge=0)
    deadline: datetime

class SavingsGoalCreate(SavingsGoalBase):
    pass

class SavingsGoalOut(SavingsGoalBase):
    id: str
    user_id: str

    class Config:
        from_attributes = True
