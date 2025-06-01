from enum import Enum as PyEnum
from sqlalchemy import Column, Numeric, Enum, Integer, ForeignKey, DateTime, String
from sqlalchemy.orm import relationship
from datetime import datetime

from app.api.schemas import TransactionType
from app.models.base import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"))
    amount = Column(Numeric(12, 2))
    transaction_type = Column(Enum(TransactionType), values_callable=lambda x: [e.value for e in TransactionType])
    to_account_id = Column(Integer, nullable=True)
    description = Column(String(200), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    account = relationship("Account", back_populates="transactions")

    def to_dict(self):
        return {
            "id": self.id,
            "account_id": self.account_id,
            "amount": float(self.amount),
            "transaction_type": self.transaction_type.value,
            "to_account_id": self.to_account_id,
            "description": self.description,
            "timestamp": self.timestamp.isoformat()
        }
