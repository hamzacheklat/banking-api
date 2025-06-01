from sanic import Blueprint, json
from sanic_ext import validate, openapi
from app.api.schemas import (
    UserLoginRequest,
    UserLoginResponse,
    UserRegisterRequest,
    UserResponse
)
from app.services.auth_service import AuthService

auth_bp = Blueprint("auth", url_prefix="/auth")


@auth_bp.post("/register")
@validate(json=UserRegisterRequest)
@openapi.definition(
    body=UserRegisterRequest,
    response=UserResponse,
    summary="Register new user",
    tag="auth"
)
async def register(request, body: UserRegisterRequest):
    user = await AuthService.register_user(
        email=body.email,
        password=body.password,
        first_name=body.first_name,
        last_name=body.last_name
    )

    return json({
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name
    }, status=201)


@auth_bp.post("/login")
@validate(json=UserLoginRequest)
@openapi.definition(
    body=UserLoginRequest,
    response=UserLoginResponse,
    summary="User login",
    tag="auth"
)
async def login(request, body: UserLoginRequest):
    auth_data = await AuthService.login_user(
        email=body.email,
        password=body.password
    )

    return json({
        "token": auth_data["token"],
        "token_type": "bearer",
        "user_id": auth_data["user"].id
    })
