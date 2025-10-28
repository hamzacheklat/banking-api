def build_messages(query, contexts):
    """
    Construit un prompt structuré qui incite le modèle à répondre uniquement
    à partir du contexte technique (Delphix + APIs).
    Répond dans la langue de la question (français ou anglais).
    """

    # Détection simple de la langue (FR si majorité de mots français)
    import re
    french_keywords = ["bonjour", "comment", "quoi", "pourquoi", "fonctionne", "exemple", "implémenter", "réponse"]
    is_french = any(word.lower() in query.lower() for word in french_keywords)
    lang = "fr" if is_french else "en"

    system_prompt_fr = (
        "Tu es un assistant d’ingénierie spécialisé dans les APIs database_apis et Delphix.\n"
        "Réponds toujours de manière claire et technique, sans inventer d’informations.\n"
        "Si l’information n’est pas présente, indique simplement qu’elle n’est pas disponible.\n\n"
        "- Si la question concerne uniquement le fonctionnement de Delphix, "
        "réponds uniquement sur le fonctionnement de Delphix (sans mentionner Python).\n"
        "- Si la question concerne l’implémentation d’une fonctionnalité Delphix dans le code database_apis, "
        "fournis une réponse avec du code pertinent ou du pseudo-code."
    )

    system_prompt_en = (
        "You are an engineering assistant specialized in database_apis and Delphix APIs.\n"
        "Always respond clearly and technically, without making up information.\n"
        "If the information is not available, just say it is not available.\n\n"
        "- If the question is only about how Delphix works, answer only about Delphix (no Python mention).\n"
        "- If the question is about implementing a Delphix feature in the database_apis code, "
        "provide an appropriate code example or pseudo-code."
    )

    system = {
        "role": "system",
        "content": system_prompt_fr if lang == "fr" else system_prompt_en
    }

    context_text = "\n\n".join(
        [f"[SOURCE: {c['metadata'].get('source', 'unknown')}] "
         f"{c['metadata'].get('path', 'N/A')}:{c['metadata'].get('endpoint', 'N/A')}\n{c['content']}"
         for c in contexts]
    )

    if lang == "fr":
        user_prompt = (
            f"CONTEXTE TECHNIQUE :\n{context_text}\n\n"
            f"QUESTION : {query}\n\n"
            "Fournis une réponse précise :\n"
            "- Basée sur le code database_apis si la question concerne les APIs database.\n"
            "- Basée sur la documentation Delphix si la question concerne uniquement Delphix.\n"
            "Inclue un exemple de code si possible pour illustrer la réponse."
        )
    else:
        user_prompt = (
            f"TECHNICAL CONTEXT:\n{context_text}\n\n"
            f"QUESTION: {query}\n\n"
            "Provide a clear and accurate answer:\n"
            "- Based on database_apis code if the question is about database APIs.\n"
            "- Based on Delphix documentation if the question is only about Delphix.\n"
            "Include a code example or pseudo-code when relevant."
        )

    user = {"role": "user", "content": user_prompt}

    return [system, user]
