from sanic import Blueprint, HTTPResponse
from sanic_ext import validate, openapi
from sanic.exceptions import Unauthorized
from app.core.security import create_access_token
from app.models.user import User
from app.core.database import get_db
from app.api.schemas import UserLoginRequest, UserLoginResponse

auth_bp = Blueprint("auth", url_prefix="/auth")

@auth_bp.post("/login")
@validate(json=UserLoginRequest)
@openapi.definition(
    body=UserLoginRequest,
    response=UserLoginResponse,
    summary="User login",
    tag="auth"
)
async def login(request, body: UserLoginRequest):
    async with get_db() as session:
        user = await session.execute(
            select(User).where(User.email == body.email)
        )
        user = user.scalar_one_or_none()
        
        if not user or not user.verify_password(body.password):
            raise Unauthorized("Invalid credentials")
        
        token = create_access_token(user.id)
        
        return HTTPResponse.json({
            "token": token,
            "token_type": "bearer"
        })
