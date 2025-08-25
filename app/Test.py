def get_filtered_products(self, filters, field_to_exclude: str | None = "product_name"):
    """
    Retrieve product actions filtered by specific criteria.

    Args:
        filters (Dict[str, Any]): Un dictionnaire de critères de filtrage.
        field_to_exclude (str | None): Le champ à exclure de chaque action. 
            Si None, pas d'exclusion. Par défaut : "product_name".

    Returns:
        List[Dict[str, Any]]: La liste des actions sérialisées, sans le champ exclu (si fourni).
    """
    if "status" in filters:
        filters["status"] = filters["status"].lower()

    raw_data = ProductActionAvailableModelController.filter_by_keys(
        product_name=self.product_name,
        **filters
    )
    dumped_data = ProductActionAvailableModelController.dump_many(raw_data)

    if field_to_exclude is None:
        return dumped_data
    else:
        return [
            {k: v for k, v in action.items() if k != field_to_exclude}
            for action in dumped_data
        ]
