import os
import click
from product_action_service import ProductActionAvailableService


@click.command()
@click.option("--products-dir", required=True, help="Chemin vers le dossier products")
def load_products_actions(products_dir: str):
    """
    Charger les produits et actions dans la table product_action_available
    en utilisant ProductActionAvailableService avec logique métier incluse.
    """
    nb_success = 0
    nb_skipped = 0
    nb_errors = 0

    for product_name in os.listdir(products_dir):
        product_path = os.path.join(products_dir, product_name)

        if not os.path.isdir(product_path):
            continue

        actions_dir = os.path.join(product_path, "actions")
        if not os.path.exists(actions_dir):
            click.echo(f"⚠️  Pas de dossier actions pour {product_name}")
            continue

        # 🔹 On instancie le service avec le nom du produit
        service = ProductActionAvailableService(product_name)

        for action_name in os.listdir(actions_dir):
            payload = {
                "product_name": product_name,
                "action_name": action_name,
            }

            try:
                service.create(payload)
                nb_success += 1
            except ValueError as e:
                # Doublon ou logique métier déclenchée
                nb_skipped += 1
            except Exception as e:
                # Autre erreur imprévue
                nb_errors += 1
                click.echo(f"❌ Erreur inattendue: {e}")

    click.echo(f"\n✅ {nb_success} action(s) insérée(s)")
    click.echo(f"⏭️ {nb_skipped} action(s) ignorée(s) (déjà existantes)")
    if nb_errors > 0:
        click.echo(f"❌ {nb_errors} erreur(s) fatale(s) rencontrée(s)")


if __name__ == "__main__":
    load_products_actions()
