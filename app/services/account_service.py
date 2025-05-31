from decimal import Decimal
from app.models.account import Account
from app.core.database import get_db
from app.utils.helpers import generate_account_number

class AccountService:
    @staticmethod
    async def create_account(user_id: int, account_type: str):
        async with get_db() as session:
            account = Account(
                user_id=user_id,
                account_number=generate_account_number(),
                account_type=account_type,
                balance=Decimal("0.00")
            )
            session.add(account)
            await session.commit()
            await session.refresh(account)
            return account
    
    @staticmethod
    async def get_user_accounts(user_id: int):
        async with get_db() as session:
            result = await session.execute(
                select(Account).where(Account.user_id == user_id)
            )
            return result.scalars().all()
