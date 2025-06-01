from sqlalchemy import Column, String, Numeric, Enum, Integer, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from app.api.schemas import AccountType
from app.models.base import Base

class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True)
    account_number = Column(String(20), unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    balance = Column(Numeric(12, 2), default=0.00)
    account_type = Column(Enum(AccountType, values_callable=lambda x: [e.value for e in AccountType]))
    is_active = Column(Boolean, default=True)

    user = relationship("User", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account")

    def to_dict(self):
        return {
            "id": self.id,
            "account_number": self.account_number,
            "balance": float(self.balance),
            "account_type": self.account_type.value,
            "is_active": self.is_active
        }