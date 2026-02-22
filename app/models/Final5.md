Parfait 👍
Tu as raison : **`CanActivate` est déprécié** (Angular 16+).
La **bonne pratique actuelle** est d’utiliser les **guards fonctionnels** :

👉 **`CanMatchFn`** (recommandé)
👉 ou `CanActivateFn` (encore supporté mais moins clean)

Ici on va faire **la version moderne, propre, future-proof** avec **`CanMatchFn`**.

---

# 🎯 RÉCAP OBJECTIF (inchangé)

* ✅ SSO obligatoire en **prod**
* ✅ **Pas de page login**
* ✅ Toutes les pages protégées
* ✅ **401 → SSO**
* ✅ **403 → page Forbidden**
* ✅ **LOCAL (`production=false`) → skip auth**
* ✅ Aucun token côté Angular

---

# ===============================

# 🟣 FRONTEND ANGULAR (MODERNE)

# ===============================

## 1️⃣ Environnements

### `environment.ts` (LOCAL)

```ts
export const environment = {
  production: false
};
```

### `environment.prod.ts` (STG / PROD)

```ts
export const environment = {
  production: true
};
```

---

## 2️⃣ Page Forbidden

### `forbidden.component.ts`

```ts
import { Component } from '@angular/core';

@Component({
  selector: 'app-forbidden',
  template: `
    <div class="forbidden">
      <h1>🚫 Accès interdit</h1>
      <p>Vous n’avez pas les droits pour accéder à cette application.</p>
      <p>Veuillez demander des accès.</p>
    </div>
  `,
  styles: [`
    .forbidden {
      height: 100vh;
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      text-align: center;
    }
  `]
})
export class ForbiddenComponent {}
```

---

## 3️⃣ Guard fonctionnel (✅ moderne)

### `auth.guard.ts`

```ts
import { inject } from '@angular/core';
import { CanMatchFn, Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { environment } from '../environments/environment';
import { firstValueFrom } from 'rxjs';

export const authGuard: CanMatchFn = async () => {

  // 🧪 LOCAL DEV → SKIP AUTH
  if (!environment.production) {
    return true;
  }

  const http = inject(HttpClient);
  const router = inject(Router);

  const API =
    'https://oracle-ai-api-stg.echonet.bnpparibas.com/api';

  try {
    await firstValueFrom(
      http.get(`${API}/session`, {
        withCredentials: true
      })
    );
    return true;

  } catch (err: any) {

    // 🔐 Pas authentifié → SSO
    if (err.status === 401) {
      window.location.href =
        'https://oracle-ai-api-stg.echonet.bnpparibas.com/api/login';
      return false;
    }

    // 🚫 Auth mais pas autorisé
    if (err.status === 403) {
      router.navigate(['/forbidden']);
      return false;
    }

    return false;
  }
};
```

✔ Pas de classe
✔ Pas de décorateur
✔ Compatible Angular 16 / 17 / 18

---

## 4️⃣ Routing Angular (protège TOUT)

### `app-routing.module.ts`

```ts
import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { ChatComponent } from './chat/chat.component';
import { AnalyticsComponent } from './analytics/analytics.component';
import { ForbiddenComponent } from './forbidden/forbidden.component';
import { authGuard } from './auth.guard';

const routes: Routes = [
  {
    path: 'chat',
    component: ChatComponent,
    canMatch: [authGuard]
  },
  {
    path: 'analytics',
    component: AnalyticsComponent,
    canMatch: [authGuard]
  },
  {
    path: 'forbidden',
    component: ForbiddenComponent
  },
  {
    path: '',
    redirectTo: 'chat',
    pathMatch: 'full'
  }
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule {}
```

👉 **Aucune page ne peut matcher la route sans auth**

---

# ===============================

# 🟢 BACKEND FASTAPI

# ===============================

## 5️⃣ Endpoint `/api/session` (AUTH + AUTHZ)

### `main.py`

```python
from fastapi import Depends, HTTPException

@app.get("/api/session")
async def session(user=Depends(get_current_user)):

    # Exemple: contrôle par groupes LDAP / claims JWT
    allowed_groups = {"oracle-ai-users", "oracle-ai-admins"}
    user_groups = set(user.get("groups", []))

    if not user_groups & allowed_groups:
        raise HTTPException(
            status_code=403,
            detail="User has no access"
        )

    return {"authenticated": True}
```

### Comportement

| Cas                          | HTTP |
| ---------------------------- | ---- |
| Pas de cookie / JWT invalide | 401  |
| Auth OK mais pas autorisé    | 403  |
| OK                           | 200  |

---

# ===============================

# 🔄 FLOW FINAL

# ===============================

## 🔹 PROD – user non connecté

```
/chat
↓
canMatch
↓
GET /api/session → 401
↓
Redirect /api/login
↓
SSO
```

---

## 🔹 PROD – user sans droits

```
/analytics
↓
canMatch
↓
GET /api/session → 403
↓
/forbidden
```

---

## 🔹 LOCAL DEV

```
environment.production = false
↓
canMatch → true
↓
Toutes les pages accessibles
```

---

# 🏆 CE QUE TU AS MAINTENANT

✅ Angular moderne (sans API dépréciée)
✅ Auth SSO **automatique & globale**
✅ Forbidden page propre
✅ Dev local fluide
✅ Sécurité enterprise

---

## 🚀 BONUS (si tu veux encore mieux)

* Accès **par page** (`chat` vs `analytics`)
* `returnUrl` automatique après SSO
* Cache session (éviter appel `/session` à chaque route)
* CSRF double-cookie
* Refresh token silencieux dans `/session`

Dis-moi, on est **pile dans les standards Angular + SSO enterprise** 👌
