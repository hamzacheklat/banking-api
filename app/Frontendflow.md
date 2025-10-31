Top — je t’ai préparé **les modifications front** (Angular) pour consommer le **nouveau retour API RAG** (le dict renvoyé par `answer_query_with_date` : `answer`, `stats`, `date_range`, `lang`, `timestamp`, …) et afficher :

* la réponse du modèle (HTML marqué et sanitizé),
* un panneau de **statistiques** (total failed + top flows/tasks/causes),
* un bouton pour afficher les détails JSON si besoin.

Je fournis :

1. `chat.component.ts` (mis à jour),
2. `chat.component.html` (mis à jour),
3. petites notes à appliquer côté `ApiService` et backend.

---

# 1) `chat.component.ts` (version adaptée)

Remplace ton fichier par ceci (ou adapte les parties indiquées). J’ai gardé ta logique `ViewChild` / `scrollToBottom` et `marked` ; la partie principale change dans le `subscribe` pour exploiter `res.stats`, `res.date_range`, etc.

```ts
// chat.component.ts
import { Component, ElementRef, ViewChild } from '@angular/core';
import { ApiService } from '../services/api.service';
import { marked } from 'marked';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';

interface Message {
  role: 'user' | 'assistant';
  content: SafeHtml | string;
  timestamp?: string;
}

interface ApiStats {
  total_failed: number;
  flows: { [flow: string]: number };
  tasks: { [task: string]: number };
  failures: { [failure: string]: number };
}

interface RagApiResponse {
  answer: string;
  stats?: ApiStats;
  query?: string;
  lang?: string;
  date_range?: string;
  timestamp?: string;
  // any other optional fields
  [key: string]: any;
}

@Component({
  selector: 'app-chat',
  templateUrl: './chat.component.html',
  styleUrls: ['./chat.component.css']
})
export class ChatComponent {
  @ViewChild('chatContainer') chatContainer!: ElementRef;
  sessionId = 'session-vanish';
  input = '';
  messages: Message[] = [];
  Loading = false;

  // nouveau state pour stats provenant de l'API
  stats?: ApiStats;
  lastDateRange?: string;
  lastLang?: string;
  lastTimestamp?: string;
  showStats = true; // toggle d'affichage

  constructor(private api: ApiService, private sanitizer: DomSanitizer) {}

  async send() {
    if (!this.input.trim() || this.Loading) return;
    const question = this.input.trim();

    this.messages.push({ role: 'user', content: question });
    this.input = '';
    this.Loading = true;
    this.scrollToBottom();

    // Appel au back — j'ai conservé la signature existante (sessionId, question, top_k)
    this.api.query(this.sessionId, question, 8).subscribe({
      next: async (resRaw: any) => {
        // Caster vers la shape attendue
        const res: RagApiResponse = resRaw;

        // marked peut prendre du markdown; on convertit et on sanitize
        const rowHtml = await marked(res.answer || '');
        const html: SafeHtml = this.sanitizer.bypassSecurityTrustHtml(rowHtml);

        // push message assistant
        this.messages.push({
          role: 'assistant',
          content: html,
          timestamp: new Date(res.timestamp || new Date().toISOString()).toLocaleTimeString()
        });

        // stocker les stats si présentes
        if (res.stats) {
          this.stats = res.stats;
        } else {
          this.stats = undefined;
        }

        this.lastDateRange = res.date_range;
        this.lastLang = res.lang;
        this.lastTimestamp = res.timestamp;

        this.Loading = false;
        this.scrollToBottom();
      },
      error: (err: any) => {
        this.messages.push({
          role: 'assistant',
          content: '⚠️ Erreur : ' + (err.error?.detail || err.message || JSON.stringify(err)),
          timestamp: new Date().toLocaleTimeString()
        });
        this.Loading = false;
        this.scrollToBottom();
      }
    });
  }

  scrollToBottom() {
    try {
      setTimeout(() => {
        this.chatContainer.nativeElement.scrollTop = this.chatContainer.nativeElement.scrollHeight;
      }, 100);
    } catch (err) {
      console.warn('scroll error', err);
    }
  }

  // utilitaire pour retourner un tableau trié (top N) à afficher dans le template
  getTop(obj?: { [k: string]: number }, n = 5): Array<{ key: string; count: number }> {
    if (!obj) return [];
    return Object.entries(obj)
      .map(([k, v]) => ({ key: k, count: v }))
      .sort((a, b) => b.count - a.count)
      .slice(0, n);
  }

  // debug: voir le JSON complet (toggle)
  toggleShowStats() {
    this.showStats = !this.showStats;
  }
}
```

---

# 2) `chat.component.html` (parties importantes)

Ajoute un petit panneau **stats** au-dessus ou à côté du chat. J’ai laissé la structure de ton chat existante (boucles `ngFor`), et ajouté la zone statistiques.

```html
<div class="chat-wrapper">
  <div class="chat-header">
    <h2>Delphix Doc Assistant</h2>

    <!-- panneau résumé rapide -->
    <div class="rag-summary" *ngIf="stats">
      <div class="range">Période: {{ lastDateRange || '-' }}</div>
      <div class="meta">Total failed: {{ stats.total_failed }}</div>

      <div class="tops">
        <div class="top-block">
          <h4>Top Flows</h4>
          <ul>
            <li *ngFor="let f of getTop(stats.flows, 5)">
              {{ f.key }} ({{ f.count }})
            </li>
          </ul>
        </div>

        <div class="top-block">
          <h4>Top Tasks</h4>
          <ul>
            <li *ngFor="let t of getTop(stats.tasks, 5)">
              {{ t.key }} ({{ t.count }})
            </li>
          </ul>
        </div>

        <div class="top-block">
          <h4>Top Causes</h4>
          <ul>
            <li *ngFor="let c of getTop(stats.failures, 5)">
              {{ c.key }} ({{ c.count }})
            </li>
          </ul>
        </div>
      </div>

      <button (click)="toggleShowStats()">
        {{ showStats ? 'Cacher détails' : 'Montrer détails' }}
      </button>

      <pre *ngIf="showStats" class="stats-json">{{ stats | json }}</pre>
    </div>
  </div>

  <div id="chatContainer" #chatContainer class="chat-box">
    <div *ngFor="let msg of messages" [ngClass]="msg.role === 'user' ? 'message-bubble user' : 'message-bubble assistant'">
      <div class="bubble" [innerHTML]="msg.content"></div>
      <div class="timestamp" *ngIf="msg.timestamp">{{ msg.timestamp }}</div>
    </div>

    <div *ngIf="Loading" class="thinking">
      <div class="dot"></div><div class="dot"></div><div class="dot"></div>
    </div>
  </div>

  <div class="input-zone">
    <input [(ngModel)]="input" (keyup.enter)="send()" [disabled]="Loading" placeholder="Pose ta question sur les flows..." />
    <button (click)="send()" [disabled]="Loading || !input.trim()">→</button>
  </div>
</div>
```

Ajoute du CSS léger (ou réutilise le tien). L’idée : `.rag-summary`, `.top-block`, `.stats-json` pour une mise en forme simple.

---

# 3) Notes côté `ApiService` & Backend

1. **Format JSON attendu** (exemple):

```json
{
  "answer": "<p>Analyse...</p>",
  "stats": {
    "total_failed": 42,
    "flows": {"FLOW_A": 10, "FLOW_B": 5},
    "tasks": {"TASK_X": 12},
    "failures": {"SQL Timeout": 8}
  },
  "date_range": "2025-10-30 → 2025-10-31",
  "lang": "fr",
  "timestamp": "2025-10-31T12:34:56Z"
}
```

Ton backend (le `rag.py` que tu as) renvoie déjà cette structure si tu transformes les `Counter` en dicts (le JSON Python fera ça automatiquement). Attention juste à renvoyer `timestamp` en ISO.

2. **CORS** : n’oublie pas d’autoriser le front (origine) si ton backend est sur un autre hôte.

3. **ApiService** : si ta méthode `query()` renvoie `Observable<any>`, pas de souci. Sinon, adapte le type de retour pour `Observable<RagApiResponse>`.

Exemple minimal (Angular service) :

```ts
// api.service.ts (extrait)
query(sessionId: string, question: string, top_k = 8) {
  const url = `/api/rag/query`; // endpoint backend
  return this.http.post<RagApiResponse>(url, { sessionId, question, top_k });
}
```

---

# 4) Rappels / choses à vérifier

* Si ton backend stream (SSE / streaming response), l’adaptation est différente — le code ci-dessus suppose une réponse JSON finale.
* Si tu veux afficher la liste complète des jobs failed (les lignes détaillées du contexte), il faudrait renvoyer depuis ton backend un champ additionnel `failed_jobs: [{FLOW, TASK, JOB_ID, FAILURE, ACTION}, ...]` et l’afficher en *table* collapsible côté front.
* Les `Counter` Python reviennent comme objets `{ "FLOW_A": 10, "FLOW_B": 5 }` — la fonction `getTop` les trie côté front.

---

Si tu veux, je peux :

* **Générer la version HTML complète** (avec CSS) pour que tu colles directement dans ton projet,
* **Adapter `ApiService`** si tu me montres son code actuel,
* ou **ajouter l’affichage détaillé des `failed_jobs`** si tu modifies le backend pour renvoyer ce champ.

Tu veux que je te colle aussi une version CSS rapide pour `.rag-summary` et `.top-block` ?
