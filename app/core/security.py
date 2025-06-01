from functools import wraps
import jwt
from datetime import datetime, timedelta
from sanic.exceptions import Unauthorized
from app.core.config import settings


def protected():
    def decorator(f):
        @wraps(f)
        async def decorated_function(request, *args, **kwargs):
            auth_header = request.headers.get("Authorization")

            if not auth_header or not auth_header.startswith("Bearer "):
                raise Unauthorized("Missing or invalid authorization header")

            token = auth_header.split(" ")[1]

            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
                request.ctx.user_id = int(payload["sub"])  # Convert to int
            except jwt.ExpiredSignatureError:
                raise Unauthorized("Token has expired")
            except jwt.InvalidTokenError:
                raise Unauthorized("Invalid token")
            except ValueError:
                raise Unauthorized("Invalid user ID format")

            return await f(request, *args, **kwargs)

        return decorated_function

    return decorator


def create_access_token(user_id: int) -> str:
    payload = {
        "exp": datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES),
        "iat": datetime.utcnow(),
        "sub": str(user_id)  # Convert to string for JWT compliance
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
