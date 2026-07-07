import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Numeric, ForeignKey
from ..database import Base

def generate_uuid():
    return str(uuid.uuid4())

class IncomeEntry(Base):
    __tablename__ = "income"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    source_name = Column(String(100), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(10), default="EGP")
    date = Column(DateTime, nullable=False)
    status = Column(String(30), default="received")  # received, expected
    platform = Column(String(50), nullable=True)  # Upwork, Fiverr, Direct, etc.
    month = Column(DateTime, nullable=False)  # أول يوم في الشهر (للتجميع)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
