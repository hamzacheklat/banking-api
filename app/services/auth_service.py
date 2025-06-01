from sqlalchemy import select
from sanic.exceptions import Unauthorized, BadRequest
from app.models.user import User
from app.core.database import async_session
from app.core.security import create_access_token


class AuthService:

    @staticmethod
    async def register_user(email: str, password: str, first_name: str, last_name: str):
        async with async_session() as session:
            existing_user = await session.execute(
                select(User).where(User.email == email)
            )
            if existing_user.scalar_one_or_none():
                raise BadRequest("Email already registered")

            # Crée un nouvel utilisateur
            user = User(
                email=email,
                first_name=first_name,
                last_name=last_name
            )
            user.set_password(password)

            session.add(user)
            await session.commit()
            await session.refresh(user)

            return user

    @staticmethod
    async def login_user(email: str, password: str):
        async with async_session() as session:
            user = await session.execute(
                select(User).where(User.email == email)
            )
            user = user.scalar_one_or_none()

            if not user or not user.verify_password(password):
                raise Unauthorized("Invalid credentials")

            if not user.is_active:
                raise Unauthorized("Account is disabled")

            token = create_access_token(user.id)

            return {
                "token": token,
                "user": user
            }
