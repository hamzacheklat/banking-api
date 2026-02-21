Parfait 👌
Voici **la version complète FRONT + BACK**, propre entreprise, avec :

* ✅ BFF (Backend For Frontend)
* ✅ Front et Back sur domaines différents
* ✅ Access token + Refresh token
* ✅ Refresh automatique côté backend
* ✅ Vérification groupe LDAP `database`
* ✅ Redirection `/forbidden`
* ✅ Cookie httpOnly sécurisé
* ✅ Angular sans token

---

# 🏗 Hypothèse d’URLs

```
FRONT : https://oracle-ai-stg.echonet.bnpparibas.com
BACK  : https://oracle-ai-api-stg.echonet.bnpparibas.com
SSO   : https://ssoforms.sso-stg.bnpparibas.com
```

Adapte si besoin.

---

# ===============================

# 🟢 BACKEND FASTAPI COMPLET

# ===============================

## 📦 Installation

```bash
pip install fastapi uvicorn httpx python-jose[cryptography]
```

---

## 📁 config.py

```python
OIDC_ISSUER = "https://ssoforms.sso-stg.bnpparibas.com/affwebservices/CASSO/oidc/DATABASE_oracle-performance-ai-stg"

CLIENT_ID = "CLIENT_ID_MARKETPLACE"
CLIENT_SECRET = "CLIENT_SECRET_MARKETPLACE"

FRONT_URL = "https://oracle-ai-stg.echonet.bnpparibas.com"
BACK_URL = "https://oracle-ai-api-stg.echonet.bnpparibas.com"

REDIRECT_URI = f"{BACK_URL}/api/callback"

ACCESS_COOKIE = "oracle_ai_access"
REFRESH_COOKIE = "oracle_ai_refresh"

REQUIRED_GROUP = "database"
```

---

## 📁 main.py (VERSION COMPLETE PRODUCTION)

```python
import secrets
import httpx
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt, ExpiredSignatureError
from config import *

app = FastAPI()

# ===============================
# CORS
# ===============================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONT_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

jwks_cache = None

async def get_jwks():
    global jwks_cache
    if jwks_cache:
        return jwks_cache
    async with httpx.AsyncClient() as client:
        jwks_cache = (await client.get(f"{OIDC_ISSUER}/jwks")).json()
    return jwks_cache

# ===============================
# LOGIN
# ===============================

@app.get("/api/login")
async def login():
    state = secrets.token_urlsafe(32)

    auth_url = (
        f"{OIDC_ISSUER}/authorize"
        f"?client_id={CLIENT_ID}"
        f"&response_type=code"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope=openid profile email offline_access"
        f"&state={state}"
    )

    return RedirectResponse(auth_url)

# ===============================
# CALLBACK
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

    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")

    if not access_token:
        return RedirectResponse(f"{FRONT_URL}/forbidden")

    # 🔐 Validation immédiate + groupe
    jwks = await get_jwks()
    header = jwt.get_unverified_header(access_token)
    kid = header["kid"]
    key = next(k for k in jwks["keys"] if k["kid"] == kid)

    payload = jwt.decode(
        access_token,
        key,
        algorithms=["RS256"],
        audience=CLIENT_ID,
        issuer=OIDC_ISSUER,
    )

    groups = payload.get("groups", []) or payload.get("memberOf", [])

    if REQUIRED_GROUP not in groups:
        return RedirectResponse(f"{FRONT_URL}/forbidden")

    response = RedirectResponse(f"{FRONT_URL}/chat")

    response.set_cookie(
        key=ACCESS_COOKIE,
        value=access_token,
        httponly=True,
        secure=True,
        samesite="none",
    )

    if refresh_token:
        response.set_cookie(
            key=REFRESH_COOKIE,
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite="none",
        )

    return response

# ===============================
# REFRESH
# ===============================

async def refresh_access_token(refresh_token: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{OIDC_ISSUER}/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    return response.json()

# ===============================
# AUTH DEPENDENCY
# ===============================

async def get_current_user(request: Request, response: JSONResponse):

    access_token = request.cookies.get(ACCESS_COOKIE)
    refresh_token = request.cookies.get(REFRESH_COOKIE)

    if not access_token:
        raise HTTPException(status_code=401)

    jwks = await get_jwks()

    try:
        header = jwt.get_unverified_header(access_token)
        kid = header["kid"]
        key = next(k for k in jwks["keys"] if k["kid"] == kid)

        payload = jwt.decode(
            access_token,
            key,
            algorithms=["RS256"],
            audience=CLIENT_ID,
            issuer=OIDC_ISSUER,
        )

    except ExpiredSignatureError:

        if not refresh_token:
            raise HTTPException(status_code=401)

        token_data = await refresh_access_token(refresh_token)
        new_access = token_data.get("access_token")

        if not new_access:
            raise HTTPException(status_code=401)

        response.set_cookie(
            key=ACCESS_COOKIE,
            value=new_access,
            httponly=True,
            secure=True,
            samesite="none",
        )

        header = jwt.get_unverified_header(new_access)
        kid = header["kid"]
        key = next(k for k in jwks["keys"] if k["kid"] == kid)

        payload = jwt.decode(
            new_access,
            key,
            algorithms=["RS256"],
            audience=CLIENT_ID,
            issuer=OIDC_ISSUER,
        )

    groups = payload.get("groups", []) or payload.get("memberOf", [])

    if REQUIRED_GROUP not in groups:
        raise HTTPException(status_code=403)

    return payload

# ===============================
# ROUTES
# ===============================

@app.get("/api/me")
async def me(user=Depends(get_current_user)):
    return user

@app.get("/api/chat")
async def chat(user=Depends(get_current_user)):
    return {"message": "chat ok"}

@app.get("/api/analytics")
async def analytics(user=Depends(get_current_user)):
    return {"message": "analytics ok"}

# ===============================
# LOGOUT
# ===============================

@app.get("/api/logout")
def logout():
    response = RedirectResponse(FRONT_URL)
    response.delete_cookie(ACCESS_COOKIE, samesite="none", secure=True)
    response.delete_cookie(REFRESH_COOKIE, samesite="none", secure=True)
    return response
```

---

# ===============================

# 🟣 ANGULAR COMPLET

# ===============================

---

## 📁 api.service.ts

```ts
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';

@Injectable({ providedIn: 'root' })
export class ApiService {

  private API =
    'https://oracle-ai-api-stg.echonet.bnpparibas.com/api';

  constructor(private http: HttpClient) {}

  me() {
    return this.http.get(`${this.API}/me`, { withCredentials: true });
  }

  chat() {
    return this.http.get(`${this.API}/chat`, { withCredentials: true });
  }

  analytics() {
    return this.http.get(`${this.API}/analytics`, { withCredentials: true });
  }
}
```

---

## 📁 auth.interceptor.ts

```ts
import { Injectable } from '@angular/core';
import {
  HttpInterceptor,
  HttpRequest,
  HttpHandler,
  HttpErrorResponse
} from '@angular/common/http';
import { catchError } from 'rxjs/operators';
import { throwError } from 'rxjs';

@Injectable()
export class AuthInterceptor implements HttpInterceptor {

  intercept(req: HttpRequest<any>, next: HttpHandler) {

    const cloned = req.clone({ withCredentials: true });

    return next.handle(cloned).pipe(
      catchError((error: HttpErrorResponse) => {

        if (error.status === 401) {
          window.location.href =
            'https://oracle-ai-api-stg.echonet.bnpparibas.com/api/login';
        }

        if (error.status === 403) {
          window.location.href = '/forbidden';
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

## 📁 forbidden.component.ts

```ts
import { Component } from '@angular/core';

@Component({
  selector: 'app-forbidden',
  template: `
    <div class="forbidden">
      <h1>Accès refusé</h1>
      <p>Veuillez demander les droits d'accès à ce site.</p>
    </div>
  `,
  styles: [`
    .forbidden {
      text-align: center;
      margin-top: 120px;
    }
    h1 {
      color: red;
      font-size: 32px;
    }
  `]
})
export class ForbiddenComponent {}
```

---

# 🎯 Résultat Final

| Cas                 | Résultat     |
| ------------------- | ------------ |
| Non connecté        | Login        |
| Access expiré       | Refresh auto |
| Refresh expiré      | Login        |
| Pas groupe database | Forbidden    |
| Groupe OK           | Accès        |

---

Tu es maintenant sur :

> 🏦 Architecture bancaire
> 🔐 Zéro token côté front
> 🔄 Refresh automatique
> 🛡 Contrôle LDAP
> 🧱 Enterprise ready

---

Si tu veux maintenant :

* 🛡 CSRF protection ultra propre
* 🔄 Rotation refresh token sécurisée
* 🧠 Mapping multi-groupes → rôles internes
* 📊 Audit logs sécurité

On peut encore monter en niveau 👌
