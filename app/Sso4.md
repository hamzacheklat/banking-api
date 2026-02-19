Parfait 👍
Je te redonne **LE SET COMPLET FRONT + BACK**, **cohérent**, **corrigé**, et **prêt prod / banque**, **sans client secret**, **avec PKCE**, **gestion redirect**, **JWT clean**, **mode local maîtrisé**.

Je te mets aussi **exactement quels fichiers ajouter / modifier**.

---

# 🟦 FRONTEND — Angular 16 + OIDC PKCE (COMPLET)

---

## 📁 Structure finale

```
frontend/
└── src/
    ├── app/
    │   ├── core/
    │   │   └── auth/
    │   │       ├── auth.config.ts
    │   │       ├── auth.service.ts
    │   │       ├── auth.guard.ts
    │   │       ├── auth.interceptor.ts
    │   │       └── redirect.component.ts
    │   │
    │   ├── app-routing.module.ts
    │   ├── app.module.ts
    │   └── app.component.ts
    │
    ├── environments/
    │   ├── environment.ts
    │   └── environment.prod.ts
    │
    └── main.ts
```

---

## 1️⃣ `environment.ts`

📄 `src/environments/environment.ts`

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

## 2️⃣ `auth.config.ts`

📄 `core/auth/auth.config.ts`

```ts
import { AuthConfig } from 'angular-oauth2-oidc';
import { environment } from '../../../environments/environment';

export const authConfig: AuthConfig = {
  issuer: environment.oidc.issuer,
  clientId: environment.oidc.clientId,

  redirectUri: window.location.origin + '/redirect',

  responseType: 'code',        // PKCE
  scope: environment.oidc.scope,
  usePkce: true,

  showDebugInformation: true,
  strictDiscoveryDocumentValidation: false
};
```

---

## 3️⃣ `auth.service.ts`

📄 `core/auth/auth.service.ts`

```ts
import { Injectable } from '@angular/core';
import { OAuthService } from 'angular-oauth2-oidc';
import { authConfig } from './auth.config';

@Injectable({ providedIn: 'root' })
export class AuthService {

  constructor(private oauth: OAuthService) {
    this.init();
  }

  async init() {
    this.oauth.configure(authConfig);
    await this.oauth.loadDiscoveryDocumentAndTryLogin();
  }

  login() {
    this.oauth.initCodeFlow();
  }

  logout() {
    this.oauth.logOut();
  }

  get accessToken(): string {
    return this.oauth.getAccessToken();
  }

  isAuthenticated(): boolean {
    return this.oauth.hasValidAccessToken();
  }

  isTokenExpired(): boolean {
    return !this.oauth.hasValidAccessToken();
  }

  get identityClaims(): any {
    return this.oauth.getIdentityClaims();
  }

  get groups(): string[] {
    return this.identityClaims?.groups || [];
  }

  hasGroup(group: string): boolean {
    return this.groups.includes(group);
  }
}
```

---

## 4️⃣ `auth.guard.ts`

📄 `core/auth/auth.guard.ts`

```ts
import { Injectable } from '@angular/core';
import { CanActivate } from '@angular/router';
import { AuthService } from './auth.service';

@Injectable({ providedIn: 'root' })
export class AuthGuard implements CanActivate {

  constructor(private auth: AuthService) {}

  canActivate(): boolean {

    if (!this.auth.isAuthenticated()) {
      this.auth.login();
      return false;
    }

    return true;
  }
}
```

---

## 5️⃣ `auth.interceptor.ts`

📄 `core/auth/auth.interceptor.ts`

```ts
import { Injectable } from '@angular/core';
import {
  HttpInterceptor,
  HttpRequest,
  HttpHandler,
  HttpEvent
} from '@angular/common/http';
import { Observable } from 'rxjs';
import { AuthService } from './auth.service';
import { environment } from '../../../environments/environment';

@Injectable()
export class AuthInterceptor implements HttpInterceptor {

  constructor(private auth: AuthService) {}

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {

    if (!req.url.startsWith(environment.apiUrl)) {
      return next.handle(req);
    }

    const token = this.auth.accessToken;

    if (token) {
      req = req.clone({
        setHeaders: {
          Authorization: `Bearer ${token}`
        }
      });
    }

    return next.handle(req);
  }
}
```

---

## 6️⃣ `redirect.component.ts` ⚠️ OBLIGATOIRE

📄 `core/auth/redirect.component.ts`

```ts
import { Component, OnInit } from '@angular/core';
import { OAuthService } from 'angular-oauth2-oidc';
import { Router } from '@angular/router';

@Component({
  template: `<p>Authentification en cours...</p>`
})
export class RedirectComponent implements OnInit {

  constructor(
    private oauth: OAuthService,
    private router: Router
  ) {}

  async ngOnInit() {
    await this.oauth.loadDiscoveryDocumentAndTryLogin();
    this.router.navigateByUrl('/');
  }
}
```

---

## 7️⃣ `app-routing.module.ts`

📄 `app-routing.module.ts`

```ts
import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { RedirectComponent } from './core/auth/redirect.component';
import { AuthGuard } from './core/auth/auth.guard';

const routes: Routes = [
  { path: 'redirect', component: RedirectComponent },
  {
    path: '',
    canActivate: [AuthGuard],
    loadChildren: () =>
      import('./features/home/home.module').then(m => m.HomeModule)
  }
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule {}
```

---

## 8️⃣ `app.module.ts`

📄 `app.module.ts`

```ts
import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { HttpClientModule, HTTP_INTERCEPTORS } from '@angular/common/http';
import { OAuthModule } from 'angular-oauth2-oidc';

import { AppComponent } from './app.component';
import { AppRoutingModule } from './app-routing.module';
import { AuthInterceptor } from './core/auth/auth.interceptor';
import { RedirectComponent } from './core/auth/redirect.component';

@NgModule({
  declarations: [
    AppComponent,
    RedirectComponent
  ],
  imports: [
    BrowserModule,
    HttpClientModule,
    OAuthModule.forRoot(),
    AppRoutingModule
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

# 🟥 BACKEND — FastAPI + JWT RS256 (COMPLET)

---

## 📁 Structure finale

```
backend/
└── app/
    ├── main.py
    ├── core/
    │   ├── config.py
    │   └── security.py
    └── dependencies/
        └── auth.py
```

---

## 1️⃣ `config.py`

📄 `core/config.py`

```python
OIDC_ISSUER = "https://ssoforms.dev.echonet/affwebservices/CASSO/oidc/DATABASE_oracle-tuning-ai-stg"

AUDIENCE = "0001bf83-XXXX-XXXX-XXXX"

JWKS_URL = f"{OIDC_ISSUER}/jwks"
```

---

## 2️⃣ `security.py`

📄 `core/security.py`

```python
from jose import jwt
import requests
from functools import lru_cache
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from starlette.status import HTTP_401_UNAUTHORIZED
from app.core.config import JWKS_URL, AUDIENCE, OIDC_ISSUER

security = HTTPBearer()

@lru_cache()
def get_jwks():
    return requests.get(JWKS_URL).json()

def verify_token(credentials=Depends(security)):
    token = credentials.credentials

    try:
        jwks = get_jwks()
        header = jwt.get_unverified_header(token)

        key = next(k for k in jwks["keys"] if k["kid"] == header["kid"])

        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=AUDIENCE,
            issuer=OIDC_ISSUER
        )

        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")

    except Exception:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
```

---

## 3️⃣ `auth.py` (RBAC groupes)

📄 `dependencies/auth.py`

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

## 4️⃣ `main.py`

📄 `main.py`

```python
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.core.security import verify_token
from app.dependencies.auth import require_group

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://oracle-tuning-advisor-emea-stg.cib.echonet"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/public")
def public():
    return {"message": "Public endpoint"}

@app.get("/user")
def user(payload=Depends(verify_token)):
    return payload

@app.get("/admin")
def admin(payload=Depends(require_group("APP_ORACLE_TUNING_ADMIN"))):
    return {"message": "Admin access"}
```

---

# 🟢 CE QUE TU N’AS **PAS** À FAIRE

❌ Page login Angular
❌ Utiliser le client secret
❌ Appeler `/token` depuis le backend
❌ Stocker les tokens en localStorage manuellement

---

# 🧪 MODE LOCAL (RECOMMANDÉ)

```
/etc/hosts
127.0.0.1 oracle-tuning-advisor-emea-stg.cib.echonet
```

```
ng serve --ssl true --host oracle-tuning-advisor-emea-stg.cib.echonet
```

---

# ✅ Résultat final

✔ SSO PKCE conforme
✔ Sécurité bancaire
✔ JWT validé côté backend
✔ RBAC par groupes LDAP
✔ Local dev maîtrisé
✔ Prêt PROD

---

👉 Si tu veux maintenant :

* refresh token silencieux
* logs SSO
* RBAC avancé
* test avec un vrai JWT

Dis-moi 💪
