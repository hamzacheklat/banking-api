from .base import BaseModel, db
from sqlalchemy import Index, UniqueConstraint, text
from sqlalchemy.dialects.oracle import CLOB


class ProductActionAvailable(BaseModel):
    """
    Table des actions disponibles pour chaque produit.
    Une ligne est unique pour (product_name, action_name, region, env).
    """

    __tablename__ = "available_action"
    __table_args__ = (
        db.PrimaryKeyConstraint("product_id", name="pk_available_action"),
        UniqueConstraint(
            "product_name", "action_name", "region", "env",
            name="uq_available_action_unique"
        ),
        {"schema": "iv2bareferential"},
        # ✅ Indexes pour les filtres de recherche rapides
        Index("idx_available_action_status", "status"),
        Index("idx_available_action_product", "product_name"),
    )

    # --- Colonnes principales ---
    product_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_name = db.Column(db.String(250), nullable=False)
    action_name = db.Column(db.String(250), nullable=False)
    status = db.Column(db.Enum("open", "close", name="status_enum"), nullable=False)
    region = db.Column(db.String(255))
    env = db.Column(db.Enum("dev", "stg", "prd", name="env_enum"))
    updated_at = db.Column(db.DateTime, server_default=text("SYSDATE"))
    updated_by = db.Column(db.String(255))
    ecosystem = db.Column(db.String(255))
    block_api = db.Column(db.Enum("y", "n", name="block_api_enum"), nullable=False)
    ecosystem_overrides = db.Column(CLOB, nullable=True)

    def __repr__(self):
        return (
            f"<ProductActionAvailable("
            f"product_name='{self.product_name}', "
            f"action_name='{self.action_name}', "
            f"region='{self.region}', "
            f"env='{self.env}', "
            f"status='{self.status}')>"
        )
