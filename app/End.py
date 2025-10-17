from typing import Dict, Any, List, Optional

class ProductUpdater:
    def update(self, status: str, filters: Dict[str, Any] = None, user_name: str = None) -> Dict[str, Any]:
        self.log.start(f"update product_name='{self.product_name}'")

        filters = filters or {}
        status = status.lower()
        ecosystem = filters.get("ecosystem", "all")
        block_api = filters.get("block_api")

        criterias_base = {"product_name": self.product_name}
        for k, v in filters.items():
            if k != "ecosystem":
                criterias_base[k] = v

        lines_all, lines_specific = self._get_existing_lines(criterias_base)
        updated_instances = []

        if ecosystem == "all":
            for line_all, line_specific in zip(lines_all, lines_specific):
                self._handle_all_status_update(line_all, line_specific, status, user_name, criterias_base)
                updated_instances.extend([line_all, line_specific])
        else:
            for line_all, line_specific in zip(lines_all, lines_specific):
                updated = self._handle_specific_ecosystem_update(
                    line_all,
                    line_specific,
                    self._parse_ecosystem_list(line_specific.get("ecosystem", "")),
                    self._parse_ecosystem_list(ecosystem),
                    status,
                    user_name,
                    criterias_base
                )
                updated_instances.extend(updated)

        self._update_block_api(updated_instances, block_api, criterias_base)
        self.log.success(f"✅ updated product_name='{self.product_name}'")
        return ProductActionAvailableModelController.dump_many(updated_instances)

    def _get_existing_lines(self, criterias_base: Dict[str, Any]):
        criterias_all = criterias_base.copy()
        criterias_all["ecosystem"] = "all"
        lines_all = ProductActionAvailableModelController.filter_by_keys(**criterias_all)

        criterias_non_all = criterias_base.copy()
        criterias_non_all.pop("ecosystem", None)
        all_lines = ProductActionAvailableModelController.filter_by_keys(**criterias_non_all)
        lines_specific = [line for line in all_lines if line.get("ecosystem") != "all"]

        if not lines_all or not lines_specific:
            raise ValueError("Lignes attendues manquantes pour le produit.")

        if len(lines_all) != len(lines_specific):
            raise ValueError("Le nombre de lignes 'all' et spécifiques ne correspond pas.")

        return lines_all, lines_specific

    def _parse_ecosystem_list(self, eco_str: str) -> List[str]:
        return sorted(set(e.strip() for e in eco_str.split(",") if e.strip()))

    def _handle_all_status_update(self, line_all, line_specific, status: str, user_name: str, criterias_base):
        ProductActionAvailableModelController.update_by_criterias(
            criterias_kwargs={**criterias_base, "ecosystem": "all"},
            new_values_kwargs={"status": status, "updated_by": user_name}
        )
        ProductActionAvailableModelController.update_by_criterias(
            criterias_kwargs={**criterias_base, "ecosystem": line_specific.get("ecosystem", "")},
            new_values_kwargs={"status": status, "ecosystem": "", "updated_by": user_name}
        )

    def _handle_specific_ecosystem_update(
        self, line_all, line_specific, current_eco_list: List[str], input_eco_list: List[str],
        status: str, user_name: str, criterias_base
    ) -> List[Dict[str, Any]]:

        if status == "close":
            if line_all["status"] == "open":
                current_eco_list = sorted(set(current_eco_list + input_eco_list))
        elif status == "open":
            if line_all["status"] == "close":
                current_eco_list = sorted(set(current_eco_list + input_eco_list))
            else:
                current_eco_list = [eco for eco in current_eco_list if eco not in input_eco_list]

        new_eco_str = ",".join(current_eco_list)
        new_status = "close" if current_eco_list else "open"

        ProductActionAvailableModelController.update_by_criterias(
            criterias_kwargs={**criterias_base, "ecosystem": line_specific.get("ecosystem", "")},
            new_values_kwargs={
                "status": new_status,
                "ecosystem": new_eco_str,
                "updated_by": user_name
            }
        )

        return [line_specific]

    def _update_block_api(self, instances: List[Dict[str, Any]], block_api: Optional[str], criterias_base):
        final_block_api_value = "mgmt" if block_api == "y" else "n"
        for instance in instances:
            ProductActionAvailableModelController.update_by_criterias(
                criterias_kwargs={**criterias_base, "ecosystem": instance.get("ecosystem", "")},
                new_values_kwargs={"block_api": final_block_api_value}
            )
