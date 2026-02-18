Parfait 👌
Si tu as activé **PKCE**, on va faire une config **propre SPA + API sécurisée**, adaptée à ton produit SSO OpenID.

Je vais te donner :

1. ✅ Ce que tu dois copier depuis le produit
2. 🔵 Tous les fichiers FRONTEND (Angular + PKCE)
3. 🔴 Tous les fichiers BACKEND (FastAPI + JWT validation)
4. 🧠 Les points sécurité importants

---

# ✅ 1️⃣ CE QUE TU DOIS COPIER DEPUIS TON PRODUIT

Depuis tes captures, tu dois récupérer :

---

## 🔹 1. Issuer

Dans :

```
Provider Meta (.well-known/openid-configuration)
```

Exemple (à adapter avec TON URL exacte) :

```
https://ssoforms.dev.echonet/affwebservices/CASSO/oidc/DATABASE_oracle-tuning-ai-stg
```

⚠️ Tu ne mets PAS `.well-known` à la fin.

---

## 🔹 2. Client ID

Dans :

```
Artifact Information → Client ID
```

Exemple :

```
0001bf83-2a04-198e-b00d-4eb30af30000
```

---

## 🔹 3. Redirect URL

Dans :

```
Redirect Uri
```

Exemple :

```
https://oracle-tuning-advisor-emea-stg.cib.echonet/redirect
```

⚠️ Cette URL DOIT exister dans Angular.

---

## 🔹 4. JWKS URI

Dans :

```
Jwk Set endpoint
```

Exemple :

```
https://.../jwks
```

---

## 🔹 5. Scope

Actuellement tu as :

```
openid
```

Je recommande :

```
openid profile
```

Et demander si possible :

```
openid profile groups
```

---

# 🔵 =========================

# FRONTEND ANGULAR 16 + PKCE

# =========================

---

## 📁 Structure

```
frontend/
│
└── src/
    ├── app/
    │   ├── core/
    │   │   └── auth/
    │   │       ├── auth.config.ts
    │   │       ├── auth.service.ts
    │   │       ├── auth.interceptor.ts
    │   │       ├── auth.guard.ts
    │   │       └── role.guard.ts
    │   │
    │   ├── app.module.ts
    │   └── app.component.ts
    │
    └── environments/
        ├── environment.ts
        └── environment.prod.ts
```

---

# 📄 environment.ts

📍 `frontend/src/environments/environment.ts`

⚠️ Remplace les valeurs par celles de TON produit

```ts
export const environment = {
  production: false,
  apiUrl: 'http://localhost:8000',

  oidc: {
    issuer: 'https://ssoforms.dev.echonet/affwebservices/CASSO/oidc/DATABASE_oracle-tuning-ai-stg',
    clientId: '0001bf83-XXXX-XXXX-XXXX',
    scope: 'openid profile'
  }
};
```

---

# 📄 auth.config.ts

📍 `frontend/src/app/core/auth/auth.config.ts`

PKCE activé automatiquement avec `responseType: 'code'`

```ts
import { AuthConfig } from 'angular-oauth2-oidc';
import { environment } from '../../../environments/environment';

export const authConfig: AuthConfig = {
  issuer: environment.oidc.issuer,

  redirectUri: window.location.origin + '/redirect',

  clientId: environment.oidc.clientId,

  responseType: 'code',   // Authorization Code Flow
  scope: environment.oidc.scope,

  usePkce: true,          // IMPORTANT

  showDebugInformation: true,
  strictDiscoveryDocumentValidation: false
};
```

---

# 📄 auth.service.ts

📍 `frontend/src/app/core/auth/auth.service.ts`

```ts
import { Injectable } from '@angular/core';
import { OAuthService } from 'angular-oauth2-oidc';
import { authConfig } from './auth.config';

@Injectable({ providedIn: 'root' })
export class AuthService {

  constructor(private oauthService: OAuthService) {
    this.init();
  }

  async init() {
    this.oauthService.configure(authConfig);
    await this.oauthService.loadDiscoveryDocumentAndTryLogin();
  }

  login() {
    this.oauthService.initCodeFlow();
  }

  logout() {
    this.oauthService.logOut();
  }

  get accessToken(): string {
    return this.oauthService.getAccessToken();
  }

  get identityClaims(): any {
    return this.oauthService.getIdentityClaims();
  }

  get userGroups(): string[] {
    const claims: any = this.identityClaims;
    return claims?.groups || claims?.memberOf || [];
  }

  hasGroup(group: string): boolean {
    return this.userGroups.includes(group);
  }
}
```

---

# 📄 auth.interceptor.ts

📍 `frontend/src/app/core/auth/auth.interceptor.ts`

```ts
import { Injectable } from '@angular/core';
import { HttpEvent, HttpHandler, HttpInterceptor, HttpRequest } from '@angular/common/http';
import { Observable } from 'rxjs';
import { AuthService } from './auth.service';

@Injectable()
export class AuthInterceptor implements HttpInterceptor {

  constructor(private auth: AuthService) {}

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {

    const token = this.auth.accessToken;

    if (token) {
      const cloned = req.clone({
        setHeaders: {
          Authorization: `Bearer ${token}`
        }
      });
      return next.handle(cloned);
    }

    return next.handle(req);
  }
}
```

---

# 📄 auth.guard.ts

📍 `frontend/src/app/core/auth/auth.guard.ts`

```ts
import { Injectable } from '@angular/core';
import { CanActivate } from '@angular/router';
import { AuthService } from './auth.service';

@Injectable({ providedIn: 'root' })
export class AuthGuard implements CanActivate {

  constructor(private auth: AuthService) {}

  canActivate(): boolean {

    if (!this.auth.accessToken) {
      this.auth.login();
      return false;
    }

    return true;
  }
}
```

---

# 📄 app.module.ts

📍 `frontend/src/app/app.module.ts`

```ts
import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { HttpClientModule, HTTP_INTERCEPTORS } from '@angular/common/http';
import { OAuthModule } from 'angular-oauth2-oidc';

import { AppComponent } from './app.component';
import { AuthInterceptor } from './core/auth/auth.interceptor';

@NgModule({
  declarations: [AppComponent],
  imports: [
    BrowserModule,
    HttpClientModule,
    OAuthModule.forRoot()
  ],
  providers: [
    {
      provide: HTTP_INTERCEPTORS,
      useClass: AuthInterceptor,
      multi: true
    }
  ],
  bootstrap: [AppComponent]
})
export class AppModule {}
```

---

# 🔴 =========================

# BACKEND FASTAPI

# =========================

---

## 📁 Structure

```
backend/
│
└── app/
    ├── main.py
    ├── core/
    │   ├── config.py
    │   └── security.py
    ├── dependencies/
    │   └── auth.py
    └── api/
        ├── router.py
        └── routes/
            ├── user.py
            └── admin.py
```

---

# 📄 config.py

📍 `backend/app/core/config.py`

```python
OIDC_ISSUER = "https://ssoforms.dev.echonet/affwebservices/CASSO/oidc/DATABASE_oracle-tuning-ai-stg"

AUDIENCE = "0001bf83-XXXX-XXXX-XXXX"

JWKS_URL = f"{OIDC_ISSUER}/jwks"
```

---

# 📄 security.py

📍 `backend/app/core/security.py`

```python
from jose import jwt
import requests
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer
from starlette.status import HTTP_401_UNAUTHORIZED
from app.core.config import JWKS_URL, AUDIENCE, OIDC_ISSUER

security = HTTPBearer()

jwks = requests.get(JWKS_URL).json()

def verify_token(credentials=Depends(security)):

    token = credentials.credentials

    try:
        header = jwt.get_unverified_header(token)

        key = next(
            k for k in jwks["keys"]
            if k["kid"] == header["kid"]
        )

        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=AUDIENCE,
            issuer=OIDC_ISSUER,
        )

        return payload

    except Exception:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
```

---

# 📄 auth.py (LDAP groups)

📍 `backend/app/dependencies/auth.py`

```python
from fastapi import Depends, HTTPException
from app.core.security import verify_token

def require_group(group_name: str):

    def checker(payload=Depends(verify_token)):

        groups = payload.get("groups", [])

        if group_name not in groups:
            raise HTTPException(
                status_code=403,
                detail="Not enough permissions"
            )

        return payload

    return checker
```

---

# 📄 main.py

📍 `backend/app/main.py`

```python
from fastapi import FastAPI, Depends
from app.core.security import verify_token
from app.dependencies.auth import require_group

app = FastAPI()

@app.get("/public")
def public():
    return {"message": "Public"}

@app.get("/user")
def user(payload=Depends(verify_token)):
    return {"user": payload}

@app.get("/admin")
def admin(payload=Depends(require_group("APP_ORACLE_TUNING_ADMIN"))):
    return {"message": "Admin access"}
```

---

# 🔐 Important

✔ PKCE → seulement frontend
✔ Backend valide signature JWT
✔ Audience = client_id
✔ Issuer = exact issuer
✔ Groupes doivent être dans le token

---

Si tu veux maintenant, on peut :

* 🔎 Vérifier ton token réel
* 🔥 Ajouter refresh token automatique
* 🛡️ Mettre en place un vrai RBAC enterprise
* 🏦 Adapter 100% compatible infra bancaire

On continue 👌
