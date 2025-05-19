import jwt
from datetime import datetime, timedelta
from sanic import Request
from sanic.exceptions import Unauthorized
from app.core.config import settings

def create_access_token(user_id: int) -> str:
    payload = {
        "exp": datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES),
        "iat": datetime.utcnow(),
        "sub": user_id
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

async def protected(request: Request):
    auth_header = request.headers.get("Authorization")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        raise Unauthorized("Missing or invalid authorization header")
    
    token = auth_header.split(" ")[1]
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        request.ctx.user_id = payload.get("sub")
    except jwt.ExpiredSignatureError:
        raise Unauthorized("Token has expired")
    except jwt.InvalidTokenError:
        raise Unauthorized("Invalid token")
