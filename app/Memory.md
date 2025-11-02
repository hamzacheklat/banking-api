from datetime import datetime
from langchain_community.chat_models import ChatLiteLLM
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from vector_store import get_vanish_vectorstore
import config

# ⚙️ Initialisation du VectorStore (Chroma)
vectorstore = get_vanish_vectorstore()
retriever = vectorstore.as_retriever(search_kwargs={"k": 8})

# 🧠 Initialisation du modèle de chat (via LiteLLM)
llm = ChatLiteLLM(
    model=config.LITELLM_MODEL,
    api_key=config.LITELLM_API_KEY
)

# 🧩 Prompt contextuel bilingue
template = """
You are an assistant specialized in analyzing failed job flows and task anomalies.

Today's date is {today}.
You remember previous interactions with the user to maintain context.

If the user speaks French, reply in French.
If the user speaks English, reply in English.

Use the context from the database to provide a precise and structured answer.

Each record may contain:
FLOW, TASK, JOB_ID, SUB_ID, FAILURE REASON, WHAT TO DO, START_TIME, END_TIME, ORIGIN, TOWER_URL.

Be concise but analytical.

-------------------
Context:
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

# 💬 Mémoire conversationnelle (automatiquement utilisée par la chain)
memory = ConversationBufferMemory(
    memory_key="chat_history",
    return_messages=True
)

# 🔗 Création du RAG conversationnel complet
qa_chain = ConversationalRetrievalChain.from_llm(
    llm=llm,
    retriever=retriever,
    memory=memory,  # 👈 La mémoire est injectée ici
    combine_docs_chain_kwargs={"prompt": prompt}
)


# 🚀 Fonction principale
def answer_query(query: str):
    """
    Pose une question au RAG conversationnel.
    La mémoire garde automatiquement les tours précédents.
    """
    today = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    response = qa_chain.invoke({
        "today": today,
        "question": query
    })

    return {
        "query": query,
        "answer": response["answer"],
        "history": memory.chat_memory.messages,
        "date": today
    }


# 🧹 Réinitialisation de la mémoire (utile entre deux sessions)
def reset_memory():
    memory.clear()
    print("🧽 Mémoire conversationnelle réinitialisée.")


# 🧪 Exemple CLI
if __name__ == "__main__":
    print("🤖 Assistant conversationnel RAG initialisé !")
    while True:
        q = input("\n💬 Toi: ")
        if q.lower() in ["exit", "quit"]:
            break
        if q.lower() in ["reset", "clear"]:
            reset_memory()
            continue
        res = answer_query(q)
        print(f"🤖 Assistant: {res['answer']}")
