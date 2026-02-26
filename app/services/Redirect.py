from fastapi.responses import RedirectResponse

@router.get("/authorize")
def authorize():
    oidc = OidcService()
    url_info = oidc.build_authorize_url()

    return RedirectResponse(
        url=url_info["authorize_url"],
        status_code=302
    )
