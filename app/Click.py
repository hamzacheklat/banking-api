@click.command()
def load_products_actions():
    """
    Load product actions from a folder structure like:
    products/<global>/<product>/actions
    """
    success_count = 0
    skipped_count = 0
    error_count = 0

    if not os.path.exists(PRODUCTS_DIR):
        click.echo(f"Products directory not found: {PRODUCTS_DIR}")
        return

    # Parcourt chaque dossier global (oracle, mongodb, kafka, etc.)
    for global_name in os.listdir(PRODUCTS_DIR):
        global_path = os.path.join(PRODUCTS_DIR, global_name)
        if not os.path.isdir(global_path):
            continue

        # Parcourt chaque produit dans ce dossier global
        for product_name in os.listdir(global_path):
            product_path = os.path.join(global_path, product_name)
            if not os.path.isdir(product_path):
                continue

            if product_name not in ALLOWED_PRODUCTS:
                continue

            actions_dir = os.path.join(product_path, "actions")
            if not os.path.isdir(actions_dir):
                continue  # pas d’actions → on skip

            click.echo(f"Found 'actions' for product: {product_name} (global: {global_name})")

            service = ProductActionAvailableService(product_name)

            for action_name in os.listdir(actions_dir):
                payload = {
                    "product_name": product_name,
                    "action_name": action_name,
                }
                try:
                    service.create(payload)
                    success_count += 1
                    click.echo(f"Created action '{action_name}' for product '{product_name}'")
                except ValueError:
                    skipped_count += 1
                    click.echo(f"Skipped existing action '{action_name}' for product '{product_name}'")
                except Exception as e:
                    error_count += 1
                    click.echo(f"Unexpected error for {product_name}/{action_name}: {e}")

    click.echo("\n=== Import Summary ===")
    click.echo(f"{success_count} action(s) created")
    click.echo(f"{skipped_count} action(s) skipped (already exist)")
    if error_count > 0:
        click.echo(f"{error_count} unexpected error(s)")
