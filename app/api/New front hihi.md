Parfait ! On va adapter le **CSS et l’UI Angular** pour que toutes les sections et le résumé final envoyés par ton backend soient bien présentés, en **Markdown scrollable**, avec un style clair et pro. On prend en compte :

* `analysisResult.section_results` → chaque section avec son nom et son contenu Markdown.
* `analysisResult.final_summary` → résumé final global.
* `analysisResult.top_sqls` → tableau des Top SQLs.

Voici une version CSS + HTML Angular adaptée :

---

## `app.component.css` (adapté au backend)

```css
/* Global resets */
body, html {
  margin: 0;
  padding: 0;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  background: #f5f6fa;
  color: #333;
}

/* App Shell */
.app-shell {
  max-width: 1300px;
  margin: 0 auto;
  padding: 16px;
}

/* Header */
.header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
}

.logo {
  width: 48px;
  height: 48px;
  background: #4f46e5;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 1.5rem;
  border-radius: 50%;
}

.title {
  font-size: 1.5rem;
  font-weight: 600;
}

.small {
  font-size: 0.85rem;
  color: #555;
}

/* Grid */
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
  gap: 16px;
}

/* Card */
.card {
  background: #fff;
  padding: 16px;
  border-radius: 12px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.08);
  display: flex;
  flex-direction: column;
}

.card h3 {
  margin-top: 0;
  margin-bottom: 12px;
}

/* Form */
.form-row {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}

.form-col {
  flex: 1;
}

.input, .select {
  width: 100%;
  padding: 6px 10px;
  border-radius: 6px;
  border: 1px solid #ccc;
  font-size: 0.95rem;
}

.input:focus, .select:focus {
  outline: none;
  border-color: #4f46e5;
  box-shadow: 0 0 0 2px rgba(79,70,229,0.2);
}

/* Buttons */
.btn {
  background: #4f46e5;
  color: white;
  border: none;
  padding: 8px 14px;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  transition: background 0.2s;
}

.btn:hover {
  background: #4338ca;
}

.btn.secondary {
  background: #e0e0e0;
  color: #333;
}

.btn.secondary:hover {
  background: #c7c7c7;
}

/* Tables */
.table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 8px;
  font-size: 0.9rem;
}

.table th, .table td {
  border: 1px solid #ddd;
  padding: 6px 10px;
}

.table th {
  background: #f3f4f6;
}

/* Markdown Cards */
markdown {
  display: block;
  max-height: 400px;
  overflow-y: auto;
  padding: 12px;
  background: #fefefe;
  border-radius: 8px;
  border: 1px solid #ddd;
  font-size: 0.95rem;
  line-height: 1.5;
  white-space: pre-wrap;
}

/* Scrollbar for markdown */
markdown::-webkit-scrollbar {
  width: 8px;
}

markdown::-webkit-scrollbar-thumb {
  background: #bbb;
  border-radius: 4px;
}

markdown::-webkit-scrollbar-thumb:hover {
  background: #999;
}
```

---

## `app.component.html` (adapté au backend)

```html
<div class="app-shell">
  <div class="header">
    <div class="logo">TA</div>
    <div>
      <div class="title">Oracle Tuning Advisor</div>
      <div class="small">AWR snapshots explorer & AI-assisted tuning</div>
    </div>
  </div>

  <div class="grid">
    <!-- Connection & Snapshots -->
    <div class="card">
      <h3>Connection & Snapshots</h3>
      <div class="form-row">
        <div class="form-col">
          <input class="input" placeholder="Oracle user" [(ngModel)]="oracle_user">
        </div>
        <div class="form-col">
          <input class="input" type="password" placeholder="Password" [(ngModel)]="oracle_password">
        </div>
      </div>

      <div style="margin-top:10px">
        <input class="input" placeholder="DSN (host:1521/ORCL)" [(ngModel)]="oracle_dsn">
      </div>

      <div style="margin-top:12px" class="form-row">
        <button class="btn" (click)="loadSnapshots()">Load snapshots</button>
        <button class="btn secondary" (click)="snapshots = []">Clear</button>
      </div>

      <div *ngIf="loadingSnaps" style="margin-top:12px">Loading snapshots...</div>
      <div *ngIf="loadError" class="small" style="color:#b91c1c;margin-top:10px">{{ loadError }}</div>
    </div>

    <!-- Analysis -->
    <div class="card">
      <h3>Analyze</h3>

      <label class="small">Global start</label>
      <select class="select" [(ngModel)]="global_start_snap">
        <option [ngValue]="null">-- select --</option>
        <option *ngFor="let s of snapshots" [value]="s.snap_id">{{ s.snap_id }} — {{ s.begin_interval_time }}</option>
      </select>

      <label class="small" style="margin-top:6px">Global end</label>
      <select class="select" [(ngModel)]="global_end_snap">
        <option [ngValue]="null">-- select --</option>
        <option *ngFor="let s of snapshots" [value]="s.snap_id">{{ s.snap_id }} — {{ s.end_interval_time }}</option>
      </select>

      <label class="small" style="margin-top:6px">Focus start</label>
      <select class="select" [(ngModel)]="focus_start_snap">
        <option [ngValue]="null">-- select --</option>
        <option *ngFor="let s of snapshots" [value]="s.snap_id">{{ s.snap_id }} — {{ s.begin_interval_time }}</option>
      </select>

      <label class="small" style="margin-top:6px">Focus end</label>
      <select class="select" [(ngModel)]="focus_end_snap">
        <option [ngValue]="null">-- select --</option>
        <option *ngFor="let s of snapshots" [value]="s.snap_id">{{ s.snap_id }} — {{ s.end_interval_time }}</option>
      </select>

      <label class="small" style="margin-top:8px">Top N SQLs</label>
      <input class="input" type="number" min="1" max="50" [(ngModel)]="top_n_sql">

      <div style="margin-top:12px;display:flex;gap:10px">
        <button class="btn" style="flex:1" (click)="runAnalysis()">Run AI Tuning Advisor</button>
        <button class="btn secondary" style="flex:1" (click)="analysisResult = null; analysisError='';">Reset</button>
      </div>

      <div *ngIf="analyzing" style="margin-top:12px">Running analysis…</div>
      <div *ngIf="analysisError" class="small" style="color:#b91c1c;margin-top:8px">{{ analysisError }}</div>
    </div>
  </div>

  <!-- Results -->
  <div style="margin-top:18px">
    <div *ngIf="analysisResult" class="card">
      <h3>Top SQLs</h3>
      <table class="table">
        <thead>
          <tr><th>SQL_ID</th><th>Elapsed</th><th>Buffer gets</th><th>Disk reads</th></tr>
        </thead>
        <tbody>
          <tr *ngFor="let s of analysisResult.top_sqls">
            <td>{{ s.sql_id }}</td>
            <td>{{ s.elapsed_time_delta }}</td>
            <td>{{ s.buffer_gets_delta }}</td>
            <td>{{ s.disk_reads_delta }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div *ngIf="analysisResult?.final_summary" class="card" style="margin-top:20px">
      <h3>Final Summary</h3>
      <markdown [data]="analysisResult.final_summary"></markdown>
    </div>

    <div *ngIf="analysisResult?.section_results" class="card" style="margin-top:20px">
      <h3>Section Analysis</h3>
      <div *ngFor="let section of objectKeys(analysisResult.section_results)">
        <h4>{{ section }}</h4>
        <markdown [data]="analysisResult.section_results[section]"></markdown>
      </div>
    </div>
  </div>
</div>
```

---

✅ **Adaptations backend → frontend :**

1. Chaque **section** retournée par le backend est affichée dans sa propre carte Markdown.
2. Le **résumé final** global est rendu dans une carte Markdown séparée.
3. Les **Top SQLs** restent dans un tableau classique.
4. Scroll et style adaptés pour les rapports longs.

---

Si tu veux, je peux maintenant te fournir **une version dark mode complète**, avec couleurs sombres pour les cartes Markdown, les tableaux et l’UI entière, pour un rendu plus pro et lisible sur des rapports AWR très longs.

Veux‑tu que je fasse ça ?
<div class="app-shell">
  <div class="header">
    <div class="logo">TA</div>
    <div>
      <div class="title">Oracle Tuning Advisor</div>
      <div class="small">AWR snapshots explorer & AI-assisted tuning</div>
    </div>
  </div>

  <div class="grid">
    <!-- Connection & Snapshots -->
    <div class="card">
      <h3>Connection & Snapshots</h3>
      <div class="form-row">
        <div class="form-col">
          <input class="input" placeholder="Oracle user" [(ngModel)]="oracle_user">
        </div>
        <div class="form-col">
          <input class="input" type="password" placeholder="Password" [(ngModel)]="oracle_password">
        </div>
      </div>

      <div style="margin-top:10px">
        <input class="input" placeholder="DSN (host:1521/ORCL)" [(ngModel)]="oracle_dsn">
      </div>

      <div style="margin-top:12px" class="form-row">
        <button class="btn" (click)="loadSnapshots()">Load snapshots</button>
        <button class="btn secondary" (click)="snapshots = []">Clear</button>
      </div>

      <div *ngIf="loadingSnaps" style="margin-top:12px">Loading snapshots...</div>
      <div *ngIf="loadError" class="small" style="color:#b91c1c;margin-top:10px">{{ loadError }}</div>
    </div>

    <!-- Analysis -->
    <div class="card">
      <h3>Analyze</h3>

      <label class="small">Global start</label>
      <select class="select" [(ngModel)]="global_start_snap">
        <option [ngValue]="null">-- select --</option>
        <option *ngFor="let s of snapshots" [value]="s.snap_id">{{ s.snap_id }} — {{ s.begin_interval_time }}</option>
      </select>

      <label class="small" style="margin-top:6px">Global end</label>
      <select class="select" [(ngModel)]="global_end_snap">
        <option [ngValue]="null">-- select --</option>
        <option *ngFor="let s of snapshots" [value]="s.snap_id">{{ s.snap_id }} — {{ s.end_interval_time }}</option>
      </select>

      <label class="small" style="margin-top:6px">Focus start</label>
      <select class="select" [(ngModel)]="focus_start_snap">
        <option [ngValue]="null">-- select --</option>
        <option *ngFor="let s of snapshots" [value]="s.snap_id">{{ s.snap_id }} — {{ s.begin_interval_time }}</option>
      </select>

      <label class="small" style="margin-top:6px">Focus end</label>
      <select class="select" [(ngModel)]="focus_end_snap">
        <option [ngValue]="null">-- select --</option>
        <option *ngFor="let s of snapshots" [value]="s.snap_id">{{ s.snap_id }} — {{ s.end_interval_time }}</option>
      </select>

      <label class="small" style="margin-top:8px">Top N SQLs</label>
      <input class="input" type="number" min="1" max="50" [(ngModel)]="top_n_sql">

      <div style="margin-top:12px;display:flex;gap:10px">
        <button class="btn" style="flex:1" (click)="runAnalysis()">Run AI Tuning Advisor</button>
        <button class="btn secondary" style="flex:1" (click)="analysisResult = null; analysisError='';">Reset</button>
      </div>

      <div *ngIf="analyzing" style="margin-top:12px">Running analysis…</div>
      <div *ngIf="analysisError" class="small" style="color:#b91c1c;margin-top:8px">{{ analysisError }}</div>
    </div>
  </div>

  <!-- Results -->
  <div style="margin-top:18px">
    <div *ngIf="analysisResult?.final_summary" class="card">
      <h3>Final Summary</h3>
      <markdown [data]="analysisResult.final_summary"></markdown>
    </div>

    <div *ngIf="analysisResult?.section_results" class="card" style="margin-top:20px">
      <h3>Section Analysis</h3>
      <div *ngFor="let section of objectKeys(analysisResult.section_results)">
        <h4>{{ section }}</h4>
        <markdown [data]="analysisResult.section_results[section]"></markdown>
      </div>
    </div>
  </div>
</div>
