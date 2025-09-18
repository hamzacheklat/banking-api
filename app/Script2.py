import os
import click
from sqlalchemy.orm import Session

# Importer ton modèle déjà existant
from models.product_action_available import ProductActionAvailable
from db import SessionLocal  # à adapter selon ton projet

# Racine des produits
PRODUCTS_DIR = "./products"

# Régions et environnements
REGIONS = ["emea", "amer", "apac"]
ENVS = ["dev", "stg", "prd"]

# Produits à inclure
ALLOWED_PRODUCTS = [
    "mongodb",
    "oracle",
    "postgresql",
    "sql_server",
    "sybase_ase",
    "sybase_iq",
]

@click.group()
def cli():
    """CLI pour gérer product_action_available"""
    pass

@cli.command()
def populate():
    """Remplit la table product_action_available avec les produits/actions filtrés"""
    db: Session = SessionLocal()

    for product in os.listdir(PRODUCTS_DIR):
        if product not in ALLOWED_PRODUCTS:
            continue  # on ignore les produits non listés

        product_path = os.path.join(PRODUCTS_DIR, product)
        actions_path = os.path.join(product_path, "cluster", "actions")

        if os.path.isdir(actions_path):
            for action in os.listdir(actions_path):
                action_path = os.path.join(actions_path, action)
                if os.path.isdir(action_path):
                    for region in REGIONS:
                        for env in ENVS:
                            entry = ProductActionAvailable(
                                product_name=product,
                                action_name=action,
                                region=region,
                                env=env,
                                status="open"
                            )
                            db.add(entry)
                            click.echo(f"Ajouté: {product} - {action} - {region} - {env}")

    db.commit()
    db.close()
    click.echo("✅ Remplissage terminé")

if __name__ == "__main__":
    cli()
