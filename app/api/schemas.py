from pydantic import BaseModel, EmailStr, Field
from enum import Enum
from typing import Optional

class AccountType(str, Enum):
    SAVINGS = "savings"
    CHECKING = "checking"
    CREDIT = "credit"

class TransactionType(str, Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRANSFER = "transfer"

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)

class UserLoginResponse(BaseModel):
    token: str
    token_type: str = "bearer"

class AccountCreateRequest(BaseModel):
    account_type: AccountType

class TransactionCreateRequest(BaseModel):
    amount: float = Field(..., gt=0)
    transaction_type: TransactionType
    to_account_id: Optional[int] = None
    description: Optional[str] = None
