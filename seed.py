import asyncio
from sqlalchemy import insert, delete
from app.core.database import engine
from app.models.base import Base
from app.models.user import User
from app.models.account import Account, AccountType
from app.models.transaction import Transaction, TransactionType
from datetime import datetime, timedelta


async def seed_data():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    users = [
        {
            "email": "client1@banque.com",
            "password_hash": generate_password_hash("motdepasse"),
            "first_name": "Jean",
            "last_name": "Dupont",
            "is_active": True
        },
        {
            "email": "client2@banque.com",
            "password_hash": generate_password_hash("motdepasse"),
            "first_name": "Marie",
            "last_name": "Martin",
            "is_active": True
        },
        {
            "email": "admin@banque.com",
            "password_hash": generate_password_hash("admin123"),
            "first_name": "Admin",
            "last_name": "System",
            "is_active": True
        }
    ]

    accounts = [
        {"account_number": "FR7630001007941234567890185", "user_id": 1, "balance": 1500.00,
         "account_type": AccountType.CHECKING.value, "is_active": True},
        {"account_number": "FR7630001007949876543210186", "user_id": 1, "balance": 5000.00,
         "account_type": AccountType.SAVINGS.value, "is_active": True},
        {"account_number": "FR7630001007945555555550187", "user_id": 2, "balance": 300.00,
         "account_type": AccountType.CHECKING.value, "is_active": True},
        {"account_number": "FR7630001007949999999990188", "user_id": 3, "balance": 10000.00,
         "account_type": AccountType.CREDIT.value, "is_active": True}
    ]

    transactions = [
        {"account_id": 1, "amount": 100.00, "transaction_type": TransactionType.DEPOSIT.value,
         "description": "Dépôt initial", "timestamp": datetime.now() - timedelta(days=2)},
        {"account_id": 1, "amount": 50.00, "transaction_type": TransactionType.WITHDRAWAL.value,
         "description": "Retrait DAB", "timestamp": datetime.now() - timedelta(days=1)},
        {"account_id": 2, "amount": 200.00, "transaction_type": TransactionType.TRANSFER.value,
         "to_account_id": 1, "description": "Virement mensuel", "timestamp": datetime.now()},
        {"account_id": 4, "amount": 1000.00, "transaction_type": TransactionType.DEPOSIT.value,
         "description": "Dépôt admin", "timestamp": datetime.now() - timedelta(hours=1)}
    ]

    async with engine.begin() as conn:
        await conn.execute(delete(Transaction))
        await conn.execute(delete(Account))
        await conn.execute(delete(User))

        await conn.execute(insert(User), users)
        await conn.execute(insert(Account), accounts)
        await conn.execute(insert(Transaction), transactions)

        print("Base de données réinitialisée avec succès!")
        print(f"{len(users)} utilisateurs créés")
        print(f"{len(accounts)} comptes créés")
        print(f"{len(transactions)} transactions créées")


def generate_password_hash(password):
    """Génère un hash cohérent pour tous les mots de passe"""
    from werkzeug.security import generate_password_hash
    return generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)


if __name__ == "__main__":
    asyncio.run(seed_data())