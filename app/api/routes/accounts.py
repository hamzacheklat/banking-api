from sanic import json, Blueprint
from sanic.views import HTTPMethodView
from sanic_ext import validate, openapi

from app.api.schemas import AccountCreateRequest, AccountResponse
from app.core.security import protected
from app.services.account_service import AccountService

accounts_bp = Blueprint("accounts", url_prefix="/accounts")

class AccountView(HTTPMethodView):
    decorators = [protected()]

    async def get(self, request):
        """Get all accounts for the authenticated user"""
        user_id = request.ctx.user_id
        accounts = await AccountService.get_user_accounts(user_id)
        return json([account.to_dict() for account in accounts])

    @validate(json=AccountCreateRequest)
    @openapi.definition(
        body=AccountCreateRequest,
        response=AccountResponse,
        summary="Create new account",
        tag="accounts"
    )
    async def post(self, request, body: AccountCreateRequest):
        """Create a new account for the authenticated user"""
        user_id = request.ctx.user_id
        account = await AccountService.create_account(user_id, body.account_type)
        return json(account.to_dict(), status=201)

# Register the view
accounts_bp.add_route(AccountView.as_view(), "/")