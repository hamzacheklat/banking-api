Parfait 👌
Voici la **version complète BACK + FRONT**, propre, stateless, middleware JWT global, autorisation par groupes, page forbidden, routing protégé.

Architecture :

* ✅ Authorization Code
* ✅ Pas de refresh
* ✅ Pas de store
* ✅ Backend stateless
* ✅ Middleware JWT global
* ✅ Vérification signature + audience
* ✅ Autorisation par groupes pour `/chat`
* ✅ Page 403 Forbidden
* ✅ Angular guard moderne (CanActivateFn)

---

# ============================

# 🔵 BACKEND — FASTAPI

# ============================

## 📁 Architecture

```text
backend/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── security.py
│   ├── dependencies.py
│   └── api/
│       └── routes.py
└── requirements.txt
```

---

## requirements.txt

```txt
fastapi
uvicorn
requests
python-jose[cryptography]
```

---

## config.py

```python
OIDC_BASE = "https://ssoforms.dev.echonet/affwebservices/CASSO/oidc/IV2PRODUCERS_dantestoidc"

AUTHORIZE_ENDPOINT = f"{OIDC_BASE}/authorize"
TOKEN_ENDPOINT = f"{OIDC_BASE}/token"
JWKS_ENDPOINT = f"{OIDC_BASE}/jwks"

CLIENT_ID = "YOUR_CLIENT_ID"
CLIENT_SECRET = "YOUR_CLIENT_SECRET"

FRONT_URL = "http://localhost:4200"
REDIRECT_URI = f"{FRONT_URL}/auth/callback"

ALLOWED_CHAT_GROUPS = ["oracle-ai-users", "oracle-ai-admins"]
```

---

## security.py (Middleware JWT Global)

```python
import requests
from jose import jwt
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from config import JWKS_ENDPOINT, CLIENT_ID

JWKS = requests.get(JWKS_ENDPOINT).json()

def verify_token(token: str):

    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header["kid"]

    key = next(k for k in JWKS["keys"] if k["kid"] == kid)

    return jwt.decode(
        token,
        key,
        algorithms=["RS256"],
        audience=CLIENT_ID
    )


class JWTMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):

        if request.url.path.startswith("/api/authorize") or \
           request.url.path.startswith("/api/token"):
            return await call_next(request)

        auth = request.headers.get("authorization")

        if not auth or not auth.startswith("Bearer "):
            raise HTTPException(status_code=401)

        token = auth.replace("Bearer ", "")

        try:
            payload = verify_token(token)
            request.state.user = payload
        except Exception:
            raise HTTPException(status_code=401)

        return await call_next(request)
```

---

## dependencies.py (Authorization par groupes)

```python
from fastapi import Request, HTTPException
from config import ALLOWED_CHAT_GROUPS

def require_chat_group(request: Request):

    user = request.state.user
    groups = user.get("groups", [])

    if not any(group in ALLOWED_CHAT_GROUPS for group in groups):
        raise HTTPException(status_code=403)

    return user
```

---

## api/routes.py

```python
from fastapi import APIRouter, Depends, Request
from dependencies import require_chat_group

router = APIRouter()

@router.get("/chat")
def chat(user = Depends(require_chat_group)):
    return {
        "message": "Chat OK",
        "user": user.get("preferred_username")
    }

@router.get("/analytics")
def analytics(request: Request):
    return {
        "message": "Analytics OK",
        "user": request.state.user.get("preferred_username")
    }
```

---

## main.py

```python
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
import urllib.parse
import secrets

from config import *
from security import JWTMiddleware
from api.routes import router as api_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONT_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(JWTMiddleware)

# ===============================
# AUTHORIZE
# ===============================

@app.get("/api/authorize")
def authorize():

    state = secrets.token_urlsafe(32)
    encoded_redirect = urllib.parse.quote(REDIRECT_URI, safe="")

    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "scope": "openid profile",
        "redirect_uri": encoded_redirect,
        "state": state,
        "authentication_method": "siteminder"
    }

    query = "&".join(f"{k}={v}" for k, v in params.items())

    return {
        "authorize_url": f"{AUTHORIZE_ENDPOINT}?{query}"
    }

# ===============================
# TOKEN
# ===============================

@app.post("/api/token")
def token(payload: dict):

    code = payload.get("code")
    encoded_redirect = urllib.parse.quote(REDIRECT_URI, safe="")

    response = requests.post(
        TOKEN_ENDPOINT,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": encoded_redirect,
            "code": code,
            "grant_type": "authorization_code",
            "scope": "openid profile"
        }
    )

    if response.status_code != 200:
        raise HTTPException(status_code=401)

    tokens = response.json()

    return {
        "access_token": tokens.get("access_token"),
        "expires_in": tokens.get("expires_in")
    }

app.include_router(api_router, prefix="/api")
```

---

# ============================

# 🟣 FRONTEND — ANGULAR

# ============================

## 📁 Architecture

```text
frontend/src/app/
├── auth/
│   ├── auth.service.ts
│   ├── auth.interceptor.ts
│   ├── auth.guard.ts
│   └── auth-callback.component.ts
├── pages/
│   ├── chat.component.ts
│   ├── analytics.component.ts
│   └── forbidden.component.ts
├── app-routing.module.ts
├── app.module.ts
└── app.component.ts
```

---

## auth.service.ts

```ts
@Injectable({ providedIn: 'root' })
export class AuthService {

  setToken(token: string) {
    sessionStorage.setItem('access_token', token);
  }

  getToken() {
    return sessionStorage.getItem('access_token');
  }

  clear() {
    sessionStorage.clear();
  }

  isAuthenticated() {
    return !!this.getToken();
  }
}
```

---

## auth.guard.ts (Functional)

```ts
import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from './auth.service';

export const authGuard: CanActivateFn = () => {

  const auth = inject(AuthService);
  const router = inject(Router);

  if (auth.isAuthenticated()) return true;

  router.navigate(['/forbidden']);
  return false;
};
```

---

## forbidden.component.ts

```ts
@Component({
  template: `
    <div style="text-align:center;margin-top:120px">
      <h1>403 - Access Denied</h1>
      <p>Please request access to this site.</p>
    </div>
  `
})
export class ForbiddenComponent {}
```

---

## auth.interceptor.ts

```ts
@Injectable()
export class AuthInterceptor implements HttpInterceptor {

  constructor(private auth: AuthService) {}

  intercept(req: HttpRequest<any>, next: HttpHandler) {

    const token = this.auth.getToken();

    if (token) {
      req = req.clone({
        setHeaders: { Authorization: `Bearer ${token}` }
      });
    }

    return next.handle(req).pipe(
      catchError(err => {

        if (err.status === 401) {
          this.auth.clear();
          window.location.href = '/api/authorize';
        }

        throw err;
      })
    );
  }
}
```

---

## auth-callback.component.ts

```ts
@Component({ template: `<p>Authenticating...</p>` })
export class AuthCallbackComponent implements OnInit {

  constructor(
    private route: ActivatedRoute,
    private http: HttpClient,
    private auth: AuthService,
    private router: Router
  ) {}

  ngOnInit() {

    const code = this.route.snapshot.queryParamMap.get('code');

    this.http.post<any>('/api/token', { code })
      .subscribe(res => {
        this.auth.setToken(res.access_token);
        this.router.navigate(['/chat']);
      });
  }
}
```

---

## chat.component.ts

```ts
@Component({
  template: `
    <h2>Chat</h2>
    <button (click)="call()">Call API</button>
    <p>{{message}}</p>
  `
})
export class ChatComponent {

  message = '';

  constructor(private http: HttpClient) {}

  call() {
    this.http.get<any>('/api/chat')
      .subscribe(res => this.message = res.message);
  }
}
```

---

## analytics.component.ts

```ts
@Component({
  template: `
    <h2>Analytics</h2>
    <button (click)="call()">Call API</button>
    <p>{{message}}</p>
  `
})
export class AnalyticsComponent {

  message = '';

  constructor(private http: HttpClient) {}

  call() {
    this.http.get<any>('/api/analytics')
      .subscribe(res => this.message = res.message);
  }
}
```

---

## app-routing.module.ts

```ts
const routes: Routes = [
  { path: 'auth/callback', component: AuthCallbackComponent },
  { path: 'chat', component: ChatComponent, canActivate: [authGuard] },
  { path: 'analytics', component: AnalyticsComponent, canActivate: [authGuard] },
  { path: 'forbidden', component: ForbiddenComponent },
  { path: '', redirectTo: 'chat', pathMatch: 'full' }
];
```

---

## app.component.ts

```ts
@Component({
  selector: 'app-root',
  template: '<router-outlet></router-outlet>'
})
export class AppComponent implements OnInit {

  constructor(private http: HttpClient) {}

  ngOnInit() {
    if (!sessionStorage.getItem('access_token')) {
      this.http.get<any>('/api/authorize')
        .subscribe(res => window.location.href = res.authorize_url);
    }
  }
}
```

---

# ✅ Résultat Final

✔ Backend stateless
✔ Middleware JWT global
✔ Vérification signature
✔ Autorisation par groupes
✔ Front protégé par guard
✔ Page 403 Forbidden
✔ Pas de refresh
✔ Pas de store
✔ Kubernetes ready

---

Si tu veux maintenant on peut :

* 🔐 Ajouter vérification issuer + exp stricte
* 🚀 Ajouter cache JWKS intelligent
* 🏦 Ajouter RBAC multi-rôles
* 🧠 Faire version Angular standalone 17 clean
* 🔎 Faire audit sécurité complet

On monte encore d’un niveau ?
