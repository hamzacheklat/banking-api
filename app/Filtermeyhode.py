import json

class ProductActionAvailableService(BaseService):

    def __init__(self, product_name=None):
        self.log = PrefixedLogger("product_action_service")
        self.log.start(f"ProductActionAvailableService with product name {product_name}")
        self.product_name = product_name.lower()

    @classmethod
    def get_filtered_products(cls, **filters):
        """
        Retrieve product actions filtered by specific criteria (+ ecosystem filtering in Python).
        If 'ecosystem' is provided, filter by its status instead of the global one.
        """

        ecosystem = filters.pop("ecosystem", None)
        status_filter = filters.get("status")  # on garde sans le pop pour réutiliser plus tard

        # 1️⃣ On récupère toutes les instances selon les autres filtres
        base_filters = {k: v for k, v in filters.items() if k != "status"}
        instances = ProductActionAvailableModelController.filter_by_keys(**base_filters)

        # 2️⃣ Si pas d’écosystème -> filtrage simple sur status global
        if not ecosystem:
            if status_filter:
                instances = [i for i in instances if i.status == status_filter]

        # 3️⃣ Si un écosystème est indiqué -> filtrage JSON
        else:
            filtered = []
            for inst in instances:
                try:
                    eco_data = json.loads(inst.ecosystems) if inst.ecosystems else {}
                except Exception:
                    eco_data = {}

                # Si la clé existe dans ecosystems et qu’on doit filtrer sur son statut
                if ecosystem in eco_data:
                    if not status_filter or eco_data[ecosystem] == status_filter:
                        filtered.append(inst)
                else:
                    # Si la clé n’existe pas, on ignore ou on garde selon ton besoin
                    # Ici on choisit d’ignorer
                    continue

            instances = filtered

        # 4️⃣ Sérialisation
        actions = ProductActionAvailableModelController.dump_many(instances)
        return actions
