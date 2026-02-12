from database import DatabasesConfig
from request import _current_request
from request import JobRequest

def run_job():
    db_name = "oracle"  # ou iv2 / sybase / mongo
    db_config = DatabasesConfig(db_name)

    session = db_config.get_session()

    token = _current_request.set(JobRequest(session))

    try:
        # 🔥 ton code EXISTANT marche sans modification
        engines = NginModelController.dump_many(NginModelController.all())
    finally:
        session.close()
        _current_request.reset(token)
