import os
import click
from product_action_service import ProductActionAvailableService

# 🔁 Replace this with your real absolute path to the 'products' directory
PRODUCTS_DIR = "/absolute/path/to/your/products"


@click.command()
def load_products_actions():
    """
    Load product actions from a predefined folder structure and insert them
    using the ProductActionAvailableService.
    """
    success_count = 0
    skipped_count = 0
    error_count = 0

    if not os.path.exists(PRODUCTS_DIR):
        click.echo(f"❌ Products directory not found: {PRODUCTS_DIR}")
        return

    # Iterate over product directories
    for product_name in os.listdir(PRODUCTS_DIR):
        product_path = os.path.join(PRODUCTS_DIR, product_name)

        if not os.path.isdir(product_path):
            continue

        actions_dir = os.path.join(product_path, "actions")
        if not os.path.exists(actions_dir):
            click.echo(f"⚠️  No 'actions/' directory found for product: {product_name}")
            continue

        # Initialize service with the current product name
        service = ProductActionAvailableService(product_name)

        for action_name in os.listdir(actions_dir):
            payload = {
                "product_name": product_name,
                "action_name": action_name,
            }

            try:
                service.create(payload)
                success_count += 1
                click.echo(f"✅ Created action '{action_name}' for product '{product_name}'")
            except ValueError:
                skipped_count += 1
                click.echo(f"⏭️ Skipped existing action '{action_name}' for product '{product_name}'")
            except Exception as e:
                error_count += 1
                click.echo(f"❌ Unexpected error for {product_name}/{action_name}: {e}")

    # Final summary
    click.echo("\n📦 Import Summary:")
    click.echo(f"  ✅ {success_count} action(s) created")
    click.echo(f"  ⏭️ {skipped_count} action(s) skipped (already exist)")
    if error_count > 0:
        click.echo(f"  ❌ {error_count} unexpected error(s)")


if __name__ == "__main__":
    load_products_actions()
