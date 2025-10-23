Super — je fais tout de suite la réécriture complète de la partie **Angular** en ajoutant **tous les fichiers manquants** (angular.json, tsconfig, polyfills, main, index, styles globaux, AppComponent, etc.) et j'améliore le style (responsive, cartes, avatars, couleur, boutons, loader animé). Tu pourras copier-coller l'arborescence directement dans ton repo `frontend-angular/`.

> Remarque : je garde ton `ChatComponent` comme composant principal (tu le bootstrapes depuis `AppModule`) pour rester fidèle à ton design initial.

---

# Arborescence (frontend-angular)

```
frontend-angular/
├─ package.json
├─ angular.json
├─ tsconfig.json
├─ tsconfig.app.json
├─ tsconfig.spec.json
├─ src/
│  ├─ index.html
│  ├─ main.ts
│  ├─ polyfills.ts
│  ├─ styles.css
│  └─ app/
│     ├─ app.module.ts
│     ├─ app.component.ts
│     ├─ app.component.html
│     ├─ app.component.css
│     ├─ services/
│     │  └─ api.service.ts
│     └─ chat/
│        ├─ chat.component.ts
│        ├─ chat.component.html
│        └─ chat.component.css
```

---

## `package.json` (mis à jour — version légère, compatible Angular 16)

```json
{
  "name": "rag-angular",
  "version": "0.0.1",
  "private": true,
  "scripts": {
    "ng": "ng",
    "start": "ng serve --port 4200 --host 0.0.0.0",
    "build": "ng build --configuration production",
    "test": "ng test",
    "lint": "ng lint"
  },
  "dependencies": {
    "@angular/animations": "^16.0.0",
    "@angular/common": "^16.0.0",
    "@angular/compiler": "^16.0.0",
    "@angular/core": "^16.0.0",
    "@angular/forms": "^16.0.0",
    "@angular/platform-browser": "^16.0.0",
    "@angular/platform-browser-dynamic": "^16.0.0",
    "@angular/router": "^16.0.0",
    "rxjs": "^7.8.0",
    "tslib": "^2.5.0",
    "zone.js": "~0.13.0"
  },
  "devDependencies": {
    "@angular-devkit/build-angular": "^16.0.0",
    "@angular/cli": "^16.0.0",
    "@angular/compiler-cli": "^16.0.0",
    "typescript": "~5.0.4"
  }
}
```

---

## `angular.json`

```json
{
  "$schema": "./node_modules/@angular/cli/lib/config/schema.json",
  "version": 1,
  "projects": {
    "rag-angular": {
      "projectType": "application",
      "schematics": {},
      "root": "",
      "sourceRoot": "src",
      "architect": {
        "build": {
          "builder": "@angular-devkit/build-angular:browser",
          "options": {
            "outputPath": "dist/rag-angular",
            "index": "src/index.html",
            "main": "src/main.ts",
            "polyfills": "src/polyfills.ts",
            "tsConfig": "tsconfig.app.json",
            "assets": ["src/favicon.ico"],
            "styles": ["src/styles.css"],
            "scripts": []
          },
          "configurations": {
            "production": {
              "fileReplacements": [
                {
                  "replace": "src/environments/environment.ts",
                  "with": "src/environments/environment.prod.ts"
                }
              ],
              "optimization": true,
              "sourceMap": false,
              "extractCss": true
            }
          }
        },
        "serve": {
          "builder": "@angular-devkit/build-angular:dev-server",
          "options": {
            "browserTarget": "rag-angular:build"
          }
        },
        "test": {
          "builder": "@angular-devkit/build-angular:karma",
          "options": {
            "main": "src/test.ts",
            "polyfills": "src/polyfills.ts",
            "tsConfig": "tsconfig.spec.json"
          }
        }
      }
    }
  },
  "defaultProject": "rag-angular"
}
```

---

## `tsconfig.json`

```json
{
  "compileOnSave": false,
  "compilerOptions": {
    "baseUrl": "./",
    "outDir": "./dist/out-tsc",
    "sourceMap": true,
    "declaration": false,
    "downlevelIteration": true,
    "experimentalDecorators": true,
    "module": "es2020",
    "moduleResolution": "node",
    "importHelpers": true,
    "target": "es2020",
    "typeRoots": ["node_modules/@types"],
    "lib": ["es2020", "dom"]
  }
}
```

---

## `tsconfig.app.json`

```json
{
  "extends": "./tsconfig.json",
  "compilerOptions": {
    "outDir": "./out-tsc/app",
    "types": []
  },
  "files": ["src/main.ts", "src/polyfills.ts"],
  "include": ["src/**/*.d.ts", "src/**/*.ts"]
}
```

---

## `tsconfig.spec.json`

```json
{
  "extends": "./tsconfig.json",
  "compilerOptions": {
    "outDir": "./out-tsc/spec",
    "types": ["jasmine", "node"]
  },
  "files": ["src/test.ts"],
  "include": ["src/**/*.spec.ts", "src/**/*.d.ts"]
}
```

---

## `src/polyfills.ts`

```ts
/**
 * Polyfills for Angular 16.
 *
 * This file includes polyfills needed by Angular and is loaded before the app.
 */

// Zone JS is required by default for Angular itself.
import 'zone.js';  // Included with Angular CLI.
```

---

## `src/main.ts`

```ts
import { platformBrowserDynamic } from '@angular/platform-browser-dynamic';
import { AppModule } from './app/app.module';

platformBrowserDynamic()
  .bootstrapModule(AppModule)
  .catch(err => console.error(err));
```

---

## `src/index.html`

```html
<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8" />
  <title>RAG - Angular</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <link rel="icon" type="image/x-icon" href="favicon.ico" />
</head>
<body>
  <app-root></app-root>
</body>
</html>
```

---

## `src/styles.css` (global — responsive + thème)

```css
:root{
  --bg:#0f1724;
  --card:#0b1220;
  --muted:#9aa6b2;
  --accent:#4fc3f7;
  --accent-2:#7ee787;
  --glass: rgba(255,255,255,0.03);
  --radius:12px;
  --max-width:980px;
  --shadow: 0 6px 20px rgba(2,6,23,0.6);
  font-family: Inter, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

*{box-sizing:border-box}
html,body{height:100%;margin:0;background: linear-gradient(180deg,#081226 0%, #071029 100%); color:#e6eef6}
a{color:var(--accent)}

.app-shell{
  max-width:var(--max-width);
  margin:28px auto;
  padding:22px;
  border-radius:16px;
  background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));
  box-shadow: var(--shadow);
  border: 1px solid rgba(255,255,255,0.03);
}

/* Header */
.header{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:16px;
  margin-bottom:18px;
}
.brand{
  display:flex;align-items:center;gap:12px;
}
.logo{
  width:48px;height:48px;border-radius:10px;background:linear-gradient(135deg,var(--accent),#2bb6f2);display:flex;align-items:center;justify-content:center;font-weight:700;color:#022032
}
.title{font-size:1.25rem;font-weight:600}
.subtitle{font-size:0.9rem;color:var(--muted)}

/* Controls */
.controls{display:flex;gap:12px;align-items:center}
.btn{
  background:var(--accent);color:#022032;padding:8px 12px;border-radius:10px;border:none;font-weight:600;cursor:pointer;
  box-shadow: 0 6px 18px rgba(79,195,247,0.12);
}
.btn.secondary{background:transparent;border:1px solid rgba(255,255,255,0.04);color:var(--muted)}
.btn:disabled{opacity:0.6;cursor:not-allowed}

/* Chat area */
.chat-wrap{display:flex;gap:18px}
.left{flex:1;min-width:260px;display:flex;flex-direction:column;gap:12px}
.right{width:320px;flex-shrink:0}

/* messages box */
.messages{
  height:520px;
  overflow:auto;
  padding:16px;
  border-radius:12px;
  background: linear-gradient(180deg, rgba(255,255,255,0.01), rgba(255,255,255,0.00));
  border: 1px solid rgba(255,255,255,0.025);
}
.msg{
  display:flex;gap:12px;margin:10px 0;align-items:flex-end;
}
.msg.user{justify-content:flex-end}
.avatar{
  width:36px;height:36px;border-radius:8px;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-weight:700;
}
.avatar.user{background:linear-gradient(135deg,#1e88e5,#4fc3f7);color:#022032}
.avatar.assistant{background:linear-gradient(135deg,#2e7d32,#7ee787);color:#04200a}

/* bubble */
.bubble{
  max-width:80%;
  padding:12px 14px;border-radius:12px;background:var(--glass);backdrop-filter: blur(6px);
  color:#eaf6ff;border:1px solid rgba(255,255,255,0.03);
}
.msg.user .bubble{background:linear-gradient(135deg, rgba(79,195,247,0.12), rgba(79,195,247,0.06)); color:#e7f8ff}
.meta{font-size:0.75rem;color:var(--muted);margin-top:6px}

/* input */
.composer{
  display:flex;gap:8px;margin-top:12px;align-items:center;
}
.composer input[type="text"]{
  flex:1;padding:12px;border-radius:10px;border:1px solid rgba(255,255,255,0.04);
  background:transparent;color:inherit;font-size:0.95rem;
}
.composer .send{min-width:120px}

/* right panel */
.panel-card{
  background: linear-gradient(180deg, rgba(255,255,255,0.01), rgba(255,255,255,0.00));
  padding:12px;border-radius:12px;border:1px solid rgba(255,255,255,0.02);
}
.panel-card h4{margin:0 0 8px 0;color:var(--accent)}
.small{font-size:0.85rem;color:var(--muted)}

/* loader */
.loader{
  display:inline-block;padding:6px 10px;border-radius:10px;background:linear-gradient(90deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));
}
.pulse{
  display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px;background:var(--accent);
  animation: pulse 1s infinite;
}
@keyframes pulse{0%{transform:scale(1);opacity:1}50%{transform:scale(1.6);opacity:0.5}100%{transform:scale(1);opacity:1}}

/* responsive */
@media (max-width:900px){
  .chat-wrap{flex-direction:column}
  .right{width:100%}
  .messages{height:420px}
}
```

---

## `src/app/app.module.ts` (module — bootstrape ChatComponent)

```ts
import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { HttpClientModule } from '@angular/common/http';
import { FormsModule } from '@angular/forms';

import { AppComponent } from './app.component';
import { ChatComponent } from './chat/chat.component';
import { ApiService } from './services/api.service';

@NgModule({
  declarations: [AppComponent, ChatComponent],
  imports: [BrowserModule, HttpClientModule, FormsModule],
  providers: [ApiService],
  bootstrap: [AppComponent]
})
export class AppModule {}
```

---

## `src/app/app.component.ts`

```ts
import { Component } from '@angular/core';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent {}
```

---

## `src/app/app.component.html`

```html
<div class="app-shell">
  <div class="header">
    <div class="brand">
      <div class="logo">RAG</div>
      <div>
        <div class="title">RAG interne — Confluence • Chroma • LiteLLM</div>
        <div class="subtitle">Angular 16 — Interface minimale & réactive</div>
      </div>
    </div>

    <div class="controls">
      <button class="btn" (click)="null">Docs</button>
      <button class="btn secondary" (click)="null">Paramètres</button>
    </div>
  </div>

  <app-chat></app-chat>
</div>
```

---

## `src/app/app.component.css`

```css
/* small adjustments for app wrapper (kept minimal) */
:host {display:block}
```

---

## `src/app/services/api.service.ts` (même que ta version, avec timeout option si tu veux)

```ts
import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class ApiService {
  // change si ton backend est proxifié / docker
  base = 'http://localhost:8000';

  constructor(private http: HttpClient) {}

  query(sessionId: string, query: string, top_k = 5): Observable<any> {
    const body = { session_id: sessionId, query, top_k };
    return this.http.post(`${this.base}/query`, body);
  }

  ingestConfluence(): Observable<any> {
    return this.http.post(`${this.base}/ingest_confluence`, {});
  }
}
```

---

## `src/app/chat/chat.component.ts` (amélioré — gestion erreurs, loader, copies)

```ts
import { Component, ElementRef, ViewChild } from '@angular/core';
import { ApiService } from '../services/api.service';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
}

@Component({
  selector: 'app-chat',
  templateUrl: './chat.component.html',
  styleUrls: ['./chat.component.css']
})
export class ChatComponent {
  sessionId = 'session-1';
  input = '';
  messages: Message[] = [];
  loading = false;

  @ViewChild('messagesBox') messagesBox!: ElementRef<HTMLDivElement>;

  constructor(private api: ApiService) {}

  private scrollToBottom() {
    try {
      setTimeout(() => {
        if (this.messagesBox && this.messagesBox.nativeElement) {
          const el = this.messagesBox.nativeElement;
          el.scrollTop = el.scrollHeight;
        }
      }, 50);
    } catch {}
  }

  send() {
    if (!this.input.trim() || this.loading) return;
    const q = this.input.trim();
    this.messages.push({ role: 'user', content: q, timestamp: new Date().toISOString() });
    this.input = '';
    this.loading = true;
    this.scrollToBottom();

    this.api.query(this.sessionId, q, 5).subscribe({
      next: (res) => {
        this.messages.push({
          role: 'assistant',
          content: res.answer || '— Pas de réponse —',
          timestamp: res.timestamp || new Date().toISOString()
        });
        this.loading = false;
        this.scrollToBottom();
      },
      error: (err) => {
        const detail = err.error?.detail || err.message || JSON.stringify(err);
        this.messages.push({
          role: 'assistant',
          content: 'Erreur: ' + detail,
          timestamp: new Date().toISOString()
        });
        this.loading = false;
        this.scrollToBottom();
      }
    });
  }

  runIngest() {
    if (this.loading) return;
    if (!confirm('Lancer l\'ingestion Confluence ?')) return;
    this.loading = true;
    this.api.ingestConfluence().subscribe({
      next: () => {
        alert('Ingestion terminée.');
        this.loading = false;
      },
      error: (e) => {
        alert('Erreur ingestion: ' + (e.error?.detail || e.message || JSON.stringify(e)));
        this.loading = false;
      }
    });
  }

  copy(text: string) {
    try {
      navigator.clipboard.writeText(text);
      alert('Copié dans le presse-papiers');
    } catch {
      alert('Impossible de copier');
    }
  }
}
```

---

## `src/app/chat/chat.component.html` (amélioré — UI)

```html
<div class="chat-wrap">
  <div class="left">
    <div class="controls" style="justify-content:space-between">
      <div>
        <button class="btn" (click)="runIngest()" [disabled]="loading">🔄 Ingest Confluence</button>
        <button class="btn secondary" (click)="messages=[]" [disabled]="loading">🧹 Clear</button>
      </div>
      <div class="small">Session: <b>{{sessionId}}</b></div>
    </div>

    <div class="messages" #messagesBox>
      <ng-container *ngIf="messages.length === 0">
        <div class="panel-card" style="text-align:center;margin:18px">
          <div style="font-weight:600">Prêt — pose une question à la base Confluence</div>
          <div class="small">Ex: "Comment configurer le déploiement ?" ou "Procédure backup Swift".</div>
        </div>
      </ng-container>

      <div *ngFor="let m of messages" class="msg" [ngClass]="{'user': m.role==='user', 'assistant': m.role==='assistant'}">
        <div class="avatar" [ngClass]="{'user': m.role==='user','assistant': m.role==='assistant'}">
          {{ m.role==='user' ? 'U' : 'A' }}
        </div>

        <div>
          <div class="bubble">
            <div [innerText]="m.content"></div>
            <div class="meta">
              <span>{{ m.role }} • {{ m.timestamp | date:'dd/MM/yyyy HH:mm:ss' }}</span>
              <button style="margin-left:10px" (click)="copy(m.content)">Copier</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="composer">
      <input type="text" [(ngModel)]="input" (keyup.enter)="send()" [disabled]="loading" placeholder="Pose ta question..." />
      <button class="btn send" (click)="send()" [disabled]="loading || !input.trim()">Envoyer</button>
    </div>

    <div style="margin-top:10px" *ngIf="loading">
      <div class="loader"><span class="pulse"></span>Traitement...</div>
    </div>
  </div>

  <div class="right">
    <div class="panel-card">
      <h4>Contexte & Astuces</h4>
      <div class="small">• Pose des questions précises (procédure, erreurs, how-to).</div>
      <div class="small">• Les réponses proviennent uniquement des documents ingestés.</div>
    </div>

    <div class="panel-card" style="margin-top:12px">
      <h4>Actions rapides</h4>
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        <button class="btn secondary" (click)="messages=[]">Clear chat</button>
        <button class="btn" (click)="runIngest()">Ingest maintenant</button>
      </div>
    </div>
  </div>
</div>
```

---

## `src/app/chat/chat.component.css` (amélioré — spécifique au composant)

```css
/* reuse global variables from styles.css; only small local tweaks here */
.button-inline{padding:6px 10px;border-radius:8px}

.messages .bubble button{
  background:transparent;border:none;color:var(--accent);cursor:pointer;font-weight:600;
}
.messages .bubble button:hover{opacity:0.9}
```

---

### ✅ Ce que je t'ai livré

* Tous les fichiers Angular essentiels (config + code) prêts à coller.
* Un UI plus moderne et responsive, loader animé, boutons, et copy-to-clipboard.
* Bootstrapping via `AppComponent` qui contient ton `ChatComponent`.

---

### ▶️ Étapes pour tester localement

1. Copier `frontend-angular/` avec les fichiers ci-dessus.
2. Dans `frontend-angular` :

```bash
npm install
npm start
```

3. Backend doit tourner sur `http://localhost:8000` (ou change `ApiService.base` si tu utilises docker).

---

Si tu veux, je peux ensuite :

* générer un **Dockerfile** + **nginx** config pour servir le build prod et un `docker-compose.yml` (backend + chroma + frontend nginx) comme tu proposais ;
* ou convertir le style en SCSS ou intégrer Tailwind/Material (nécessite dépendances supplémentaires).

Dis-moi ce que tu préfères — je peux directement te donner le `docker-compose.yml` + configs si tu veux le bundle complet.
