def update(self, status: str, filters: Dict[str, Any] = None, user_name: str = None) -> Dict[str, Any]:
    """
    Met à jour le statut (open/close) d'un produit/action pour un ou plusieurs écosystèmes.
    Ne crée jamais de nouvelle ligne. Gère aussi block_api (y → mgmt, sinon n).
    """

    self.log.start(f"update product_name='{self.product_name}'")

    criterias = {"product_name": self.product_name}
    if filters:
        criterias.update(filters)

    ecosystem = filters.get("ecosystem") if filters and "ecosystem" in filters else "all"
    block_api = filters.get("block_api") if filters else None
    status = status.lower()
    updated_instances = []

    # 1. Récupérer les 2 lignes existantes
    line_all = ProductActionAvailableModelController.filter_by_keys(
        product_name=self.product_name, ecosystem="all"
    )
    line_non_all = ProductActionAvailableModelController.filter_by_keys(
        product_name=self.product_name
    )
    line_non_all = [l for l in line_non_all if l.get("ecosystem") != "all"]

    line_all = line_all[0] if line_all else None
    line_specific = line_non_all[0] if line_non_all else None

    if not line_all or not line_specific:
        raise ValueError("Lignes attendues manquantes pour le produit. Aucune création n'est autorisée.")

    # Parser la liste des ecos existants dans la ligne spécifique
    current_eco_str = line_specific.get("ecosystem", "")
    current_eco_list = [e.strip() for e in current_eco_str.split(",") if e.strip()]

    input_eco_list = [e.strip() for e in ecosystem.split(",") if e.strip()] if ecosystem != "all" else []

    # CAS 1 : ecosystem = all
    if ecosystem == "all":
        # Met à jour les 2 lignes
        ProductActionAvailableModelController.update_by_criterias(
            criterias_kwargs={"id": line_all["id"]},
            new_values_kwargs={"status": status, "updated_by": user_name}
        )
        ProductActionAvailableModelController.update_by_criterias(
            criterias_kwargs={"id": line_specific["id"]},
            new_values_kwargs={"status": status, "ecosystem": "", "updated_by": user_name}
        )
        updated_instances.extend([line_all, line_specific])

    # CAS 2 : ecosystem spécifique
    else:
        if status == "close":
            if line_all["status"] == "open":
                # Ajouter à la liste des écosystèmes fermés
                for eco in input_eco_list:
                    if eco not in current_eco_list:
                        current_eco_list.append(eco)
            else:
                # all est déjà fermé, pas besoin de redoubler l'info
                input_eco_list = []  # rien à faire

        elif status == "open":
            if line_all["status"] == "close":
                # Exception à l'état global fermé → on ouvre certains écos
                for eco in input_eco_list:
                    if eco not in current_eco_list:
                        current_eco_list.append(eco)
                new_status = "open"
            else:
                # all est open, donc on retire l’eco de la blacklist s’il y est
                for eco in input_eco_list:
                    if eco in current_eco_list:
                        current_eco_list.remove(eco)

        # Mise à jour de la ligne spécifique
        new_eco_str = ",".join(sorted(current_eco_list))
        new_status = "close" if current_eco_list else "open"

        ProductActionAvailableModelController.update_by_criterias(
            criterias_kwargs={"id": line_specific["id"]},
            new_values_kwargs={
                "status": new_status,
                "ecosystem": new_eco_str,
                "updated_by": user_name
            }
        )
        updated_instances.append(line_specific)

    # Blocage API : toujours mis à jour
    final_block_api_value = "mgmt" if block_api == "y" else "n"

    for instance in updated_instances:
        ProductActionAvailableModelController.update_by_criterias(
            criterias_kwargs={"id": instance["id"]},
            new_values_kwargs={"block_api": final_block_api_value}
        )

    self.log.success(f"✅ updated product_name='{self.product_name}'")
    return ProductActionAvailableModelController.dump_many(updated_instances)
