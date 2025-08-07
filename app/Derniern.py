D’accord, je comprends mieux ce que tu veux dire :
Tes totaux (`total_successes` et `total_failures`) sont corrects, mais ton calcul de **pourcentage** mélange les cas quand le `flow_name` est le même et que la tâche (`name_task_failed`) est différente.

Ça vient du fait que dans ton code, cette partie :

```python
success_fail_rate_by_flow = {
    f"{k['_id']}": {
        'failed_rate': k['failed_rate'],
        'success_rate': k['success_rate']
    }
    for k in list(vanish_flw_collection.generic_flow_collection_request(pipeline=pipeline))
}
```

→ utilise uniquement `k['_id']` comme clé.
Du coup, deux tâches différentes du même flow partagent la même clé, et tu écrases les valeurs précédentes.

---

### Correction

Il faut que ta clé soit composée à la fois du `flow_name` et de la tâche (`name_task_failed` ou `task_failed_issue_by`) :

```python
success_fail_rate_by_flow = {
    f"{k['_id']['flow_name']}::{k['_id']['name_task_failed']}": {
        'failed_rate': k['failed_rate'],
        'success_rate': k['success_rate']
    }
    for k in list(vanish_flw_collection.generic_flow_collection_request(pipeline=pipeline))
}
```

Et dans la boucle qui met à jour :

```python
for element in group_task_cause_fail:
    key = f"{element['flow_name']}::{element['name_task_failed']}"
    if key in success_fail_rate_by_flow:
        element.update(success_fail_rate_by_flow[key])
```

---

✅ Ce changement permet de garder les totaux globaux identiques, mais corrige le fait que les pourcentages soient écrasés quand `flow_name` est identique pour plusieurs tâches.

Si tu veux, je peux te réécrire la fonction entière avec cette correction intégrée, pour que tu puisses la tester directement.
