Parfait 👌
Voici **une configuration complète et propre** Angular + FastAPI pour :

* ✅ SSO OIDC (Authorization Code + PKCE)
* ✅ Login automatique
* ✅ Routes `/chat` et `/analytics`
* ✅ Route `/redirect` obligatoire
* ✅ Guard
* ✅ Interceptor global
* ✅ Backend FastAPI validation JWT via JWKS
* ✅ CORS
* ✅ Mode MOCK en DEV

---

# ===============================

# 🟢 FRONTEND – ANGULAR COMPLET

# ===============================

Installe :

```bash
npm install angular-oauth2-oidc
```

---

# 📁 src/app/auth/auth.config.ts

```ts
import { AuthConfig } from 'angular-oauth2-oidc';

export const authConfig: AuthConfig = {
  issuer: 'https://ssoforms.dev.echonet/affwebservices/CASSO/oidc/DATABASE_oracle-tuning-ai-stg',

  redirectUri: window.location.origin + '/redirect',

  clientId: 'DATABASE_oracle-tuning-ai-stg',

  responseType: 'code',

  scope: 'openid profile email',

  usePkce: true,

  requireHttps: false, // ⚠️ mettre true en PROD

  showDebugInformation: true
};
```

---

# 📁 src/app/auth/auth.service.ts

```ts
import { Injectable } from '@angular/core';
import { OAuthService } from 'angular-oauth2-oidc';
import { authConfig } from './auth.config';

@Injectable({ providedIn: 'root' })
export class AuthService {

  constructor(private oauthService: OAuthService) {}

  async initAuth(): Promise<void> {
    this.oauthService.configure(authConfig);

    await this.oauthService.loadDiscoveryDocument();
    await this.oauthService.tryLoginCodeFlow();
  }

  login() {
    this.oauthService.initCodeFlow();
  }

  logout() {
    this.oauthService.logOut();
  }

  get token(): string {
    return this.oauthService.getAccessToken();
  }

  get isLogged(): boolean {
    return this.oauthService.hasValidAccessToken();
  }
}
```

---

# 📁 src/app/auth/auth.guard.ts

```ts
import { Injectable } from '@angular/core';
import { CanActivate } from '@angular/router';
import { OAuthService } from 'angular-oauth2-oidc';

@Injectable({ providedIn: 'root' })
export class AuthGuard implements CanActivate {

  constructor(private oauthService: OAuthService) {}

  canActivate(): boolean {

    if (this.oauthService.hasValidAccessToken()) {
      return true;
    }

    this.oauthService.initCodeFlow();
    return false;
  }
}
```

---

# 📁 src/app/auth/auth.interceptor.ts

```ts
import { Injectable } from '@angular/core';
import {
  HttpEvent,
  HttpHandler,
  HttpInterceptor,
  HttpRequest
} from '@angular/common/http';
import { Observable } from 'rxjs';
import { OAuthService } from 'angular-oauth2-oidc';

@Injectable()
export class AuthInterceptor implements HttpInterceptor {

  constructor(private oauthService: OAuthService) {}

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {

    const token = this.oauthService.getAccessToken();

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

# 📁 src/app/auth/redirect.component.ts

```ts
import { Component, OnInit } from '@angular/core';
import { OAuthService } from 'angular-oauth2-oidc';
import { Router } from '@angular/router';

@Component({
  template: `<p>Authentification en cours...</p>`
})
export class RedirectComponent implements OnInit {

  constructor(
    private oauthService: OAuthService,
    private router: Router
  ) {}

  async ngOnInit() {
    await this.oauthService.tryLoginCodeFlow();
    this.router.navigate(['/chat']);
  }
}
```

---

# 📁 src/app/pages/chat/chat.component.ts

```ts
import { Component } from '@angular/core';

@Component({
  selector: 'app-chat',
  template: `<h2>Chat Page</h2>`
})
export class ChatComponent {}
```

---

# 📁 src/app/pages/analytics/analytics.component.ts

```ts
import { Component } from '@angular/core';

@Component({
  selector: 'app-analytics',
  template: `<h2>Analytics Page</h2>`
})
export class AnalyticsComponent {}
```

---

# 📁 src/app/app-routing.module.ts

```ts
import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

import { ChatComponent } from './pages/chat/chat.component';
import { AnalyticsComponent } from './pages/analytics/analytics.component';
import { RedirectComponent } from './auth/redirect.component';
import { AuthGuard } from './auth/auth.guard';

const routes: Routes = [

  { path: 'redirect', component: RedirectComponent },

  {
    path: 'chat',
    component: ChatComponent,
    canActivate: [AuthGuard]
  },

  {
    path: 'analytics',
    component: AnalyticsComponent,
    canActivate: [AuthGuard]
  },

  { path: '', redirectTo: 'chat', pathMatch: 'full' },

  { path: '**', redirectTo: 'chat' }
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule {}
```

---

# 📁 src/app/app.module.ts

```ts
import { NgModule, APP_INITIALIZER } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { HttpClientModule, HTTP_INTERCEPTORS } from '@angular/common/http';
import { OAuthModule } from 'angular-oauth2-oidc';

import { AppComponent } from './app.component';
import { RedirectComponent } from './auth/redirect.component';
import { ChatComponent } from './pages/chat/chat.component';
import { AnalyticsComponent } from './pages/analytics/analytics.component';
import { AuthInterceptor } from './auth/auth.interceptor';
import { AuthService } from './auth/auth.service';
import { AppRoutingModule } from './app-routing.module';

export function initializeApp(authService: AuthService) {
  return () => authService.initAuth();
}

@NgModule({
  declarations: [
    AppComponent,
    RedirectComponent,
    ChatComponent,
    AnalyticsComponent
  ],
  imports: [
    BrowserModule,
    HttpClientModule,
    OAuthModule.forRoot(),
    AppRoutingModule
  ],
  providers: [
    {
      provide: APP_INITIALIZER,
      useFactory: initializeApp,
      deps: [AuthService],
      multi: true
    },
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

# ===============================

# 🟢 BACKEND – FASTAPI COMPLET

# ===============================

Installer :

```bash
pip install fastapi uvicorn python-jose requests
```

---

# 📁 config.py

```python
import os

OIDC_ISSUER = "https://ssoforms.dev.echonet/affwebservices/CASSO/oidc/DATABASE_oracle-tuning-ai-stg"
OIDC_AUDIENCE = "DATABASE_oracle-tuning-ai-stg"

MOCK_AUTH = os.getenv("MOCK_AUTH", "false") == "true"
```

---

# 📁 security.py

```python
import requests
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt
from config import OIDC_ISSUER, OIDC_AUDIENCE, MOCK_AUTH

security = HTTPBearer(auto_error=False)

jwks = requests.get(f"{OIDC_ISSUER}/jwks").json()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):

    if MOCK_AUTH:
        return {
            "sub": "dev-user",
            "email": "dev@local",
            "roles": ["ADMIN"]
        }

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            audience=OIDC_AUDIENCE,
            issuer=OIDC_ISSUER
        )
        return payload

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
```

---

# 📁 main.py

```python
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from security import verify_token

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://database-oracle-tuning-ai-stg.xmp.net.intra"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/secure")
def secure_route(user=Depends(verify_token)):
    return {
        "message": "Authenticated",
        "user": user
    }

@app.get("/chat")
def chat(user=Depends(verify_token)):
    return {"chat": "ok", "user": user}

@app.get("/analytics")
def analytics(user=Depends(verify_token)):
    return {"analytics": "ok", "user": user}
```

---

# ===============================

# 🟢 À CONFIGURER CÔTÉ SSO

# ===============================

Redirect URI :

```
https://ton-domaine/redirect
```

Web Origin :

```
https://ton-domaine
```

Flow autorisé :

* Authorization Code
* PKCE
* RS256

---

# 🚀 FLOW FINAL

1. User ouvre `/chat`
2. AuthGuard détecte absence token
3. Redirection SSO
4. Login
5. Retour `/redirect`
6. Token stocké
7. Interceptor envoie Bearer automatiquement
8. Backend valide via JWKS

---

Si tu veux maintenant :

🔐 version full backend enterprise (tokens jamais exposés au browser)
🔄 refresh token silencieux avancé
🧱 architecture modulaire Angular propre (lazy loading)

Dis-moi.
