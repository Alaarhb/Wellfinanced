import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Numeric, ForeignKey
from ..database import Base

def generate_uuid():
    return str(uuid.uuid4())

class Account(Base):
    __tablename__ = "accounts"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    label = Column(String(100), nullable=False)  # اسم الحساب (e.g. PayPal)
    institution = Column(String(100), nullable=True)  # البنك (e.g. CIB)
    category = Column(String(50), nullable=False)  # cash, checking, savings, wallet, etc.
    current_balance = Column(Numeric(12, 2), default=0.00)
    currency = Column(String(10), default="EGP")
    status = Column(String(30), default="active")  # active, inactive
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
