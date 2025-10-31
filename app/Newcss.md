Super — je m’occupe de **mettre à jour ton front Angular** pour consommer correctement la nouvelle sortie du backend `answer_query_with_history()` (qui renvoie maintenant `answer`, `stats`, `date_range`, `table` (DataFrame) — qu’on recevra serialisée en JSON comme une *liste d’objets* — et les autres métadonnées).

Je te donne :

* le **`chat.component.ts`** complet (mis à jour),
* le **`chat.component.html`** complet (mis à jour),
* un **extrait `ApiService`** (méthode `query()` + endpoint export),
* quelques **notes backend** (comment sérialiser `DataFrame`),
* et 2 petites utilitaires front (affichage table + export CSV côté client).

Je pars du principe que ton backend renvoie `table` serialisée comme `df.to_dict(orient='records')`. Si tu préfères `table_html`, je l’indique aussi.

---

## 1) Rappel important — à ajouter côté backend

Avant tout : fais en sorte que ton `rag.py` renvoie la table sous forme sérialisable JSON, par exemple :

```python
# au moment de renvoyer la réponse HTTP (Flask/FastAPI/...) :
result = answer_query_with_history(...)
# Convert dataframe en liste de dicts
table_records = result["table"].to_dict(orient="records") if not result["table"].empty else []
# Optionnel : fournir aussi une version HTML (pratique pour afficher directement)
table_html = result["table"].to_html(index=False) if not result["table"].empty else ""

return {
  "answer": result["answer"],
  "stats": result["stats"],
  "date_range": result["date_range"],
  "timestamp": result["timestamp"],
  "table": table_records,
  "table_html": table_html
}
```

Côté API REST, renvoie `application/json`. Pour export Excel côté backend tu peux proposer un endpoint séparé qui renvoie un fichier excel (content-disposition).

---

## 2) `ApiService` (extrait)

Adapte ton service pour typer la réponse et ajouter un endpoint d’export si tu veux serveur-side Excel.

```ts
// api.service.ts (extrait)
import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

export interface RagApiResponse {
  answer: string;
  stats?: any;
  date_range?: string;
  lang?: string;
  timestamp?: string;
  table?: any[];       // liste d'objets = rows
  table_html?: string; // optionnel si backend l'envoie
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  constructor(private http: HttpClient) {}

  query(sessionId: string, question: string, top_k = 8): Observable<RagApiResponse> {
    return this.http.post<RagApiResponse>('/api/rag/query', { sessionId, question, top_k });
  }

  // optional: server-side export endpoint (returns blob)
  exportReport(format: 'xlsx' | 'csv' | 'pdf', payload: any) {
    return this.http.post(`/api/rag/export?format=${format}`, payload, {
      responseType: 'blob'
    });
  }
}
```

---

## 3) `chat.component.ts` (mis à jour)

Supporte : affichage réponse (HTML safe), stats, table (liste d’objets), export CSV client-side, affichage `table_html` si backend l’envoie.

```ts
// chat.component.ts
import { Component, ElementRef, ViewChild } from '@angular/core';
import { ApiService, RagApiResponse } from '../services/api.service';
import { marked } from 'marked';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';

@Component({
  selector: 'app-chat',
  templateUrl: './chat.component.html',
  styleUrls: ['./chat.component.css']
})
export class ChatComponent {
  @ViewChild('chatContainer') chatContainer!: ElementRef;
  sessionId = 'session-vanish';
  input = '';
  messages: Array<{ role: 'user' | 'assistant'; content: SafeHtml | string; timestamp?: string }> = [];
  Loading = false;

  // nouveaux états
  stats?: any;
  lastDateRange?: string;
  lastLang?: string;
  lastTimestamp?: string;

  // table
  tableRows: any[] = [];       // rows = array of objects
  tableColumns: string[] = []; // computed from keys
  tableHtml?: string;          // optional html representation from backend
  showTable = false;
  showStats = true;

  constructor(private api: ApiService, private sanitizer: DomSanitizer) {}

  async send() {
    if (!this.input.trim() || this.Loading) return;
    const question = this.input.trim();

    this.messages.push({ role: 'user', content: question });
    this.input = '';
    this.Loading = true;
    this.scrollToBottom();

    this.api.query(this.sessionId, question, 8).subscribe({
      next: async (res: RagApiResponse) => {
        // Markdown/HTML answer -> sanitize
        const rowHtml = await marked(res.answer || '');
        const html: SafeHtml = this.sanitizer.bypassSecurityTrustHtml(rowHtml);

        this.messages.push({
          role: 'assistant',
          content: html,
          timestamp: new Date(res.timestamp || new Date().toISOString()).toLocaleTimeString()
        });

        // stats + metadata
        this.stats = res.stats;
        this.lastDateRange = res.date_range;
        this.lastLang = res.lang;
        this.lastTimestamp = res.timestamp;

        // table : soit backend renvoie 'table' (records), soit 'table_html'
        if (res.table && Array.isArray(res.table) && res.table.length > 0) {
          this.tableRows = res.table;
          this.tableColumns = Object.keys(this.tableRows[0] || {});
          this.showTable = true;
          this.tableHtml = undefined;
        } else if (res.table_html) {
          this.tableHtml = res.table_html;
          this.tableRows = [];
          this.tableColumns = [];
          this.showTable = true;
        } else {
          this.tableRows = [];
          this.tableColumns = [];
          this.tableHtml = undefined;
          this.showTable = false;
        }

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

  getTop(obj?: { [k: string]: number }, n = 5): Array<{ key: string; count: number }> {
    if (!obj) return [];
    return Object.entries(obj)
      .map(([k, v]) => ({ key: k, count: v as number }))
      .sort((a, b) => b.count - a.count)
      .slice(0, n);
  }

  toggleShowStats() { this.showStats = !this.showStats; }
  toggleShowTable() { this.showTable = !this.showTable; }

  // ---------- Export CSV client-side (simple)
  downloadCsv() {
    if ((!this.tableRows || this.tableRows.length === 0) && !this.tableHtml) return;

    // if we have JS rows => build CSV
    if (this.tableRows && this.tableRows.length > 0) {
      const cols = this.tableColumns;
      const csvRows = [
        cols.join(','), // header
        ...this.tableRows.map(row => cols.map(c => this.csvEscape(row[c])).join(','))
      ].join('\n');

      this.downloadBlob(csvRows, `failed_jobs_${(this.lastDateRange || '').replace(/ /g, '_')}.csv`, 'text/csv');
      return;
    }

    // else if we only have html, let user copy or backend export
    const blob = new Blob([this.tableHtml || ''], { type: 'text/html' });
    this.downloadBlob(blob, `failed_jobs_${(this.lastDateRange || '').replace(/ /g, '_')}.html`, 'text/html');
  }

  csvEscape(value: any) {
    if (value === null || value === undefined) return '';
    const s = String(value).replace(/"/g, '""');
    return `"${s}"`;
  }

  downloadBlob(data: Blob | string, filename: string, mime: string) {
    const blob = (typeof data === 'string') ? new Blob([data], { type: mime }) : data;
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    window.URL.revokeObjectURL(url);
  }

  // optional: ask backend to build excel/pdf and return blob
  exportServerSide(format: 'xlsx' | 'pdf') {
    const payload = { sessionId: this.sessionId, question: '', date_range: this.lastDateRange }; // adjust as needed
    this.api.exportReport(format, payload).subscribe((blob: Blob) => {
      const ext = format === 'xlsx' ? 'xlsx' : 'pdf';
      this.downloadBlob(blob, `report_${(this.lastDateRange||'report')}.${ext}`, blob.type);
    });
  }
}
```

---

## 4) `chat.component.html` (mis à jour)

Affiche : réponse sanitizée, stats (top 5), table (HTML si présent ou tableau natif), boutons export CSV / request server export.

```html
<div class="chat-wrapper">
  <div class="chat-header">
    <h2>Delphix Doc Assistant</h2>

    <div class="rag-summary" *ngIf="stats">
      <div class="range">Période: {{ lastDateRange || '-' }}</div>
      <div class="meta">Total failed: {{ stats.total_failed }}</div>

      <div class="tops">
        <div class="top-block">
          <h4>Top Flows</h4>
          <ul>
            <li *ngFor="let f of getTop(stats.flows, 5)">{{ f.key }} ({{ f.count }})</li>
          </ul>
        </div>

        <div class="top-block">
          <h4>Top Causes</h4>
          <ul>
            <li *ngFor="let c of getTop(stats.failures, 5)">{{ c.key }} ({{ c.count }})</li>
          </ul>
        </div>

        <div class="top-block">
          <h4>Origines</h4>
          <ul>
            <li *ngFor="let o of getTop(stats.origins, 5)">{{ o.key }} ({{ o.count }})</li>
          </ul>
        </div>
      </div>

      <div class="summary-actions">
        <button (click)="toggleShowStats()">{{ showStats ? 'Cacher détails' : 'Montrer détails' }}</button>
        <button (click)="toggleShowTable()" [disabled]="!tableRows.length && !tableHtml">Afficher tableau</button>
        <button (click)="downloadCsv()" [disabled]="!tableRows.length && !tableHtml">Télécharger CSV / HTML</button>
        <button (click)="exportServerSide('xlsx')" [disabled]="!lastDateRange">Exporter Excel (serveur)</button>
      </div>

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

  <!-- Tableau détaillé -->
  <div class="table-panel" *ngIf="showTable">
    <h3>Tableau des jobs failed</h3>

    <!-- si backend renvoie table_html -->
    <div *ngIf="tableHtml" [innerHTML]="tableHtml"></div>

    <!-- sinon on génère un tableau natif -->
    <table *ngIf="!tableHtml && tableRows.length > 0" class="failed-table">
      <thead>
        <tr><th *ngFor="let c of tableColumns">{{ c }}</th></tr>
      </thead>
      <tbody>
        <tr *ngFor="let r of tableRows">
          <td *ngFor="let c of tableColumns">{{ r[c] }}</td>
        </tr>
      </tbody>
    </table>

  </div>

  <div class="input-zone">
    <input [(ngModel)]="input" (keyup.enter)="send()" [disabled]="Loading" placeholder="Pose ta question sur les flows..." />
    <button (click)="send()" [disabled]="Loading || !input.trim()">→</button>
  </div>
</div>
```

---

## 5) CSS rapide (optionnel)

Ajoute dans `chat.component.css` quelques règles simples :

```css
.rag-summary { border: 1px solid #e0e0e0; padding: 12px; margin-bottom: 8px; background:#fafafa; }
.top-block { display:inline-block; vertical-align:top; margin-right: 16px; }
.summary-actions button { margin-right:8px; }
.failed-table { width:100%; border-collapse: collapse; margin-top:8px; }
.failed-table th, .failed-table td { border:1px solid #ddd; padding:6px; font-size:13px; }
.table-panel { margin: 12px 0; padding: 8px; border-radius:6px; background:#fff; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
```

---

## 6) Remarques & suggestions

* **Serialisation** : backend → `table` = `df.to_dict(orient='records')` est la plus simple. `table_html` est pratique pour un rendu rapide côté front.
* **Exports** :

  * Client-side CSV fonctionne bien pour datasets raisonnables.
  * Pour Excel/PDF mieux faire côté serveur (pandas.to_excel / reportlab / weasyprint) et exposer `/api/rag/export`.
* **Performance** : si `table` est volumineuse (> 10k rows), renvoie un preview (top N) ou proposer pagination/back-end streaming.
* **Sécurité** : tu utilises `bypassSecurityTrustHtml` pour l’answer (markdown -> html). Assure-toi que le HTML provient d’une source contrôlée (le modèle). Si tu affiches `table_html` raw, pareil : sanitize côté backend ou afficher en iframe safe.
* **Streaming** : si le backend renvoie un stream pendant la génération, il faudra adapter le front pour traiter les chunks (EventSource / SSE ou web-socket). Ici j’ai pris la voie d’une réponse JSON finale.

---

Si tu veux, je peux :

* Générer le **endpoint backend** Flask/FastAPI minimal qui renvoie exactement ce JSON (avec `df.to_dict`) et l’endpoint `export`,
* Ajouter **pagination** côté front pour la table,
* Ou intégrer un export **Excel** côté client (via `xlsx` lib) — dis si tu veux que je t’ajoute ça maintenant.

Tu veux que je te fournisse aussi la route backend complète (FastAPI) pour renvoyer la réponse et l’export ?
