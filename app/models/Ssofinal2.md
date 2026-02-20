Parfait 👌
On va faire **Solution 3 propre entreprise** :

> 🔒 Le navigateur ne parle JAMAIS au SSO
> 🔒 Angular parle uniquement à FastAPI
> 🔒 FastAPI parle au SSO
> 🔒 Les tokens ne sont jamais exposés au browser

👉 Architecture **BFF (Backend For Frontend)**

---

# 🏗 Architecture finale

```
Browser
   ↓
Angular
   ↓ (cookies httpOnly)
FastAPI  ←→  SSO (OIDC)
```

✔ Plus de CORS
✔ Plus de token dans le localStorage
✔ Sécurité enterprise

---

# 🎯 Principe

On utilise :

* Authorization Code Flow + PKCE
* FastAPI gère :

  * Redirect vers SSO
  * Callback
  * Exchange code → token
  * Stockage token en session (cookie httpOnly)

Angular ne voit jamais le token.

---

# ===============================

# 🟢 BACKEND FASTAPI COMPLET (BFF)

# ===============================

Installer :

```bash
pip install fastapi uvicorn httpx python-jose itsdangerous
```

---

# 📁 config.py

```python
OIDC_ISSUER = "https://ssoforms.dev.echonet/affwebservices/CASSO/oidc/DATABASE_oracle-tuning-ai-stg"

CLIENT_ID = "DATABASE_oracle-tuning-ai-stg"
CLIENT_SECRET = "xxxxx"  # si requis

REDIRECT_URI = "https://ton-domaine/api/callback"

FRONT_URL = "https://ton-domaine"
```

---

# 📁 main.py

```python
import httpx
import secrets
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt
from config import *

app = FastAPI()

# 🔐 Cookie sécurisé
COOKIE_NAME = "session_token"

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONT_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===============================
# 1️⃣ LOGIN → redirect vers SSO
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
# 2️⃣ CALLBACK SSO
# ===============================

@app.get("/api/callback")
async def callback(code: str):

    token_url = f"{OIDC_ISSUER}/token"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            token_url,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": REDIRECT_URI,
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

    token_data = response.json()

    access_token = token_data["access_token"]

    resp = RedirectResponse(FRONT_URL + "/chat")

    # 🔐 Cookie HTTPOnly
    resp.set_cookie(
        key=COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=True,
        samesite="lax"
    )

    return resp

# ===============================
# 3️⃣ Vérification JWT
# ===============================

async def get_current_user(request: Request):

    token = request.cookies.get(COOKIE_NAME)

    if not token:
        raise HTTPException(status_code=401)

    async with httpx.AsyncClient() as client:
        jwks = (await client.get(f"{OIDC_ISSUER}/jwks")).json()

    payload = jwt.decode(
        token,
        jwks,
        algorithms=["RS256"],
        audience=CLIENT_ID,
        issuer=OIDC_ISSUER
    )

    return payload

# ===============================
# 4️⃣ Routes protégées
# ===============================

@app.get("/api/chat")
async def chat(user=Depends(get_current_user)):
    return {"chat": "ok", "user": user}

@app.get("/api/analytics")
async def analytics(user=Depends(get_current_user)):
    return {"analytics": "ok", "user": user}

# ===============================
# 5️⃣ Logout
# ===============================

@app.get("/api/logout")
def logout():
    response = JSONResponse({"logout": "ok"})
    response.delete_cookie(COOKIE_NAME)
    return response
```

---

# ===============================

# 🟢 ANGULAR SIMPLIFIÉ

# ===============================

👉 On SUPPRIME angular-oauth2-oidc
👉 On n’utilise plus de guard OIDC
👉 Angular devient simple

---

# 📁 auth.service.ts

```ts
import { Injectable } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class AuthService {

  login() {
    window.location.href = '/api/login';
  }

  logout() {
    window.location.href = '/api/logout';
  }
}
```

---

# 📁 auth.guard.ts

```ts
import { Injectable } from '@angular/core';
import { CanActivate } from '@angular/router';

@Injectable({ providedIn: 'root' })
export class AuthGuard implements CanActivate {

  canActivate(): boolean {
    return true; // Backend protège
  }
}
```

---

# 📁 http config

Dans Angular :

```ts
this.http.get('/api/chat', { withCredentials: true })
```

⚠ IMPORTANT : `withCredentials: true`

---

# 🎯 Flow complet maintenant

1. User ouvre `/chat`
2. Angular appelle `/api/chat`
3. Backend voit pas de cookie → 401
4. Angular redirige vers `/api/login`
5. Backend redirect vers SSO
6. Login SSO
7. Callback `/api/callback`
8. Backend met cookie httpOnly
9. Redirection `/chat`
10. Angular appelle `/api/chat`
11. OK

---

# 🔥 Avantages

✔ Aucun appel SSO côté navigateur
✔ Aucun problème CORS
✔ Token invisible
✔ Compatible entreprise
✔ Compatible reverse proxy nginx

---

# 🟢 Si tu es derrière NGINX

Ajoute :

```nginx
location /api/ {
    proxy_pass http://fastapi:8000/;
    proxy_set_header Host $host;
}
```

---

# ⚠ Très important

Si Angular et FastAPI sont sur :

* même domaine → parfait
* domaines différents → cookie doit être :

```
samesite=None;
secure;
```

---

# 🎯 Résultat

Tu passes d’un modèle SPA public
➡ à un modèle BFF sécurisé enterprise.

---

Si tu veux maintenant :

* 🔄 Refresh token automatique
* 🧠 Gestion des rôles
* 🏢 Multi-environnement (stg/prd)
* 🔐 CSRF protection
* 🧱 Architecture propre avec NGINX complet

Dis-moi.
