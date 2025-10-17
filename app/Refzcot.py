def create_product_actions(payload: Dict[str, str], logger: PrefixedLogger) -> Dict[str, Any]:
    """
    Crée des actions produit pour chaque combinaison env/région.
    Gère les cas 'all' ou autre valeur pour 'ecosystem'.
    """
    envs = ["dev", "stg", "prd"]
    regions = ["emea", "apac", "amer"]

    logger.start(f"Create product_name: {payload.get('product_name')}")
    existing = ProductActionAvailableModelController.filter_by_keys(**payload)

    if existing:
        logger.error(
            f"Product name: {payload.get('product_name')}, "
            f"Action: {payload.get('action_name')}, "
            f"Region: {payload.get('region')}, "
            f"Env: {payload.get('env')} already exists"
        )
        raise ValueError("Action already exists for this product.")

    instances = []
    ecosystem = payload.get("ecosystem")

    # Détermine les valeurs à utiliser selon l'écosystème
    if ecosystem == "all":
        ecosystems_to_create = ["", "all"]
    else:
        ecosystems_to_create = ["all", ecosystem]

    for region in regions:
        for env in envs:
            for eco in ecosystems_to_create:
                action_payload = payload.copy()
                action_payload.update({
                    "env": env,
                    "region": region,
                    "ecosystem": eco
                })
                instances.append(ProductActionAvailableModelController.create(**action_payload))

    logger.success(
        f"Created product_name: {payload.get('product_name')}, "
        f"action: {payload.get('action_name')}"
    )

    return ProductActionAvailableModelController.dump_many(instances)
