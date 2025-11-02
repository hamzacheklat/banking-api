Parfait 💪 tu vas adorer cette version — on va rendre ton **RAG LangChain conversationnel**, donc il retiendra **le contexte des questions précédentes** (comme un vrai assistant d’analyse des jobs).

---

# 🧠 Objectif

✅ Ton RAG reste basé sur les embeddings Chroma.
✅ On ajoute une **mémoire conversationnelle** via LangChain (`ConversationBufferMemory`).
✅ L’assistant comprend les suivis contextuels :

> “Et celui d’hier ?” ou “Et le flow X ?” après une première question.
> ✅ Le tout sans perdre la logique du prompt et de la recherche.

---

## 📂 Fichier mis à jour : `rag_langchain.py`

Voici **la version complète** et à jour, prête à remplacer ton fichier actuel :

```python
from datetime import datetime
from langchain_community.chat_models import ChatLiteLLM
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from vector_store import get_vanish_vectorstore
import config


# 🧠 1. Initialisation du vector store et du retriever
vectorstore = get_vanish_vectorstore()
retriever = vectorstore.as_retriever(search_kwargs={"k": 8})

# 💬 2. Initialisation du modèle
llm = ChatLiteLLM(model=config.LITELLM_MODEL, api_key=config.LITELLM_API_KEY)

# 🧩 3. Prompt contextuel et bilingue
template = """
You are a specialized assistant that analyzes failed job flows from system logs and MongoDB data.
Today's date is {today}.

You are talking to a user who might ask follow-up questions, so remember context from previous turns.

If the user speaks French, respond in French.
If the user speaks English, respond in English.

Use the context provided to answer precisely and clearly.

Each record in the database includes:
FLOW, TASK, JOB_ID, FAILURE REASON, WHAT TO DO, START_TIME, END_TIME, ORIGIN, and potentially Tower URL.

Summarize with:
- Which flows or jobs failed and when
- Recurring patterns if any
- Impact and cause (origin)
- Recommended actions (WHAT TO DO)
- Add context from previous conversation if relevant

-------------------
Context from DB:
{context}
-------------------

Question:
{question}

Answer:
"""

prompt = PromptTemplate(
    input_variables=["today", "context", "question"],
    template=template
)

# 🧠 4. Mémoire conversationnelle
memory = ConversationBufferMemory(
    memory_key="chat_history",
    return_messages=True,
)

# 🪄 5. Construction du RAG conversationnel
qa_chain = ConversationalRetrievalChain.from_llm(
    llm=llm,
    retriever=retriever,
    memory=memory,
    combine_docs_chain_kwargs={"prompt": prompt}
)

# 🚀 6. Fonction principale
def answer_query(query: str):
    today = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    response = qa_chain.invoke({
        "today": today,
        "question": query
    })
    return {
        "query": query,
        "answer": response["answer"],
        "date": today
    }


# 🧪 Test local
if __name__ == "__main__":
    print("Assistant conversationnel RAG 🚀")
    while True:
        q = input("💬 Toi: ")
        if q.lower() in ["exit", "quit"]:
            break
        res = answer_query(q)
        print(f"🤖 Assistant: {res['answer']}\n")
```

---

## ⚙️ Ce qui change

| Élément               | Ancien comportement                  | Nouveau comportement                               |
| --------------------- | ------------------------------------ | -------------------------------------------------- |
| **LangChain Chain**   | `RetrievalQA` (sans mémoire)         | `ConversationalRetrievalChain`                     |
| **Mémoire**           | Aucune                               | `ConversationBufferMemory` garde tout l’historique |
| **Prompt**            | Statique                             | Gère les conversations continues                   |
| **Suivi du contexte** | Non                                  | Oui                                                |
| **Langues**           | Français/Anglais déjà pris en charge | inchangé                                           |

---

## 💬 Exemple de dialogue

```
Toi: Quels jobs ont échoué aujourd’hui ?
🤖 Assistant: Aujourd’hui, 3 jobs ont échoué : FLOW1, FLOW3, FLOW8...

Toi: Et ceux de la semaine dernière ?
🤖 Assistant: La semaine dernière, les mêmes jobs FLOW3 et FLOW8 ont aussi échoué, ce qui indique un problème récurrent.

Toi: Et comment corriger FLOW3 ?
🤖 Assistant: Selon le champ "WHAT TO DO", il faut redémarrer le conteneur associé et vérifier la connexion à Swift.
```

✅ Aucun paramètre date obligatoire
✅ L’assistant comprend les suivis “celui d’hier”, “et le précédent”, etc.
✅ La mémoire n’est pas réinitialisée entre les appels tant que ton app FastAPI tourne.

---

Souhaites-tu que je t’ajoute aussi :

* 🧾 un **endpoint `/reset_memory`** dans `main.py` pour nettoyer la mémoire quand l’utilisateur veut “nouvelle conversation” ?
* 💾 une **mémoire persistante sur disque (Chroma ou Redis)** pour qu’il garde l’historique même après redémarrage ?
