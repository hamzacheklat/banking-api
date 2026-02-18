Parfait 👌 tu es exactement dans un cas classique :

* Frontend : **Angular 16**
* Backend : **FastAPI**
* IdP : **SSO OpenID Connect (SiteMinder / CASSO)**
* Autorisation : basée sur **groupes LDAP / entitlements**
* Flow : **Authorization Code Flow**

On va faire une architecture propre et enterprise-ready 🔐

---

# 🎯 Architecture cible

### 👉 Flow recommandé (Secure)

```
Angular  →  SSO (OIDC)
           ←  id_token + access_token
Angular  →  FastAPI (Authorization: Bearer access_token)
FastAPI  →  Verify JWT via JWKS
FastAPI  →  Check LDAP groups (claims)
```

⚠️ IMPORTANT :

* Le frontend ne parle JAMAIS au backend sans token
* Le backend ne fait JAMAIS confiance au frontend
* L'autorisation se fait côté backend uniquement

---

# 🧠 Étape 1 — Configuration SSO

Dans ton produit OpenID Client tu as :

* authorization_endpoint
* token_endpoint
* jwks_uri
* introspection_endpoint
* client_id
* client_secret

Tu dois utiliser :

* **Authorization Code Flow**
* Scope : `openid profile`
* Ajouter un scope custom si LDAP groups sont mappés (ex: `groups`)

Demande à l’équipe SSO :
👉 Les groupes LDAP sont-ils injectés dans le token ?

* Dans `groups`
* Dans `memberOf`
* Dans `roles`
* Dans `entitlements`

---

# 🔥 FRONTEND Angular 16

On va utiliser :

```
npm install angular-oauth2-oidc
```

---

## 📁 auth.config.ts

```ts
import { AuthConfig } from 'angular-oauth2-oidc';

export const authConfig: AuthConfig = {
  issuer: 'https://ssoforms.dev.echonet/...',

  redirectUri: window.location.origin,
  clientId: 'TON_CLIENT_ID',

  responseType: 'code',
  scope: 'openid profile',

  showDebugInformation: true,
  strictDiscoveryDocumentValidation: false,
};
```

---

## 📁 auth.service.ts

```ts
import { Injectable } from '@angular/core';
import { OAuthService } from 'angular-oauth2-oidc';
import { authConfig } from './auth.config';

@Injectable({ providedIn: 'root' })
export class AuthService {

  constructor(private oauthService: OAuthService) {
    this.configure();
  }

  async configure() {
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

## 📁 HTTP Interceptor

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

# 🚀 BACKEND FastAPI

On va :

* Vérifier signature JWT via JWKS
* Vérifier audience
* Vérifier issuer
* Vérifier groupe LDAP

---

## 📦 Install

```
pip install python-jose requests
```

---

## 📁 security.py

```python
from jose import jwt
import requests
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer
from starlette.status import HTTP_401_UNAUTHORIZED

OIDC_ISSUER = "https://ssoforms.dev.echonet/..."
JWKS_URL = f"{OIDC_ISSUER}/jwks"
AUDIENCE = "TON_CLIENT_ID"

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

    except Exception as e:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
```

---

# 🎯 Autorisation par Groupe LDAP

Supposons que dans le token tu as :

```json
{
  "sub": "u123456",
  "groups": [
    "APP_ORACLE_TUNING_USER",
    "APP_ORACLE_TUNING_ADMIN"
  ]
}
```

---

## 📁 dependency group

```python
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

## 📁 main.py

```python
from fastapi import FastAPI, Depends
from security import verify_token, require_group

app = FastAPI()

@app.get("/public")
def public():
    return {"message": "Public endpoint"}


@app.get("/user")
def user(payload=Depends(verify_token)):
    return {"user": payload}


@app.get("/admin")
def admin(payload=Depends(require_group("APP_ORACLE_TUNING_ADMIN"))):
    return {"message": "Admin access granted"}
```

---

# 🔐 Entitlement Model (Enterprise propre)

Tu dois créer dans LDAP :

* APP_ORACLE_TUNING_USER
* APP_ORACLE_TUNING_ADMIN

Le process normal :

1. User demande accès
2. Manager valide
3. Groupe LDAP ajouté
4. Token contient le groupe
5. Backend autorise

---

# 🛡️ Important Sécurité

NE JAMAIS :

* Vérifier groupes uniquement côté Angular ❌
* Faire confiance au user claims sans signature ❌
* Stocker le client_secret dans Angular ❌

---

# 🏗️ Option Enterprise++

Si ton SSO ne met pas les groupes dans le JWT :

➡️ Utilise endpoint `/introspect`
➡️ Ou appelle un API LDAP interne
➡️ Ou demande mapping SSO → groups dans token

---

# 🧩 Résumé Architecture

| Composant | Rôle                       |
| --------- | -------------------------- |
| Angular   | Login + envoi Bearer token |
| SSO       | Authentification           |
| FastAPI   | Validation token           |
| LDAP      | Autorisation par groupe    |

---

Si tu veux je peux te faire :

* 🔥 Version complète prête à dockeriser
* 🔥 Version avec refresh token
* 🔥 Version avec RBAC propre (role → permission mapping)
* 🔥 Diagramme clair pour ton équipe sécurité

Dis-moi 👍
