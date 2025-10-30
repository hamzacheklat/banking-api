Parfait 👌 — tu veux donc :

➡️ Que le **rapport quotidien** s’appuie sur la **base MongoDB + index Chroma (RAG)**,
➡️ Pour **analyser automatiquement les erreurs/flows du jour**,
➡️ Et générer un **rapport lisible (Excel ou PDF)** que l’on peut aussi **envoyer par mail**.

On va donc combiner trois briques :

1. **Analyse RAG** (interprétation intelligente des erreurs du jour)
2. **Génération de rapport** (Excel ou PDF, au choix)
3. **Envoi automatique** (mail ou Slack, selon ton infra)

---

## ⚙️ Architecture complète

```
app/
├── config.py
├── vector_store.py
├── embedder.py
├── mongo_ingest.py
├── rag.py
├── litellm_client.py
└── report_generator.py  👈 (nouveau module)
```

---

## 🧩 Étape 1 : rapport basé sur le RAG

Voici le contenu du nouveau fichier `app/report_generator.py` :

```python
import pandas as pd
from datetime import datetime
from pymongo import MongoClient
from rag import answer_query
import config
import smtplib
from email.message import EmailMessage
from io import BytesIO
from openpyxl import Workbook


def fetch_flows_for_date(date_str: str):
    """
    Récupère les documents Mongo vanish_flows pour une date donnée.
    """
    client = MongoClient(config.MONGO_URI)
    db = client[config.MONGO_DB]
    col = db["vanish_flows"]

    # Format attendu du champ date dans la base (à adapter si besoin)
    query = {"DATE": {"$regex": f"^{date_str}"}}
    return list(col.find(query))


def generate_rag_summary(flow_docs):
    """
    Fait un résumé intelligent des causes d’échec du jour via RAG.
    """
    if not flow_docs:
        return "Aucune donnée pour cette date."

    joined = "\n\n".join([
        f"FLOW: {d.get('FLOW', '')}\nTASK: {d.get('TASK', '')}\nFAILURE: {d.get('FAILURE REASON', '')}"
        for d in flow_docs
    ])

    query = (
        "Analyse ces logs de flux du jour et résume : "
        "1️⃣ les types d'erreurs récurrents, "
        "2️⃣ les causes probables, "
        "3️⃣ les actions recommandées."
    )

    result = answer_query(query + "\n\n" + joined)
    return result["answer"]


def generate_excel_report(date_str: str, flow_docs, rag_summary: str):
    """
    Crée un rapport Excel complet à partir des flux + résumé RAG.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Rapport des Flows"

    # En-têtes
    headers = ["DATE", "FLOW", "TASK", "JOB_ID", "SUB_ID", "FAILURE REASON", "WHAT TO DO?"]
    ws.append(headers)

    # Données
    for doc in flow_docs:
        ws.append([
            doc.get("DATE", ""),
            doc.get("FLOW", ""),
            doc.get("TASK", ""),
            doc.get("JOB_ID", ""),
            doc.get("SUB_ID", ""),
            doc.get("FAILURE REASON", ""),
            doc.get("WHAT TO DO?", ""),
        ])

    # Ajout du résumé RAG à la fin
    ws.append([])
    ws.append(["--- Résumé RAG ---"])
    for line in rag_summary.split("\n"):
        ws.append([line])

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()


def send_report_via_email(recipient, subject, attachment_bytes, date_str):
    """
    Envoie le rapport Excel par e-mail.
    """
    msg = EmailMessage()
    msg["From"] = "rapport-vanish@tondomaine.com"
    msg["To"] = recipient
    msg["Subject"] = subject

    msg.set_content(f"Voici le rapport des flows du {date_str}.\n\nBonne journée !")

    msg.add_attachment(
        attachment_bytes,
        maintype="application",
        subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"rapport_flows_{date_str}.xlsx",
    )

    with smtplib.SMTP("smtp.tondomaine.com", 587) as server:
        server.starttls()
        server.login("rapport-vanish@tondomaine.com", "TON_MDP")
        server.send_message(msg)
        print(f"📧 Rapport envoyé à {recipient}")


def generate_daily_report(date_str=None, send_email=False, recipient=None):
    """
    Fonction principale :
    - Récupère les flows Mongo
    - Génère résumé RAG
    - Crée le rapport Excel
    - L’envoie par mail (optionnel)
    """
    if not date_str:
        date_str = datetime.now().strftime("%d/%m/%Y")

    print(f"📅 Génération du rapport du {date_str}")

    flows = fetch_flows_for_date(date_str)
    rag_summary = generate_rag_summary(flows)
    excel_bytes = generate_excel_report(date_str, flows, rag_summary)

    if send_email and recipient:
        send_report_via_email(recipient, f"Rapport des flows du {date_str}", excel_bytes, date_str)
    else:
        with open(f"rapport_flows_{date_str}.xlsx", "wb") as f:
            f.write(excel_bytes)
        print(f"✅ Rapport sauvegardé : rapport_flows_{date_str}.xlsx")


if __name__ == "__main__":
    generate_daily_report(send_email=False)
```

---

## 🧠 Fonctionnement

1. Le script **récupère les flux du jour depuis Mongo** (`DATE` = jour courant).
2. Il envoie le tout au **RAG** pour un résumé intelligent.
3. Il **génère un rapport Excel** complet (identique à tes tableaux colorés).
4. Optionnellement, il **envoie ce rapport par e-mail**.

---

## 🕐 Usage

* **Génération locale :**

  ```bash
  python app/report_generator.py
  ```

* **Envoi automatique :**

  ```bash
  python app/report_generator.py --send-email true --recipient "ops@tondomaine.com"
  ```

---

## 📊 Étape suivante possible

Si tu veux aller plus loin, je peux t’ajouter :

* Un **rapport PDF plus visuel** (avec logos, mise en couleur par flow).
* Une **intégration Slack/Teams** (pour envoyer un résumé + le fichier).
* Une **commande RAG “analyse semaine”** qui compare les jours précédents.

---

Souhaites-tu que je t’ajoute maintenant :
1️⃣ le **rapport PDF** (avec couleurs comme tes tableaux),
ou 2️⃣ l’**envoi automatique vers Slack/Teams** ?
