from sanic import Sanic
from sanic_ext import Extend
from app.core.config import settings


def create_app() -> Sanic:
    app = Sanic("BankingAPI")

    # Configuration
    app.config.update_config(settings)

    # Extensions
    Extend(app)

    # Health check
    @app.get("/")
    async def health_check(request):
        return {"status": "healthy", "version": "1.0.0"}

    return app
