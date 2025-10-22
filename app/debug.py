from embedder import embed_texts
from vector_store import get_collection
from rag import chroma_search, build_messages

# 1️⃣ Vérifie combien de documents sont ingérés
collection = get_collection()
print("Nombre de documents dans Chroma :", collection.count())

# 2️⃣ Teste l'embedding d'une requête
query = "Test de récupération de document"
q_emb = embed_texts([query])[0]
print("Embedding de la requête :", q_emb[:5], "...")  # affiche seulement les 5 premiers éléments

# 3️⃣ Recherche dans Chroma
contexts = chroma_search(q_emb, top_k=5)
print("Documents retrouvés :", len(contexts))
for c in contexts:
    print("Titre:", c['metadata'].get('title', 'N/A'))
    print("Extrait:", c['content'][:100], "\n")

# 4️⃣ Construit les messages pour Litellm
messages = build_messages(query, contexts)
print("Messages envoyés à Litellm :")
for m in messages:
    print(m['role'], "->", m['content'][:200], "...\n")
