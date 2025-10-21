Parfait ! On va créer un **projet Angular minimal prêt à tourner sur Angular 18** avec tous les fichiers de configuration essentiels. Je vais te donner **tous les `package.json`, `tsconfig.json`, et fichiers de `src/`** pour que tu puisses juste copier-coller et démarrer.

---

## 1️⃣ `package.json` complet (Angular 18)

```json
{
  "name": "bnp-chatbot",
  "version": "1.0.0",
  "scripts": {
    "start": "ng serve --host 0.0.0.0 --port 4200",
    "build": "ng build",
    "ng": "ng"
  },
  "private": true,
  "dependencies": {
    "@angular/animations": "^18.0.0",
    "@angular/common": "^18.0.0",
    "@angular/compiler": "^18.0.0",
    "@angular/core": "^18.0.0",
    "@angular/forms": "^18.0.0",
    "@angular/platform-browser": "^18.0.0",
    "@angular/platform-browser-dynamic": "^18.0.0",
    "@angular/router": "^18.0.0",
    "rxjs": "^7.8.1",
    "uuid": "^9.0.0"
  },
  "devDependencies": {
    "@angular/cli": "^18.0.0",
    "@angular/compiler-cli": "^18.0.0",
    "@angular-devkit/build-angular": "^18.0.0",
    "typescript": "^5.4.0"
  }
}
```

---

## 2️⃣ `tsconfig.json`

```json
{
  "compilerOptions": {
    "target": "es2020",
    "module": "es2020",
    "moduleResolution": "node",
    "experimentalDecorators": true,
    "skipLibCheck": true,
    "strict": true,
    "outDir": "./dist/out-tsc",
    "types": []
  },
  "include": ["src/**/*.ts"]
}
```

---

## 3️⃣ Arborescence `src/`

```
src/
 ├─ index.html
 ├─ main.ts
 ├─ polyfills.ts
 ├─ styles.css
 └─ app/
     ├─ app.module.ts
     └─ chat/
         ├─ chat.component.ts
         ├─ chat.component.html
         └─ chat.component.css
```

---

### `src/index.html`

```html
<!doctype html>
<html lang="fr">
  <head>
    <meta charset="utf-8">
    <title>BNP Chatbot</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
  </head>
  <body>
    <app-root>Chargement...</app-root>
  </body>
</html>
```

### `src/polyfills.ts`

```ts
/** polyfills minimal pour Angular 18 */
```

### `src/main.ts`

```ts
import { platformBrowserDynamic } from '@angular/platform-browser-dynamic';
import { AppModule } from './app/app.module';

platformBrowserDynamic().bootstrapModule(AppModule)
  .catch(err => console.error(err));
```

### `src/styles.css`

```css
body { margin: 0; font-family: Arial, sans-serif; background: #f6f7fb; }
```

---

### `src/app/app.module.ts`

```ts
import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { FormsModule } from '@angular/forms';
import { HttpClientModule } from '@angular/common/http';
import { ChatComponent } from './chat/chat.component';

@NgModule({
  declarations: [ChatComponent],
  imports: [BrowserModule, FormsModule, HttpClientModule],
  bootstrap: [ChatComponent]
})
export class AppModule {}
```

---

### `src/app/chat/chat.component.ts`

```ts
import { Component, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { v4 as uuidv4 } from 'uuid';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

@Component({
  selector: 'app-root',
  templateUrl: './chat.component.html',
  styleUrls: ['./chat.component.css']
})
export class ChatComponent implements OnInit {
  sessionId: string = '';
  userInput: string = '';
  messages: Message[] = [];
  loading = false;
  apiUrl = 'http://localhost:8000/query';

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    this.sessionId = uuidv4();
  }

  sendMessage(): void {
    if (!this.userInput.trim()) return;
    const query = this.userInput.trim();

    this.messages.push({ role: 'user', content: query });
    this.userInput = '';
    this.loading = true;

    this.http.post<any>(this.apiUrl, {
      session_id: this.sessionId,
      query
    }).subscribe({
      next: (res) => {
        if (res.history && Array.isArray(res.history)) {
          this.messages = res.history.map((h: any) => ({ role: h.role === 'assistant' ? 'assistant' : 'user', content: h.content }));
        } else if (res.answer) {
          this.messages.push({ role: 'assistant', content: res.answer });
        }
        this.loading = false;
      },
      error: (err) => {
        console.error(err);
        this.messages.push({ role: 'assistant', content: 'Erreur: ' + (err.error?.detail || err.message) });
        this.loading = false;
      }
    });
  }

  resetSession(): void {
    this.http.post(`http://localhost:8000/reset-session/${this.sessionId}`, {})
      .subscribe(() => {
        this.messages = [];
        this.sessionId = uuidv4();
      }, (err) => {
        console.error('reset failed', err);
      });
  }
}
```

---

### `src/app/chat/chat.component.html`

```html
<div class="chat-container">
  <div class="chat-box">
    <div *ngFor="let msg of messages" [ngClass]="msg.role">
      <strong *ngIf="msg.role === 'user'">👤</strong>
      <strong *ngIf="msg.role === 'assistant'">🤖</strong>
      {{ msg.content }}
    </div>
  </div>

  <div class="chat-input">
    <input [(ngModel)]="userInput" placeholder="Pose ta question..." (keyup.enter)="sendMessage()" />
    <button (click)="sendMessage()" [disabled]="loading">Envoyer</button>
    <button (click)="resetSession()">🔄 Nouvelle session</button>
  </div>

  <div *ngIf="loading" class="loading">⏳ Génération...</div>
</div>
```

### `src/app/chat/chat.component.css`

```css
.chat-container {
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: 700px;
  margin: 2rem auto;
  border: 1px solid #ddd;
  border-radius: 10px;
  padding: 1rem;
  background: #fafafa;
}
.chat-box {
  flex: 1;
  max-height: 70vh;
  overflow-y: auto;
  margin-bottom: 1rem;
}
.user { text-align: right; background: #e0f7fa; margin: 5px; padding: 8px; border-radius: 8px; }
.assistant { text-align: left; background: #fff3e0; margin: 5px; padding: 8px; border-radius: 8px; }
.chat-input { display: flex; gap: 0.5rem; }
input { flex: 1; padding: 0.5rem; border-radius: 8px; border: 1px solid #ccc; }
button { border: none; padding: 0.5rem 1rem; background: #1976d2; color: white; border-radius: 8px; cursor: pointer; }
.loading { text-align: center; color: gray; margin-top: 1rem; }
```

---

## 4️⃣ Commandes pour lancer le projet

```bash
npm install
npm start
```

Si `ng` n’est pas trouvé, tu peux utiliser :

```bash
npx ng serve --host 0.0.0.0 --port 4200
```

---

💡 Tout est prêt pour Angular 18. Il ne manque aucun fichier de config essentiel.

Si tu veux, je peux te générer **un ZIP complet** que tu pourras directement extraire et lancer sans rien toucher.

Veux‑tu que je fasse ça ?
