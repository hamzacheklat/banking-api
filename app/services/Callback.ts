// auth-init.service.ts
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { environment } from '../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class AuthInitService {
  private redirectRequested = false;

  constructor(
    private http: HttpClient,
    private router: Router
  ) {}

  async ensureAuthorized(): Promise<void> {
    const currentUrl = window.location.pathname;

    if (currentUrl.includes('searchString')) {
      return;
    }

    if (this.isAuthenticated()) {
      return;
    }

    if (this.redirectRequested) {
      return;
    }

    try {
      // URL de redirection FIXE côté serveur
      const redirectUri = 'https://url-de-dev.com/callback';
      
      // Construire les paramètres OAuth
      const params = new URLSearchParams({
        client_id: environment.clientId,
        redirect_uri: redirectUri,
        response_type: 'code',
        scope: 'openid profile',
        state: JSON.stringify({
          return_to: currentUrl + window.location.search,
          local_return: window.location.origin
        })
      });

      const authUrl = `https://${environment.apiUrl}/auth/authorize?${params.toString()}`;
      
      this.redirectRequested = true;
      
      // Stocker l'URL de retour
      sessionStorage.setItem('auth_return_to', currentUrl + window.location.search);
      
      // Rediriger vers l'auth
      window.location.href = authUrl;

    } catch (err) {
      console.error('Erreur lors de l\'authentification:', err);
    }
  }

  isAuthenticated(): boolean {
    return !!localStorage.getItem('access_token');
  }
}
