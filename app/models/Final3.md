Parfait 👌
On va faire **la version complète, propre, cross-domain, entreprise** :

* ✅ Front et Back sur 2 domaines différents
* ✅ Cookie httpOnly
* ✅ SameSite=None
* ✅ CORS correct
* ✅ Validation JWT propre avec JWKS
* ✅ Flow automatique

---

# 🎯 Hypothèse réelle

```
FRONT : https://oracle-ai-stg.echonet.bnpparibas.com
BACK  : https://oracle-ai-api-stg.echonet.bnpparibas.com
SSO   : https://ssoforms.sso-stg.bnpparibas.com
```

👉 Adapte juste les URLs si besoin.

---

# ===============================

# 🟢 BACKEND FASTAPI COMPLET

# ===============================

## 📦 Install

```bash
pip install fastapi uvicorn httpx python-jose[cryptography]
```

---

# 📁 config.py

```python
OIDC_ISSUER = "https://ssoforms.sso-stg.bnpparibas.com/affwebservices/CASSO/oidc/DATABASE_oracle-performance-ai-stg"

CLIENT_ID = "CLIENT_ID_MARKETPLACE"
CLIENT_SECRET = "CLIENT_SECRET_MARKETPLACE"

FRONT_URL = "https://oracle-ai-stg.echonet.bnpparibas.com"
BACK_URL = "https://oracle-ai-api-stg.echonet.bnpparibas.com"

REDIRECT_URI = f"{BACK_URL}/api/callback"

COOKIE_NAME = "oracle_ai_session"
```

---

# 📁 main.py (VERSION PRODUCTION)

```python
import secrets
import httpx
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt
from config import *

app = FastAPI()

# ===============================
# 🔐 CORS
# ===============================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONT_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===============================
# 🔁 JWKS CACHE
# ===============================

jwks_cache = None

async def get_jwks():
    global jwks_cache
    if jwks_cache:
        return jwks_cache

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{OIDC_ISSUER}/jwks")
        jwks_cache = response.json()

    return jwks_cache

# ===============================
# 🔐 LOGIN
# ===============================

@app.get("/api/login")
async def login():

    state = secrets.token_urlsafe(32)

    auth_url = (
        f"{OIDC_ISSUER}/authorize"
        f"?client_id={CLIENT_ID}"
        f"&response_type=code"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope=openid profile email"
        f"&state={state}"
    )

    return RedirectResponse(auth_url)

# ===============================
# 🔁 CALLBACK
# ===============================

@app.get("/api/callback")
async def callback(code: str):

    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            f"{OIDC_ISSUER}/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": REDIRECT_URI,
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    token_data = token_response.json()

    if "access_token" not in token_data:
        raise HTTPException(status_code=400, detail=token_data)

    access_token = token_data["access_token"]

    response = RedirectResponse(url=f"{FRONT_URL}/chat")

    # 🔥 CROSS DOMAIN COOKIE
    response.set_cookie(
        key=COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=True,
        samesite="none",  # obligatoire si front/back différents
    )

    return response

# ===============================
# 🔐 VALIDATION JWT
# ===============================

async def get_current_user(request: Request):

    token = request.cookies.get(COOKIE_NAME)

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    jwks = await get_jwks()

    try:
        header = jwt.get_unverified_header(token)
        kid = header["kid"]

        key = next(k for k in jwks["keys"] if k["kid"] == kid)

        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=CLIENT_ID,
            issuer=OIDC_ISSUER,
        )

        return payload

    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

# ===============================
# 🔒 ROUTES
# ===============================

@app.get("/api/me")
async def me(user=Depends(get_current_user)):
    return user

@app.get("/api/chat")
async def chat(user=Depends(get_current_user)):
    return {"message": "chat ok", "user": user}

@app.get("/api/analytics")
async def analytics(user=Depends(get_current_user)):
    return {"message": "analytics ok", "user": user}

# ===============================
# 🚪 LOGOUT
# ===============================

@app.get("/api/logout")
def logout():
    response = RedirectResponse(url=FRONT_URL)
    response.delete_cookie(
        key=COOKIE_NAME,
        samesite="none",
        secure=True,
    )
    return response
```

---

# ===============================

# 🟣 ANGULAR COMPLET (BFF)

# ===============================

⚠️ Supprimer toute lib OIDC
⚠️ Aucun token côté front

---

# 📁 auth.service.ts

```ts
import { Injectable } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class AuthService {

  login() {
    window.location.href =
      'https://oracle-ai-api-stg.echonet.bnpparibas.com/api/login';
  }

  logout() {
    window.location.href =
      'https://oracle-ai-api-stg.echonet.bnpparibas.com/api/logout';
  }
}
```

---

# 📁 api.service.ts

```ts
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';

@Injectable({ providedIn: 'root' })
export class ApiService {

  private API =
    'https://oracle-ai-api-stg.echonet.bnpparibas.com/api';

  constructor(private http: HttpClient) {}

  getMe() {
    return this.http.get(`${this.API}/me`, {
      withCredentials: true
    });
  }

  getChat() {
    return this.http.get(`${this.API}/chat`, {
      withCredentials: true
    });
  }

  getAnalytics() {
    return this.http.get(`${this.API}/analytics`, {
      withCredentials: true
    });
  }
}
```

---

# 📁 auto-login.interceptor.ts (OPTIONNEL MAIS PROPRE)

```ts
import { Injectable } from '@angular/core';
import {
  HttpEvent,
  HttpHandler,
  HttpInterceptor,
  HttpRequest,
  HttpErrorResponse
} from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

@Injectable()
export class AuthInterceptor implements HttpInterceptor {

  intercept(req: HttpRequest<any>, next: HttpHandler):
    Observable<HttpEvent<any>> {

    const cloned = req.clone({ withCredentials: true });

    return next.handle(cloned).pipe(
      catchError((error: HttpErrorResponse) => {

        if (error.status === 401) {
          window.location.href =
            'https://oracle-ai-api-stg.echonet.bnpparibas.com/api/login';
        }

        return throwError(() => error);
      })
    );
  }
}
```

Dans `app.module.ts` :

```ts
providers: [
  { provide: HTTP_INTERCEPTORS, useClass: AuthInterceptor, multi: true }
]
```

---

# 🎯 FLOW FINAL

1. Angular appelle `/api/chat`
2. 401
3. Interceptor → `/api/login`
4. Backend → SSO
5. Login
6. SSO → `/api/callback`
7. Cookie httpOnly créé (SameSite=None)
8. Redirect vers FRONT `/chat`
9. Angular rappelle `/api/chat`
10. OK

---

# ⚠️ Marketplace

Dans la marketplace :

### Client ID

→ celui EXACT donné

### Redirect URI

```
https://oracle-ai-api-stg.echonet.bnpparibas.com/api/callback
```

---

# 🧠 Si ça ne marche pas

90% des cas :

* ❌ SameSite mal configuré
* ❌ withCredentials oublié
* ❌ allow_origins="*"
* ❌ proxy enlève secure cookie

---

Si tu veux maintenant :

* 🔄 refresh token sécurisé
* 🛡 CSRF protection propre
* 🏢 version nginx reverse proxy entreprise
* 🧠 gestion groupes LDAP

On peut monter niveau architecture encore 👌
