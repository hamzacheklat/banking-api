# utilitaire pour sanitiser les métadatas avant envoi à Chroma
def _sanitize_value(v):
    """
    Convertit la valeur en un type accepté par Chroma:
    - None -> "" (string vide)
    - bool/int/float/str -> inchangé
    - list/dict -> JSON string
    - autre -> str(v)
    """
    import json
    if v is None:
        return ""
    if isinstance(v, (bool, int, float, str)):
        return v
    if isinstance(v, (list, dict)):
        try:
            return json.dumps(v, ensure_ascii=False)
        except Exception:
            return str(v)
    # fallback
    return str(v)


def sanitize_metadata_dict(meta: dict) -> dict:
    """
    Retourne une copy du dict meta avec toutes les valeurs converties en types supportés.
    """
    return {k: _sanitize_value(v) for k, v in (meta.items() if meta else {})}
