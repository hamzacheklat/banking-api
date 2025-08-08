Oui, je vois le problème :
actuellement ton calcul du **failed\_rate** et du **success\_rate** se fait par `flow_name`, ce qui fait que si plusieurs tâches (`task_failed_name`) partagent le même `flow_name`, elles héritent toutes du même pourcentage — même si leur nombre d’échecs diffère.

En clair :

* `"_id"` dans ton pipeline Mongo correspond seulement au `flow_name`.
* Du coup, toutes les lignes avec ce `flow_name` sont agrégées ensemble, ce qui fausse le calcul.

---

### **Fix**

Il faut que l’agrégation Mongo se fasse sur **flow\_name + task\_failed\_name** pour que les calculs soient distincts.

Dans ton pipeline, modifie la partie `$group` pour avoir un `_id` qui contient les deux champs :

```python
pipeline = [
    {"$match": {
        "start_time": {
            "$lte": datetime.fromisoformat(up_date),
            "$gt": datetime.fromisoformat(down_date)
        },
        "status": {"$in": ["FAILED", "SUCCESS"]}
    }},
    {"$group": {
        "_id": {
            "flow_name": "$flow_name",
            "task_failed_name": "$task_failed_name"  # <-- ajouté
        },
        "total_successes": {
            "$sum": {"$cond": [{"$eq": ["$status", "SUCCESS"]}, 1, 0]}
        },
        "total_failures": {
            "$sum": {"$cond": [{"$eq": ["$status", "FAILED"]}, 1, 0]}
        }
    }},
    {"$project": {
        "_id": 1,
        "success_rate": {
            "$round": [
                {"$multiply": [
                    {"$divide": ["$total_successes",
                                 {"$add": ["$total_successes", "$total_failures"]}]},
                    100
                ]},
                2
            ]
        },
        "failed_rate": {
            "$round": [
                {"$multiply": [
                    {"$divide": ["$total_failures",
                                 {"$add": ["$total_successes", "$total_failures"]}]},
                    100
                ]},
                2
            ]
        }
    }}
]
```

---

### **Conséquences**

* Chaque couple `(flow_name, task_failed_name)` aura ses propres pourcentages.
* Tu devras aussi adapter le `success_fail_rate_by_flow` en Python pour que la clé d’accès inclue ces deux valeurs :

```python
success_fail_rate_by_flow = {
    (k['_id']['flow_name'], k['_id']['task_failed_name']): {
        'failed_rate': k['failed_rate'],
        'success_rate': k['success_rate']
    }
    for k in vanish_flw_collection.generic_flow_collection_request(pipeline=pipeline)
}
```

Et lors de la mise à jour :

```python
for element in group_task_cause_fail:
    key = (element['flow_name'], element['task_failed_name'])
    if key in success_fail_rate_by_flow:
        element.update(success_fail_rate_by_flow[key])
```

---

Si tu veux, je peux te réécrire **tout le bloc `get_recurrent_task_failed_flow`** déjà corrigé pour que ça marche directement avec ton code actuel.
Comme ça tu n’auras pas à chercher où adapter.
