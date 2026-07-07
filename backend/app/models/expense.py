import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Numeric, Boolean, ForeignKey
from ..database import Base

def generate_uuid():
    return str(uuid.uuid4())

class Expense(Base):
    __tablename__ = "expenses"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(String(50), nullable=False)  # rent, food, etc.
    amount = Column(Numeric(12, 2), nullable=False)
    expense_date = Column(DateTime, nullable=False)
    month = Column(DateTime, nullable=False)  # أول يوم في الشهر (للتجميع)
    is_recurring = Column(Boolean, default=False)
    recurrence_rule = Column(String(100), nullable=True)  # monthly, weekly, etc.
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
