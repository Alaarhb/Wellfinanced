import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Numeric, Integer, ForeignKey
from ..database import Base

def generate_uuid():
    return str(uuid.uuid4())

class Debt(Base):
    __tablename__ = "debts"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    debt_name = Column(String(100), nullable=False)
    total_amount = Column(Numeric(12, 2), nullable=False)
    remaining_amount = Column(Numeric(12, 2), nullable=False)
    monthly_payment = Column(Numeric(12, 2), nullable=False)  # الحد الأدنى للقسط
    interest_rate = Column(Numeric(5, 2), default=0.00)
    due_date = Column(DateTime, nullable=False)
    priority = Column(Integer, default=1)  # ترتيب أولوية يدوي من اليوزر
    status = Column(String(30), default="active")  # active, paid, overdue
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
