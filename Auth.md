Parfait 👌 on va faire **la solution 3 proprement** :
👉 **désactiver complètement OIDC en local** et utiliser un **mock auth simple**.

Tu utilises `angular-oauth2-oidc`, donc on va rendre son init conditionnel.

---

# ✅ Étape 1 — Modifier `environment.ts`

### 🔹 environment.ts (LOCAL)

```ts
export const environment = {
  production: false,
  mockAuth: true,   // 👈 AJOUTE ÇA
  oidc: {
    issuer: '',
    clientId: '',
    scope: ''
  }
};
```

---

### 🔹 environment.prod.ts

```ts
export const environment = {
  production: true,
  mockAuth: false,  // 👈 IMPORTANT
  oidc: {
    issuer: 'https://ton-vrai-issuer',
    clientId: 'client-id',
    scope: 'openid profile email'
  }
};
```

---

# ✅ Étape 2 — Modifier ton `AuthService`

Dans ta capture je vois :

```ts
constructor(private oauth: OAuthService) {
  this.init();
}
```

On va le rendre conditionnel.

---

## 🔹 Nouveau `AuthService`

```ts
import { Injectable } from '@angular/core';
import { OAuthService } from 'angular-oauth2-oidc';
import { authConfig } from './auth.config';
import { environment } from '../../environments/environment';

@Injectable({ providedIn: 'root' })
export class AuthService {

  private fakeUser = {
    name: 'Dev User',
    email: 'dev@local',
    roles: ['ADMIN']
  };

  constructor(private oauth: OAuthService) {
    if (!environment.mockAuth) {
      this.init();
    }
  }

  async init(): Promise<void> {
    this.oauth.configure(authConfig);
    await this.oauth.loadDiscoveryDocumentAndTryLogin();
  }

  login(): void {
    if (environment.mockAuth) {
      console.log('Mock login');
      return;
    }
    this.oauth.initCodeFlow();
  }

  logout(): void {
    if (environment.mockAuth) {
      console.log('Mock logout');
      return;
    }
    this.oauth.logOut();
  }

  isAuthenticated(): boolean {
    if (environment.mockAuth) {
      return true;   // 👈 toujours connecté en local
    }
    return this.oauth.hasValidAccessToken();
  }

  getAccessToken(): string {
    if (environment.mockAuth) {
      return 'fake-token';
    }
    return this.oauth.getAccessToken();
  }

  getIdentityClaims(): any {
    if (environment.mockAuth) {
      return this.fakeUser;
    }
    return this.oauth.getIdentityClaims();
  }
}
```

---

# 🎯 Résultat

En local :

* ❌ Pas d’appel à `.well-known/openid-configuration`
* ❌ Pas de 404
* ❌ Pas besoin de fake JSON
* ✅ Toujours authentifié
* ✅ Token mock
* ✅ User mock

En prod :

* Tout fonctionne normalement avec ton vrai provider OIDC

---

# 🔥 BONUS (propre pour les guards)

Si tu as un `AuthGuard`, il fonctionnera automatiquement car :

```ts
isAuthenticated()
```

retourne `true` en local.

---

# 🚀 Conclusion

👉 Supprime ton fake `.well-known`
👉 Mets `mockAuth: true`
👉 Et c’est fini.

---

Si tu veux je peux aussi te faire une version encore plus clean avec injection conditionnelle pour ne même pas charger `angular-oauth2-oidc` en local 😉
