🔥 Excellente remarque — tu as parfaitement raison.

Actuellement, dans le code que je t’ai donné pour `daily_report.py`, le résumé RAG est trop **générique** :

```python
summary_prompt = "Analyse les tendances et causes principales des jobs échoués récents."
```

👉 Il ne tient **pas compte du contenu réel** du DataFrame issu de `fetch_failed_jobs_last_24h()`.
Résultat : le LLM n’a pas accès aux erreurs précises du jour, donc il ne peut pas faire une vraie analyse contextuelle.

---

## ✅ Voici la version **corrigée et complète**

Elle passe le contenu de `fetch_failed_jobs_last_24h()` au LLM (RAG), sous une forme concise et contextuelle.
Elle combine **résumé factuel + interprétation historique via embeddings.**

---

### 📊 `daily_report.py` (version améliorée)

```python
from datetime import datetime, timedelta
from pymongo import MongoClient
import pandas as pd
from rag import answer_query
import config

def fetch_failed_jobs_last_24h():
    client = MongoClient(config.MONGO_URI)
    db = client[config.MONGO_DB]
    col = db["vanish_flows"]

    now = datetime.utcnow()
    start = now - timedelta(hours=24)

    query = {
        "DATE": {"$gte": start.strftime("%Y-%m-%d"), "$lte": now.strftime("%Y-%m-%d")},
        "$or": [{"STATUS": "FAILED"}, {"FAILURE REASON": {"$ne": None}}],
    }

    docs = list(col.find(query))
    if not docs:
        return pd.DataFrame()

    records = []
    for d in docs:
        records.append({
            "DATE": d.get("DATE"),
            "FLOW": d.get("FLOW"),
            "TASK": d.get("TASK"),
            "JOB_ID": d.get("JOB_ID"),
            "SUB_ID": d.get("SUB_ID"),
            "ORIGIN": d.get("ORIGIN") or d.get("SOURCE"),
            "FAILURE_REASON": d.get("FAILURE REASON"),
            "WHAT_TO_DO": d.get("WHAT TO DO?"),
            "IS_SIMPLE_FIX": "✅" if d.get("WHAT TO DO?") and "restart" in str(d.get("WHAT TO DO?")).lower() else "❌",
            "TOWER_URL": d.get("TOWER_URL") or d.get("URL"),
        })

    df = pd.DataFrame(records)
    df.sort_values(by="DATE", ascending=False, inplace=True)
    return df


def format_jobs_for_llm(df: pd.DataFrame, limit: int = 50) -> str:
    """
    Formate les jobs échoués pour être compréhensibles par le LLM.
    On limite à 50 lignes pour éviter un prompt trop long.
    """
    subset = df.head(limit)
    lines = []
    for _, row in subset.iterrows():
        lines.append(
            f"[{row['DATE']}] FLOW={row['FLOW']} | TASK={row['TASK']} | JOB={row['JOB_ID']} | "
            f"SUB={row['SUB_ID']} | ORIGIN={row['ORIGIN']} | FAILURE={row['FAILURE_REASON']} | "
            f"ACTION={row['WHAT_TO_DO']} | SIMPLE_FIX={row['IS_SIMPLE_FIX']} | URL={row['TOWER_URL']}"
        )
    return "\n".join(lines)


def generate_excel_report():
    df = fetch_failed_jobs_last_24h()
    if df.empty:
        print("Aucun job échoué dans les dernières 24h.")
        return

    # 🧠 Contexte réel : logs du jour à analyser
    formatted_jobs = format_jobs_for_llm(df)

    # 🔍 Analyse contextuelle avec RAG
    analysis_prompt = f"""
Tu es un assistant d'analyse des pipelines de données Vanish.
Voici la liste des jobs échoués des dernières 24h :
{formatted_jobs}

Ta mission :
1️⃣ Identifier les jobs les plus problématiques ou récurrents
2️⃣ Déterminer les causes probables par famille (SQL, Oracle, VMware, etc.)
3️⃣ Indiquer les actions correctives les plus pertinentes
4️⃣ Croiser avec l’historique (embeddings) pour voir si ces erreurs sont déjà connues
5️⃣ Produire un résumé global clair et concis

Donne ta réponse dans la même langue que la question.
    """

    rag_result = answer_query(analysis_prompt)
    summary_text = rag_result["answer"]

    # 💾 Génération du rapport Excel
    output_path = f"rapport_flows_{datetime.now().strftime('%Y%m%d')}.xlsx"
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Failed Jobs")

        # Ajouter un résumé analytique sur une autre feuille
        summary_df = pd.DataFrame({"Analyse des échecs (RAG)": [summary_text]})
        summary_df.to_excel(writer, index=False, sheet_name="Résumé")

    print(f"✅ Rapport généré avec analyse : {output_path}")


if __name__ == "__main__":
    generate_excel_report()
```

---

## ⚙️ Ce qui change

| Avant                                          | Maintenant                                                        |
| ---------------------------------------------- | ----------------------------------------------------------------- |
| `summary_prompt` était générique               | Le LLM reçoit les jobs des dernières 24h                          |
| Le résumé ne tenait pas compte du contenu réel | Le LLM lit les vrais jobs échoués et les relie à l’historique RAG |
| Pas de contextualisation                       | Prompt enrichi : famille, cause, action, comparaison historique   |
| Risque de réponses vagues                      | Réponses précises, alignées sur les logs du jour                  |

---

### 💡 Exemple de réponse générée par le RAG :

```
📊 Synthèse du 30/10/2025

🔁 Erreurs fréquentes :
- SQLServer : 4 échecs sur le même cluster (authentification échouée)
- VMWare : 2 jobs échoués sur le même datastore saturé
- Oracle Apex : timeout récurrent sur bucket distant

⚙️ Causes probables :
- Credentials expirés pour le compte SQL_PROD
- Manque d’espace disque temporaire sur l’hôte vm1prd
- Connexion S3 instable depuis APEX

🧩 Actions recommandées :
- Relancer les jobs SQL après reset des credentials
- Libérer espace ou déplacer datastore VMWare
- Vérifier latence réseau côté APEX

🧠 Historique :
Ces erreurs SQL et Oracle ont déjà été observées 3 fois ce mois-ci.
```

---

## 🧩 Résumé général

✅ `rag.py` → Chatbot libre (tu poses n’importe quelle question historique)
✅ `daily_report.py` → Rapport automatique qui :

* lit Mongo
* assemble les jobs échoués des 24h
* les passe au LLM (avec RAG contextuel historique)
* sort un Excel propre avec résumé analytique

---

Souhaites-tu que je te fasse la version **Flask + React (interface web)** pour ce rapport et ton chatbot RAG ensuite ?
(je peux te faire un front avec deux onglets : “RAG Chat” et “Rapport Quotidien”).
