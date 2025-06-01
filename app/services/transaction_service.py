from sqlalchemy import select
from sanic.exceptions import NotFound
from app.models.transaction import Transaction
from app.models.account import Account
from app.core.database import async_session


class TransactionService:

    @staticmethod
    async def verify_account_ownership(user_id: int, account_id: int):
        """Vérifie que le compte appartient à l'utilisateur"""
        async with async_session() as session:
            result = await session.execute(
                select(Account)
                .where((Account.id == account_id) & (Account.user_id == user_id))
            )
            if not result.scalar_one_or_none():
                raise NotFound("Account not found")

    @staticmethod
    async def get_transactions(account_id: int):
        """Récupère toutes les transactions d'un compte"""
        async with async_session() as session:
            result = await session.execute(
                select(Transaction)
                .where(Transaction.account_id == account_id)
                .order_by(Transaction.timestamp.desc())
            )
            return result.scalars().all()

    @staticmethod
    async def create_transaction(
            account_id: int,
            amount: float,
            transaction_type: str,
            to_account_id: int = None,
            description: str = None
    ):
        """Crée une nouvelle transaction"""
        async with async_session() as session:
            transaction = Transaction(
                account_id=account_id,
                amount=amount,
                transaction_type=transaction_type,
                to_account_id=to_account_id,
                description=description
            )
            session.add(transaction)
            await session.commit()
            await session.refresh(transaction)
            return transaction
