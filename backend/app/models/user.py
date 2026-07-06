import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Numeric
from sqlalchemy.dialects.postgresql import UUID
from ..database import Base

# دالة لتوليد الـ string UUID المتوافق مع SQLite والـ PostgreSQL
def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    profile_type = Column(String(50), default="inconsistent")  # stable, growing, inconsistent, struggling
    primary_skill = Column(String(100), nullable=True)
    avg_monthly_income = Column(Numeric(12, 2), default=0.00)
    joined_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
