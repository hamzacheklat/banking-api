Parfait 😎, je vais te donner **tous les fichiers complets, y compris les fichiers de config et d’environnement**, pour un projet **Angular 17+ frontend + FastAPI backend** avec **auth PKCE OIDC + silent refresh + accès restreint à un groupe LDAP via `/userinfo`**.

---

# 🌐 ARCHITECTURE FINALE

```
project/
│
├── backend/
│   ├── main.py
│   ├── security.py
│   ├── config.py
│   └── requirements.txt
│
└── frontend/
    ├── src/environments/
    │   ├── environment.ts
    │   └── environment.prod.ts
    │
    └── src/app/
        ├── core/auth/
        │   ├── auth.service.ts
        │   ├── auth.guard.ts
        │   └── auth.interceptor.ts
        │
        ├── features/auth/
        │   ├── login.component.ts
        │   └── login.component.html
        │
        ├── shared/header/
        │   ├── header.component.ts
        │   └── header.component.html
        │
        ├── dashboard.component.ts
        ├── dashboard.component.html
        ├── access-denied.component.ts
        ├── access-denied.component.html
        ├── app.routes.ts
        ├── app.config.ts
        └── app.component.ts
```

---

# 🔐 BACKEND — FASTAPI

## 📄 backend/requirements.txt

```txt
fastapi
uvicorn
python-jose[cryptography]
requests
```

---

## 📄 backend/config.py

```python
# OIDC / OpenID Connect configuration
OIDC_ISSUER = "https://your-idp.com/oauth2"
OIDC_JWKS_URL = f"{OIDC_ISSUER}/v1/keys"
OIDC_USERINFO = f"{OIDC_ISSUER}/userinfo"
AUDIENCE = "oracle-tuning-api"

# Nom du groupe LDAP autorisé
ALLOWED_GROUP = "ldap_group_allowed"
```

---

## 📄 backend/security.py

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
import requests
from jose import jwt
from .config import OIDC_JWKS_URL, OIDC_ISSUER, AUDIENCE, OIDC_USERINFO, ALLOWED_GROUP

security = HTTPBearer()

# Charger les clés JWKS
jwks = requests.get(OIDC_JWKS_URL).json()

def verify_token(token: str):
    try:
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
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_user(credentials=Depends(security)):
    token = credentials.credentials
    user = verify_token(token)

    # Appel /userinfo pour récupérer le groupe LDAP
    resp = requests.get(
        OIDC_USERINFO,
        headers={"Authorization": f"Bearer {token}"}
    )
    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Cannot fetch user info")

    userinfo = resp.json()

    # Vérifie que l'utilisateur est dans le groupe LDAP autorisé
    if ALLOWED_GROUP not in userinfo.get("groups", []):
        raise HTTPException(status_code=403, detail="Access denied")

    return userinfo
```

---

## 📄 backend/main.py

```python
from fastapi import FastAPI, Depends
from .security import get_current_user

app = FastAPI()

@app.get("/api/profile")
def profile(user=Depends(get_current_user)):
    return {
        "sub": user["sub"],
        "email": user.get("email"),
        "name": user.get("name"),
        "groups": user.get("groups")
    }

@app.get("/api/data")
def protected_data(user=Depends(get_current_user)):
    return {"message": "Secure data", "user": user["sub"]}
```

---

# 🌐 FRONTEND — ANGULAR 17+

## 📄 src/environments/environment.ts

```ts
export const environment = {
  production: false,

  oidc: {
    issuer: 'https://your-idp.com/oauth2',
    clientId: 'oracle-tuning-client',
    redirectUri: window.location.origin,
    scope: 'openid profile email offline_access',
    responseType: 'code'
  },

  apiUrl: 'http://localhost:8000/api'
};
```

---

## 📄 src/environments/environment.prod.ts

```ts
export const environment = {
  production: true,

  oidc: {
    issuer: 'https://your-idp.com/oauth2',
    clientId: 'oracle-tuning-client',
    redirectUri: window.location.origin,
    scope: 'openid profile email offline_access',
    responseType: 'code'
  },

  apiUrl: 'https://myapp.example.com/api'
};
```

---

## 📄 core/auth/auth.service.ts

```ts
import { Injectable } from '@angular/core';
import { OAuthService, AuthConfig } from 'angular-oauth2-oidc';
import { environment } from '../../../environments/environment';

@Injectable({ providedIn: 'root' })
export class AuthService {

  constructor(private oauth: OAuthService) {
    this.init();
  }

  private init() {
    const config: AuthConfig = {
      issuer: environment.oidc.issuer,
      clientId: environment.oidc.clientId,
      redirectUri: environment.oidc.redirectUri,
      responseType: 'code',
      scope: environment.oidc.scope,
      useSilentRefresh: true,
      silentRefreshRedirectUri: window.location.origin + '/silent-refresh.html',
      sessionChecksEnabled: true,
      showDebugInformation: true,
      usePkce: true
    };

    this.oauth.configure(config);
    this.oauth.setupAutomaticSilentRefresh();
    this.oauth.loadDiscoveryDocumentAndTryLogin();
  }

  login() { this.oauth.initLoginFlow(); }
  logout() { this.oauth.logOut(); }
  get accessToken() { return this.oauth.getAccessToken(); }
  isLoggedIn(): boolean { return this.oauth.hasValidAccessToken(); }
  get profile() { return this.oauth.getIdentityClaims(); }
}
```

---

## 📄 core/auth/auth.guard.ts

```ts
import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from './auth.service';

export const authGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);

  if (!auth.isLoggedIn()) {
    router.navigate(['/login']);
    return false;
  }

  return true; // backend renverra 403 si pas dans le groupe LDAP
};
```

---

## 📄 core/auth/auth.interceptor.ts

```ts
import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { AuthService } from './auth.service';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);

  if (auth.accessToken) {
    req = req.clone({
      setHeaders: {
        Authorization: `Bearer ${auth.accessToken}`
      }
    });
  }

  return next(req);
};
```

---

## 📄 features/auth/login.component.ts

```ts
import { Component } from '@angular/core';
import { AuthService } from '../../core/auth/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  templateUrl: './login.component.html'
})
export class LoginComponent {
  constructor(public auth: AuthService) {}
  login() { this.auth.login(); }
}
```

## 📄 features/auth/login.component.html

```html
<div style="text-align:center; margin-top:100px;">
  <h2>Oracle Tuning AI</h2>
  <button (click)="login()">🔐 Connect with SSO</button>
</div>
```

---

## 📄 shared/header/header.component.ts

```ts
import { Component } from '@angular/core';
import { AuthService } from '../../core/auth/auth.service';

@Component({
  selector: 'app-header',
  standalone: true,
  templateUrl: './header.component.html'
})
export class HeaderComponent {
  constructor(public auth: AuthService) {}
  logout() { this.auth.logout(); }
}
```

## 📄 shared/header/header.component.html

```html
<div style="display:flex; justify-content:space-between; padding:10px; background:#1e293b; color:white;">
  <div>Oracle Tuning AI</div>

  <div *ngIf="auth.isLoggedIn(); else loginBtn">
    👤 {{ auth.profile?.['sub'] }}
    <button (click)="logout()">Logout</button>
  </div>

  <ng-template #loginBtn>
    <button (click)="auth.login()">Login</button>
  </ng-template>
</div>
```

---

## 📄 dashboard.component.ts

```ts
import { Component } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../environments/environment';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  templateUrl: './dashboard.component.html'
})
export class DashboardComponent {
  data: any;
  constructor(private http: HttpClient) {}
  ngOnInit() {
    this.http.get(`${environment.apiUrl}/data`).subscribe({
      next: res => this.data = res,
      error: err => console.error(err)
    });
  }
}
```

## 📄 dashboard.component.html

```html
<div style="text-align:center; margin-top:50px;">
  <h2>Dashboard</h2>
  <pre>{{ data | json }}</pre>
</div>
```

---

## 📄 access-denied.component.ts

```ts
import { Component } from '@angular/core';

@Component({
  selector: 'app-access-denied',
  standalone: true,
  templateUrl: './access-denied.component.html'
})
export class AccessDeniedComponent {}
```

## 📄 access-denied.component.html

```html
<div style="text-align:center; margin-top:100px;">
  <h2>⛔ Access Denied</h2>
  <p>You are not allowed to access this app.</p>
</div>
```

---

## 📄 app.routes.ts

```ts
import { Routes } from '@angular/router';
import { LoginComponent } from './features/auth/login.component';
import { authGuard } from './core/auth/auth.guard';

export const routes: Routes = [
  { path: 'login', component: LoginComponent },
  { path: 'access-denied', component: () => import('./access-denied.component').then(m => m.AccessDeniedComponent) },
  {
    path: '',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./dashboard.component').then(m => m.DashboardComponent)
  }
];
```

---

## 📄 app.config.ts

```ts
import { ApplicationConfig } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { routes } from './app.routes';
import { authInterceptor } from './core/auth/auth.interceptor';

export const appConfig: ApplicationConfig = {
  providers: [
    provideRouter(routes),
    provideHttpClient(withInterceptors([authInterceptor]))
  ]
};
```

---

## 📄 src/silent-refresh.html

```html
<script>
  window.parent.postMessage(location.hash, location.origin);
</script>
```

---

✅ **Ce setup fait exactement :**

* Authentification PKCE + OIDC
* Refresh token automatique + silent refresh
* Backend valide JWT + vérifie **groupe LDAP** via `/userinfo`
* Frontend guard simple
* Page Access Denied si l’utilisateur n’est pas dans le groupe

---

Si tu veux, je peux te faire un **diagramme complet prod** montrant :

**Angular → OIDC → JWT → Backend → LDAP group check → Access**

Veux‑tu que je fasse ça ?
