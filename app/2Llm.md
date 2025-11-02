from datetime import datetime
from langchain_community.chat_models import ChatLiteLLM
from langchain.memory import ConversationBufferMemory
from langchain.prompts import ChatPromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
from vector_store import get_vanish_vectorstore
import config

# 1️⃣ Initialisation du vector store et du retriever
vectorstore = get_vanish_vectorstore()
retriever = vectorstore.as_retriever(search_kwargs={"k": 8})

# 2️⃣ Initialisation du modèle
llm = ChatLiteLLM(model=config.LITELL_MODEL, api_key=config.API_KEY)

# 3️⃣ Template contextuel et bilingue
prompt = ChatPromptTemplate.from_template("""
You are a specialized assistant that analyzes failed job flows.
Today's date is {today}.

If the user speaks French, respond in French.
If the user speaks English, respond in English.

Use the context provided to answer precisely and clearly.
""")

# 4️⃣ Création de la chaîne complète
document_chain = create_stuff_documents_chain(llm, prompt)
rag_chain = create_retrieval_chain(retriever, document_chain)

# 5️⃣ Mémoire conversationnelle (optionnelle)
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

def answer_query(query: str):
    today = datetime.now().strftime("%Y-%m-%d")
    response = rag_chain.invoke({"input": query, "today": today})
    return response["answer"]
