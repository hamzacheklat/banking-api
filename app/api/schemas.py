from pydantic import BaseModel, EmailStr, Field
from enum import Enum
from typing import Optional
from datetime import datetime
from enum import Enum as PyEnum


class AccountType(PyEnum):
    SAVINGS = "SAVINGS"
    CHECKING = "CHECKING"
    CREDIT = "CREDIT"

class TransactionType(str, Enum):
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    TRANSFER = "TRANSFER"

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)

class UserLoginResponse(BaseModel):
    token: str
    token_type: str = "bearer"
    user_id: int

class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str = Field(..., min_length=2)
    last_name: str = Field(..., min_length=2)

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    first_name: str
    last_name: str

class AccountCreateRequest(BaseModel):
    account_type: AccountType

class AccountResponse(BaseModel):
    id: int
    account_number: str
    balance: float
    account_type: AccountType
    is_active: bool

class AccountListResponse(BaseModel):
    accounts: list[AccountResponse]

class TransactionCreateRequest(BaseModel):
    amount: float = Field(..., gt=0, example=100.00)
    transaction_type: TransactionType
    to_account_id: Optional[int] = Field(None, example=2)
    description: Optional[str] = Field(None, example="Monthly rent payment")

class TransactionResponse(BaseModel):
    id: int
    account_id: int
    amount: float
    transaction_type: TransactionType
    to_account_id: Optional[int]
    description: Optional[str]
    timestamp: datetime

class TransactionListResponse(BaseModel):
    transactions: list[TransactionResponse]