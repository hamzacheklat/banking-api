def create_product_actions(payload: Dict[str, str], logger: PrefixedLogger) -> Dict[str, Any]:
    """
    Create a new product action for the given product.
    Returns:
        Dict[str, Any]: Serialized representation of the created action.
    Raises:
        ValueError: If the action already exists for this product.
    """
    envs = ["dev", "stg", "prd"]
    regions = ["emea", "apac", "amer"]

    logger.start(f"create product_name='{payload.get('product_name')}'")
    existing = ProductActionAvailableModelController.filter_by_keys(**payload)
    if existing:
        logger.error(
            f"product_name='{payload.get('product_name')}', "
            f"action='{payload.get('action_name')}', "
            f"region='{payload.get('region')}', "
            f"env='{payload.get('env')}' already exists"
        )
        raise ValueError("Action already exists for this product.")

    instances = []

    # Boucle principale pour regions x envs
    for region in regions:
        for env in envs:
            payload.update({"env": env, "region": region})

            # 1. Ecosystem = valeur par défaut (si existante dans payload)
            instances.append(ProductActionAvailableModelController.create(**payload))

            # 2. Ecosystem = 'all'
            payload_with_all = payload.copy()
            payload_with_all["ecosystem"] = "all"
            instances.append(ProductActionAvailableModelController.create(**payload_with_all))

            # 3. Ecosystem = None
            payload_with_none = payload.copy()
            payload_with_none["ecosystem"] = None
            instances.append(ProductActionAvailableModelController.create(**payload_with_none))

    logger.success(
        f"created product_name='{payload.get('product_name')}', "
        f"action='{payload.get('action_name')}'"
    )
    return ProductActionAvailableModelController.dump_many(instances)
