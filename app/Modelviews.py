from sqlalchemy import Column, String, DateTime, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class ProductActionAvailable(Base):
    __tablename__ = "product_action_available"

    # Un produit peut avoir plusieurs actions
    # La clé primaire doit être composée de (product_name, action_name)
    product_name = Column(String(255), primary_key=True)
    action_name = Column(String(100), primary_key=True)
    status = Column(String(10), nullable=False)  # "open" ou "close"
    updated_by = Column(String(100))
    updated_at = Column(DateTime, server_default=func.sysdate(), onupdate=func.sysdate())


from models.product_action_available import ProductActionAvailable
from sqlalchemy.orm import Session

class ProductActionAvailableService:

    @staticmethod
    def get_all(session: Session):
        return session.query(ProductActionAvailable).all()

    @staticmethod
    def get_by_product(session: Session, product_name: str, status: str = None):
        query = session.query(ProductActionAvailable).filter_by(product_name=product_name)
        if status:
            query = query.filter_by(status=status)
        return query.all()

    @staticmethod
    def get_action(session: Session, product_name: str, action_name: str):
        return session.query(ProductActionAvailable).filter_by(
            product_name=product_name,
            action_name=action_name
        ).first()

    @staticmethod
    def create(session: Session, product_name: str, action_name: str, status: str, updated_by: str = None):
        action = ProductActionAvailable(
            product_name=product_name,
            action_name=action_name,
            status=status,
            updated_by=updated_by
        )
        session.add(action)
        session.commit()
        return action

    @staticmethod
    def update_status(session: Session, product_name: str, action_name: str, new_status: str, updated_by: str = None):
        action = session.query(ProductActionAvailable).filter_by(
            product_name=product_name,
            action_name=action_name
        ).first()
        if action:
            action.status = new_status
            if updated_by:
                action.updated_by = updated_by
            session.commit()
        return action

    @staticmethod
    def update_all_status(session: Session, product_name: str, new_status: str, updated_by: str = None):
        actions = session.query(ProductActionAvailable).filter_by(product_name=product_name).all()
        for action in actions:
            action.status = new_status
            if updated_by:
                action.updated_by = updated_by
        session.commit()
        return actions

    @staticmethod
    def delete(session: Session, product_name: str, action_name: str):
        action = session.query(ProductActionAvailable).filter_by(
            product_name=product_name,
            action_name=action_name
        ).first()
        if action:
            session.delete(action)
            session.commit()
        return action


from sanic import Blueprint, response
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from services.product_action_available_service import ProductActionAvailableService
from models.product_action_available import Base

# Connexion Oracle (adapter tes infos)
engine = create_engine("oracle+cx_oracle://user:password@host:1521/?service_name=MONSERVICE")
SessionLocal = sessionmaker(bind=engine)

# Création table si non existante
Base.metadata.create_all(engine)

bp_products = Blueprint("products", url_prefix="/products")

# --- GET ALL ACTIONS ---
@bp_products.get("/")
async def get_all(request):
    session = SessionLocal()
    actions = ProductActionAvailableService.get_all(session)
    session.close()
    return response.json([a.__dict__ for a in actions], default=str)


# --- GET ALL ACTIONS FOR ONE PRODUCT ---
@bp_products.get("/<product_name>")
async def get_by_product(request, product_name):
    status = request.args.get("status")  # ?status=open|close
    session = SessionLocal()
    actions = ProductActionAvailableService.get_by_product(session, product_name, status)
    session.close()
    return response.json([a.__dict__ for a in actions], default=str)


# --- GET ONE ACTION ---
@bp_products.get("/<product_name>/actions/<action_name>")
async def get_action(request, product_name, action_name):
    session = SessionLocal()
    action = ProductActionAvailableService.get_action(session, product_name, action_name)
    session.close()
    if action:
        return response.json(action.__dict__, default=str)
    return response.json({"error": "Not found"}, status=404)


# --- ADD NEW ACTION ---
@bp_products.post("/<product_name>/actions")
async def add_action(request, product_name):
    data = request.json
    session = SessionLocal()
    action = ProductActionAvailableService.create(
        session,
        product_name=product_name,
        action_name=data["action_name"],
        status=data["status"],
        updated_by=data.get("updated_by")
    )
    session.close()
    return response.json(action.__dict__, default=str)


# --- UPDATE STATUS OF ONE ACTION ---
@bp_products.patch("/<product_name>/actions/<action_name>")
async def update_status(request, product_name, action_name):
    data = request.json
    session = SessionLocal()
    action = ProductActionAvailableService.update_status(
        session,
        product_name=product_name,
        action_name=action_name,
        new_status=data["status"],
        updated_by=data.get("updated_by")
    )
    session.close()
    if action:
        return response.json(action.__dict__, default=str)
    return response.json({"error": "Not found"}, status=404)


# --- UPDATE STATUS OF ALL ACTIONS FOR A PRODUCT ---
@bp_products.patch("/<product_name>/<new_status>")
async def update_all_status(request, product_name, new_status):
    session = SessionLocal()
    actions = ProductActionAvailableService.update_all_status(
        session,
        product_name=product_name,
        new_status=new_status,
        updated_by=request.json.get("updated_by") if request.json else None
    )
    session.close()
    return response.json([a.__dict__ for a in actions], default=str)


# --- DELETE ACTION ---
@bp_products.delete("/<product_name>/actions/<action_name>")
async def delete_action(request, product_name, action_name):
    session = SessionLocal()
    action = ProductActionAvailableService.delete(session, product_name, action_name)
    session.close()
    if action:
        return response.json({"message": "Deleted"})
    return response.json({"error": "Not found"}, status=404)

