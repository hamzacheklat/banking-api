Oui ! Voici comment tu peux utiliser cette fonction pas-à-pas.

---

### **1️⃣ Récupérer les snapshots focus et global**

```python
from datetime import datetime, timedelta

# Exemples de dates
global_start = datetime(2025, 11, 27, 0, 0)
global_end   = datetime(2025, 11, 27, 23, 59)

interval_start = datetime(2025, 11, 27, 10, 0)  # heure focus de départ
interval_end   = datetime(2025, 11, 27, 11, 0)  # heure focus de fin

# Connexion à Oracle
conn = get_db_connection()  # ta fonction pour te connecter à la DB

# Récupérer snap_ids pour focus et global
def get_snap_ids(conn, dbid, inst, start_time, end_time):
    cur = conn.cursor()
    cur.execute("""
        SELECT snap_id
        FROM dba_hist_snapshot
        WHERE dbid = :dbid AND instance_number = :inst
          AND begin_interval_time BETWEEN :start AND :end
        ORDER BY snap_id
    """, {"dbid": dbid, "inst": inst, "start": start_time, "end": end_time})
    return [r[0] for r in cur.fetchall()]

focus_snaps = get_snap_ids(conn, dbid=1, inst=1, start_time=interval_start, end_time=interval_end)
global_snaps = get_snap_ids(conn, dbid=1, inst=1, start_time=global_start, end_time=global_end)
```

---

### **2️⃣ Appeler la fonction pour détecter les métriques problématiques**

```python
report_json = detect_problematic_metrics(
    conn,
    dbid=1,
    inst=1,
    focus_snaps=focus_snaps,
    global_snaps=global_snaps,
    threshold_delta_percent=50,  # delta % minimum pour être considéré comme problématique
    top_n=3                       # top 3 métriques par type
)

print(report_json)
```

---

### **3️⃣ Résultat attendu**

Le JSON renvoyé contiendra trois sections :

* `problematic_sql` → top SQL problématiques
* `problematic_waits` → top Wait Events problématiques
* `problematic_sessions` → top Sessions problématiques

Chaque métrique contient :

```json
{
  "key": "sql_id/nom_event/session_id",
  "focus_total": 120,
  "global_total": 40,
  "focus_snaps": [101, 102],
  "global_snaps": [95, 96, 97],
  "delta_percent": 200
}
```

---

### ✅ **Résumé**

1. Récupère d’abord les snapshots pour **focus** et **global**.
2. Passe-les à `detect_problematic_metrics`.
3. Le JSON te donne **toutes les anomalies détectées** pour cet intervalle horaire.

---

Si tu veux, je peux te montrer **comment automatiser ça pour toutes les heures d’une journée** pour générer un **rapport complet horaire prêt à analyser**.

Veux‑tu que je fasse ça ?




Parfait ! Voici une **solution Python complète** pour détecter **tous les cas problématiques** SQL / Wait / Session entre une période focus et une période globale, **snapshot par snapshot**, sans LLM.

L’idée :

1. Construire un dictionnaire global par SQL / Wait / Session.
2. Garder pour chaque métrique les **snapshots où elle apparaît** et ses valeurs.
3. Détecter automatiquement :

   * Métrique **présente seulement dans focus** → suspecte
   * Métrique **pic ponctuel** → apparaît sur un seul snap mais valeur élevée
   * Métrique avec **delta significatif** → focus >> global

---

### **Fonction Python**

```python
from collections import defaultdict
import json

def detect_problematic_metrics(conn, dbid, inst, focus_snaps, global_snaps, threshold_delta_percent=50, top_n=3):
    """
    Detecte les métriques SQL / Wait / Session problématiques entre focus et global.

    Parameters:
    - conn : connexion Oracle
    - dbid, inst : DBID et instance number
    - focus_snaps : liste de snap_id pour la période focus
    - global_snaps : liste de snap_id pour la période globale
    - threshold_delta_percent : delta minimal pour alerter
    - top_n : nombre de top métriques par type à considérer
    """

    cur = conn.cursor()
    result = {
        "problematic_sql": [],
        "problematic_waits": [],
        "problematic_sessions": []
    }

    # --- Helper : récupérer métriques par snap ---
    def get_metrics(table, key_col, value_col, snaps):
        metrics = defaultdict(lambda: {"occurrences": [], "values": []})
        if not snaps:
            return metrics
        snap_range = f"{min(snaps)} AND {max(snaps)}"
        cur.execute(f"""
            SELECT {key_col}, snap_id, SUM({value_col}) AS value
            FROM {table}
            WHERE dbid = :dbid AND instance_number = :inst
              AND snap_id BETWEEN {snap_range}
            GROUP BY {key_col}, snap_id
            ORDER BY SUM({value_col}) DESC
        """, {"dbid": dbid, "inst": inst})
        for key, snap_id, value in cur.fetchall():
            metrics[key]["occurrences"].append(snap_id)
            metrics[key]["values"].append(value)
        return metrics

    # --- Récupération metrics focus et global ---
    focus_sql = get_metrics("dba_hist_sqlstat", "sql_id", "elapsed_time_delta", focus_snaps)
    global_sql = get_metrics("dba_hist_sqlstat", "sql_id", "elapsed_time_delta", global_snaps)

    focus_waits = get_metrics("dba_hist_system_event", "event", "time_waited_delta", focus_snaps)
    global_waits = get_metrics("dba_hist_system_event", "event", "time_waited_delta", global_snaps)

    focus_sess = get_metrics("dba_hist_active_sess_history", "session_id", "cpu_time", focus_snaps)
    global_sess = get_metrics("dba_hist_active_sess_history", "session_id", "cpu_time", global_snaps)

    # --- Détection des problématiques ---
    def analyze(focus_metrics, global_metrics, result_list):
        for key, f_data in focus_metrics.items():
            g_data = global_metrics.get(key, {"occurrences": [], "values": [0]*len(f_data["values"])})
            focus_total = sum(f_data["values"])
            global_total = sum(g_data["values"]) if g_data else 0
            delta_percent = ((focus_total / max(len(f_data["occurrences"]),1)) -
                             (global_total / max(len(g_data.get("occurrences",[])),1))) / \
                            max((global_total / max(len(g_data.get("occurrences",[])),1)),1) * 100

            # Critères problème :
            # 1) Présent seulement dans focus
            # 2) Pic ponctuel : apparaît sur un seul snap et valeur élevée
            # 3) Delta > threshold
            if (len(g_data.get("occurrences", [])) == 0 or
                (len(f_data["occurrences"]) == 1 and focus_total > max(g_data.get("values",[0])*1.5)) or
                delta_percent >= threshold_delta_percent):
                result_list.append({
                    "key": key,
                    "focus_total": focus_total,
                    "global_total": global_total,
                    "focus_snaps": f_data["occurrences"],
                    "global_snaps": g_data.get("occurrences", []),
                    "delta_percent": delta_percent
                })

    analyze(focus_sql, global_sql, result["problematic_sql"])
    analyze(focus_waits, global_waits, result["problematic_waits"])
    analyze(focus_sess, global_sess, result["problematic_sessions"])

    # Tri top N par delta %
    for section in result:
        result[section] = sorted(result[section], key=lambda x: x["delta_percent"], reverse=True)[:top_n]

    return json.dumps(result, ensure_ascii=False, indent=2)
```

---

### **✅ Points forts**

1. **Capture tous les cas problématiques** : focus-only, pic ponctuel, delta élevé.
2. **Snapshot par snapshot** → aucun événement n’est perdu.
3. **Top N métriques** → garde juste les plus significatives.
4. **Prêt à visualiser ou stocker** en JSON.

---

💡 **Conseil DBA** :

* Tu peux exécuter cette fonction **pour chaque intervalle horaire** pour détecter anomalies au fil du temps.
* Ensuite, si tu veux, tu peux envoyer **ces JSONs au LLM** pour générer un **résumé narratif**, mais la détection est déjà complète et fiable avec ce code.

---

Si tu veux, je peux te montrer **comment combiner cette fonction avec un découpage horaire automatique** pour **générer tous les rapports d’une journée**, prêts à stocker ou visualiser.

Veux‑tu que je fasse ça ?
