from sanic import json, Blueprint
from sanic.views import HTTPMethodView
from sanic_ext import validate, openapi

from app.api.schemas import TransactionCreateRequest, TransactionResponse
from app.core.security import protected
from app.services.transaction_service import TransactionService

transactions_bp = Blueprint("transactions", url_prefix="/transactions")


class TransactionView(HTTPMethodView):
    decorators = [protected()]

    async def get(self, request, account_id: int):
        """Liste des transactions d'un compte"""
        user_id = request.ctx.user_id
        await TransactionService.verify_account_ownership(user_id, account_id)
        transactions = await TransactionService.get_transactions(account_id)
        return json([tx.to_dict() for tx in transactions])

    @validate(json=TransactionCreateRequest)
    @openapi.definition(
        body=TransactionCreateRequest,
        response=TransactionResponse,
        summary="Create transaction",
        tag="transactions"
    )
    async def post(self, request, account_id: int, body: TransactionCreateRequest):
        """Création d'une transaction"""
        user_id = request.ctx.user_id
        await TransactionService.verify_account_ownership(user_id, account_id)

        transaction = await TransactionService.create_transaction(
            account_id=account_id,
            amount=body.amount,
            transaction_type=body.transaction_type,
            to_account_id=body.to_account_id,
            description=body.description
        )

        return json(transaction.to_dict(), status=201)


transactions_bp.add_route(TransactionView.as_view(), "/<account_id:int>")