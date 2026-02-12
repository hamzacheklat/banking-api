from functools import wraps
from contextvars import ContextVar
from sanic.request import Request
from config import DatabasesConfig

current_request: ContextVar = ContextVar("current_request", default=None)


def job_db(db_name: str, auto_commit: bool = False):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            db_config = DatabasesConfig(db_name)
            session = db_config.get_session()

            token = current_request.set(Request.JobRequest(session))

            try:
                result = func(*args, **kwargs)

                if auto_commit:
                    session.commit()

                return result

            except Exception:
                session.rollback()
                raise

            finally:
                session.close()
                current_request.reset(token)

        return wrapper

    return decorator
