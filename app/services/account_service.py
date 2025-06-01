from sqlalchemy import select
from app.models.account import Account
from app.core.database import async_session


class AccountService:

    @staticmethod
    async def get_user_accounts(user_id: int):
        async with async_session() as session:
            result = await session.execute(
                select(Account).where(Account.user_id == user_id))
            return result.scalars().all()

    @staticmethod
    async def create_account(user_id: int, account_type: str):
        async with async_session() as session:
            account = Account(
                user_id=user_id,
                account_type=account_type,
                balance=0.00,
                is_active=True
            )
            session.add(account)
            await session.commit()
            await session.refresh(account)
            return account
