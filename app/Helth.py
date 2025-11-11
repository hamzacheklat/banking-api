from sanic import Blueprint, Sanic, response

# Blueprint nommé et préfixe /health (tu peux changer le nom / préfixe)
bp_health = Blueprint(name="health", url_prefix="/health")

@bp_health.get("/")
async def health(request):
    """
    Health check endpoint minimal.
    Retourne un JSON simple indiquant l'état du service.
    """
    return response.json({
        "status": "ok",
        "healthy": True,
        "service": "ckms",    # adapte si nécessaire
        "message": "Health check successful"
    })

# --- Exemple d'enregistrement sur l'app Sanic (si tu veux) ---
# app = Sanic("my_app")
# app.blueprint(bp_health)
# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=8000)
