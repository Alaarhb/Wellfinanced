from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

# الأنماط المشتركة للـ User
class UserBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr

# بيانات الـ Sign Up
class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=100)
    profile_type: Optional[str] = "inconsistent"
    primary_skill: Optional[str] = None

# بيانات الـ Log In
class UserLogin(BaseModel):
    email: EmailStr
    password: str

# بيانات الـ Output (Profile Response)
class UserOut(UserBase):
    id: str
    profile_type: str
    primary_skill: Optional[str] = None
    avg_monthly_income: float
    joined_at: datetime

    class Config:
        from_attributes = True

# هيكل الـ Token الراجع
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: Optional[str] = None
