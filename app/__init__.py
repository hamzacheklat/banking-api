from sanic import Sanic
from sanic_ext import Extend
from app.core.config import settings
from app.api.routes import auth_bp, accounts_bp, transactions_bp


def create_app() -> Sanic:
    app = Sanic("BankingAPI")

    # Configuration
    app.config.update_config(settings)

    Extend(app)

    app.blueprint(auth_bp)
    app.blueprint(accounts_bp)
    app.blueprint(transactions_bp)

    # Health check
    @app.get("/")
    async def health_check(request):
        return {"status": "healthy", "version": "1.0.0"}

    return app