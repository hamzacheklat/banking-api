def delete(self, action_name: str = None) -> None:
    """
    Delete one or multiple product actions.
    Returns:
        Dict[str, Any]: Serialized representation of the updated action(s).
    """
    criterias = {"product_name": self.product_name}

    if action_name:
        # Case: delete a single action
        criterias["action_name"] = action_name
        instance = ProductActionAvailableModelController.get_instance_by_keys(**criterias)
        if instance:
            instance.delete()
        return ProductActionAvailableModelController.dump_many(
            ProductActionAvailableModelController.filter_by_keys(product_name=self.product_name)
        )

    # Case: delete all actions for the product
    instances = ProductActionAvailableModelController.filter_by_keys(**criterias)
    for instance in instances:
        instance.delete()

    return ProductActionAvailableModelController.dump_many(
        ProductActionAvailableModelController.filter_by_keys(product_name=self.product_name)
    )
