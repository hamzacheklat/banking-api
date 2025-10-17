def update(self, status: str, filters: Dict[str, Any] = None, user_name: str = None) -> Dict[str, Any]:
    self.log.start(f"update product_name='{self.product_name}'")

    filters = filters or {}
    status = status.lower()
    ecosystem = filters.get("ecosystem", "all")
    block_api = filters.get("block_api")
    criterias_base = {"product_name": self.product_name, **filters}

    line_all, line_specific = self._get_existing_lines(criterias_base)
    current_eco_list = self._parse_ecosystem_list(line_specific.get("ecosystem", ""))
    input_eco_list = self._parse_ecosystem_list(ecosystem) if ecosystem != "all" else []

    if ecosystem == "all":
        self._handle_all_status_update(line_all, line_specific, status, user_name)
        updated_instances = [line_all, line_specific]
    else:
        updated_instances = self._handle_specific_ecosystem_update(
            line_all, line_specific, current_eco_list, input_eco_list, status, user_name
        )

    self._update_block_api(updated_instances, block_api)
    self.log.success(f"✅ updated product_name='{self.product_name}'")
    return ProductActionAvailableModelController.dump_many(updated_instances)

def _get_existing_lines(self, criterias_base: Dict[str, Any]):
    criterias_all = criterias_base.copy()
    criterias_all["ecosystem"] = "all"
    line_all = ProductActionAvailableModelController.filter_by_keys(**criterias_all)[0]

    criterias_non_all = criterias_base.copy()
    criterias_non_all.pop("ecosystem", None)
    all_lines = ProductActionAvailableModelController.filter_by_keys(**criterias_non_all)
    line_specific = next((line for line in all_lines if line.get("ecosystem") != "all"), None)

    if not line_all or not line_specific:
        raise ValueError("Lignes attendues manquantes pour le produit.")

    return line_all, line_specific

def _parse_ecosystem_list(self, eco_str: str) -> List[str]:
    return sorted(set(e.strip() for e in eco_str.split(",") if e.strip()))

def _handle_all_status_update(self, line_all, line_specific, status: str, user_name: str):
    ProductActionAvailableModelController.update_by_criterias(
        criterias_kwargs={"id": line_all["id"]},
        new_values_kwargs={"status": status, "updated_by": user_name}
    )
    ProductActionAvailableModelController.update_by_criterias(
        criterias_kwargs={"id": line_specific["id"]},
        new_values_kwargs={"status": status, "ecosystem": "", "updated_by": user_name}
    )

def _handle_specific_ecosystem_update(
    self, line_all, line_specific, current_eco_list: List[str], input_eco_list: List[str],
    status: str, user_name: str
) -> List[Dict[str, Any]]:

    if status == "close":
        if line_all["status"] == "open":
            current_eco_list = sorted(set(current_eco_list + input_eco_list))
        # sinon on ne change rien (global déjà fermé)
    elif status == "open":
        if line_all["status"] == "close":
            current_eco_list = sorted(set(current_eco_list + input_eco_list))
        else:
            current_eco_list = [eco for eco in current_eco_list if eco not in input_eco_list]

    new_eco_str = ",".join(current_eco_list)
    new_status = "close" if current_eco_list else "open"

    ProductActionAvailableModelController.update_by_criterias(
        criterias_kwargs={"id": line_specific["id"]},
        new_values_kwargs={
            "status": new_status,
            "ecosystem": new_eco_str,
            "updated_by": user_name
        }
    )

    return [line_specific]

def _update_block_api(self, instances: List[Dict[str, Any]], block_api: Optional[str]):
    final_block_api_value = "mgmt" if block_api == "y" else "n"
    for instance in instances:
        ProductActionAvailableModelController.update_by_criterias(
            criterias_kwargs={"id": instance["id"]},
            new_values_kwargs={"block_api": final_block_api_value}
        )
