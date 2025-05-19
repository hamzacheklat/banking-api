from enum import Enum as PyEnum
from sqlalchemy import Column, String, Numeric, Enum, Integer, ForeignKey
from app.models.base import Base

class AccountType(PyEnum):
    SAVINGS = "savings"
    CHECKING = "checking"
    CREDIT = "credit"

class Account(Base):
    __tablename__ = "accounts"
    
    id = Column(Integer, primary_key=True)
    account_number = Column(String(20), unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    balance = Column(Numeric(12, 2), default=0.00)
    account_type = Column(Enum(AccountType))
