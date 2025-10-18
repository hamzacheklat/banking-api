def update(self, status: str, filters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update product action status for the given product.
    Handles ecosystem open/close updates in the ecosystem CLOB column.
    """

    self.log.start(f"update product name='{self.product_name}'")
    criteria = {"product_name": self.product_name}

    # Retrieve ecosystems modifications from filters
    ecosystems_to_open = filters.pop("ecosystems_to_open", [])
    ecosystems_to_close = filters.pop("ecosystems_to_close", [])

    # Filter by product_name, action_name, env, region
    base_filters = {
        k: v for k, v in filters.items() if v is not None and k in ["product_name", "action_name", "env", "region"]
    }

    instances = ProductActionAvailableModelController.filter_by_keys(**base_filters)

    if not instances:
        self.log.warning(f"No instances found for {base_filters}")
        return {}

    updated_instances = []

    for inst in instances:
        try:
            # Load ecosystem JSON from DB
            eco_data = {}
            if inst.ecosystem:
                try:
                    eco_data = json.loads(inst.ecosystem)
                except Exception:
                    self.log.warning(f"Invalid JSON in ecosystem for id={inst.id}, resetting field.")
                    eco_data = {}

            # Apply opens
            for eco in ecosystems_to_open or []:
                eco_data[eco] = "open"

            # Apply closes
            for eco in ecosystems_to_close or []:
                eco_data[eco] = "close"

            # Update instance
            inst.ecosystem = json.dumps(eco_data)
            inst.status = status.lower()
            ProductActionAvailableModelController.save(inst)

            updated_instances.append(inst)

        except Exception as e:
            self.log.error(f"Error updating ecosystem for {inst.id}: {e}")

    self.log.success(f"Updated {len(updated_instances)} product actions for product='{self.product_name}'")
    return ProductActionAvailableModelController.dump_many(updated_instances)
