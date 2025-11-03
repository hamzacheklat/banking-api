@app.get("/items")
@openapi.definition(
    summary="Liste des items",
    description="Retourne la liste complète des items disponibles.",
    response={200: [Item]}
)
@validate_response(Item)
async def get_items(request):
    return [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]
