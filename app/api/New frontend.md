# Frontend — Angular 17 (Production-ready UI)

Contenu complet prêt-à-copier pour `frontend-angular/`.

> Instructions rapides :
>
> * Copier la structure ci-dessous dans `frontend-angular/`.
> * Ajuster `src/environments/environment.ts` pour pointer vers ton backend (par défaut `http://localhost:8000`).
> * `npm install` puis `npm run start` pour le dev, `npm run build` pour la prod.

---

## package.json

```json
{
  "name": "tuning-advisor-angular",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "start": "ng serve --host 0.0.0.0 --port 4200",
    "build": "ng build --configuration production",
    "test": "ng test",
    "lint": "ng lint"
  },
  "dependencies": {
    "@angular/animations": "^17.0.0",
    "@angular/common": "^17.0.0",
    "@angular/compiler": "^17.0.0",
    "@angular/core": "^17.0.0",
    "@angular/forms": "^17.0.0",
    "@angular/platform-browser": "^17.0.0",
    "@angular/platform-browser-dynamic": "^17.0.0",
    "@angular/router": "^17.0.0",
    "rxjs": "^7.8.0",
    "zone.js": "~0.13.0"
  },
  "devDependencies": {
    "@angular/cli": "^17.0.0",
    "@angular/compiler-cli": "^17.0.0",
    "typescript": "~5.4.0"
  }
}
```

---

## angular.json

```json
{
  "$schema": "./node_modules/@angular/cli/lib/config/schema.json",
  "version": 1,
  "projects": {
    "tuning-advisor": {
      "projectType": "application",
      "root": "",
      "sourceRoot": "src",
      "architect": {
        "build": {
          "builder": "@angular-devkit/build-angular:browser",
          "options": {
            "outputPath": "dist/tuning-advisor",
            "index": "src/index.html",
            "main": "src/main.ts",
            "polyfills": [],
            "tsConfig": "tsconfig.app.json",
            "assets": ["src/favicon.ico","src/assets"],
            "styles": ["src/styles.css"],
            "scripts": []
          },
          "configurations": {
            "production": {
              "optimization": true,
              "outputHashing": "all",
              "sourceMap": false,
              "namedChunks": false,
              "extractLicenses": true,
              "bundleDependencies": "all"
            }
          }
        },
        "serve": {
          "builder": "@angular-devkit/build-angular:dev-server",
          "options": { "browserTarget": "tuning-advisor:build" }
        }
      }
    }
  }
}
```

---

## tsconfig.json

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ES2022",
    "moduleResolution": "node",
    "experimentalDecorators": true,
    "emitDecoratorMetadata": true,
    "strict": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "noImplicitReturns": true
  }
}
```

---

## tsconfig.app.json

```json
{
  "extends": "./tsconfig.json",
  "compilerOptions": {
    "outDir": "./out-tsc/app",
    "types": []
  },
  "files": ["src/main.ts"],
  "include": ["src/**/*.ts"]
}
```

---

# src/ (frontend source)

### src/environments/environment.ts

```ts
export const environment = {
  production: false,
  backendUrl: 'http://localhost:8000'
};
```

### src/environments/environment.prod.ts

```ts
export const environment = {
  production: true,
  backendUrl: 'http://localhost:8000' // change to your prod backend URL
};
```

### src/main.ts

```ts
import { enableProdMode } from '@angular/core';
import { platformBrowserDynamic } from '@angular/platform-browser-dynamic';
import { AppModule } from './app/app.module';
import { environment } from './environments/environment';

if (environment.production) {
  enableProdMode();
}

platformBrowserDynamic().bootstrapModule(AppModule)
  .catch(err => console.error(err));
```

### src/index.html

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>Oracle Tuning Advisor</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="icon" type="image/x-icon" href="favicon.ico">
  </head>
  <body>
    <app-root></app-root>
  </body>
</html>
```

### src/styles.css

```css
:root{
  --bg:#f4f7fb;
  --card:#ffffff;
  --accent:#5b6ef6;
  --accent-2:#3a4adf;
  --muted:#6b7280;
}
*{box-sizing:border-box}
html,body{height:100%;}
body{
  margin:0;
  font-family: Inter, system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial;
  background: linear-gradient(180deg, var(--bg), #eef2ff);
  color:#0f172a;
}
.app-shell{max-width:1100px;margin:24px auto;padding:20px}
.header{display:flex;align-items:center;gap:16px;margin-bottom:20px}
.logo{width:52px;height:52px;border-radius:10px;background:linear-gradient(135deg,var(--accent),var(--accent-2));display:flex;align-items:center;justify-content:center;color:white;font-weight:700}
.title{font-size:20px;font-weight:700}
.grid{display:grid;grid-template-columns:1fr 380px;gap:20px}
@media(max-width:900px){.grid{grid-template-columns:1fr}}
.card{background:var(--card);border-radius:12px;padding:18px;box-shadow:0 6px 18px rgba(15,23,42,0.06)}
.form-row{display:flex;gap:12px}
.form-col{flex:1}
.input{width:100%;padding:10px;border-radius:8px;border:1px solid #e6eefb}
.btn{display:inline-block;padding:10px 14px;border-radius:10px;background:var(--accent);color:white;border:none;cursor:pointer}
.btn.secondary{background:transparent;color:var(--accent);border:1px solid rgba(91,110,246,0.12)}
.select{width:100%;padding:10px;border-radius:8px;border:1px solid #e6eefb;background:white}
.small{font-size:13px;color:var(--muted)}
.table{width:100%;border-collapse:collapse;margin-top:12px}
.table th, .table td{padding:8px;border-bottom:1px solid #f1f5ff;text-align:left}
.report{white-space:pre-wrap;background:#0f172a;color:#e6eefb;padding:12px;border-radius:8px}
.footer{margin-top:16px;font-size:13px;color:var(--muted)}
```

---

# src/app/

### src/app/app.module.ts

```ts
import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { HttpClientModule } from '@angular/common/http';
import { FormsModule } from '@angular/forms';

import { AppComponent } from './app.component';
import { ApiService } from './services/api.service';

@NgModule({
  declarations: [AppComponent],
  imports: [BrowserModule, HttpClientModule, FormsModule],
  providers: [ApiService],
  bootstrap: [AppComponent]
})
export class AppModule {}
```

### src/app/services/api.service.ts

```ts
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private base = environment.backendUrl;
  constructor(private http: HttpClient) {}

  fetchSnapshots(creds: { oracle_user: string; oracle_password: string; oracle_dsn: string; limit?: number }){
    return this.http.post(`${this.base}/snapshots`, creds);
  }

  analyzeIntervals(payload: any){
    return this.http.post(`${this.base}/analyze-intervals`, payload);
  }
}
```

### src/app/app.component.ts

```ts
import { Component } from '@angular/core';
import { ApiService } from './services/api.service';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent {
  // DB creds (user provides per session)
  oracle_user = '';
  oracle_password = '';
  oracle_dsn = '';
  snap_limit = 500;

  // UI state
  snapshots: Array<any> = [];
  loadingSnaps = false;
  loadError = '';

  global_start_snap: number | null = null;
  global_end_snap: number | null = null;
  focus_start_snap: number | null = null;
  focus_end_snap: number | null = null;

  top_n_sql = 5;

  analyzing = false;
  analysisResult: any = null;
  analysisError = '';

  constructor(private api: ApiService) {}

  loadSnapshots(){
    this.loadError = '';
    if(!this.oracle_user || !this.oracle_password || !this.oracle_dsn){
      this.loadError = 'Fill Oracle credentials first';
      return;
    }
    this.loadingSnaps = true;
    this.api.fetchSnapshots({oracle_user:this.oracle_user, oracle_password:this.oracle_password, oracle_dsn:this.oracle_dsn, limit:this.snap_limit}).subscribe({
      next: (res:any) => {
        this.snapshots = res.snapshots || [];
        this.loadingSnaps = false;
        // Prefill selectors with reasonable defaults (most recent few)
        if(this.snapshots.length){
          this.global_end_snap = this.snapshots[0].snap_id;
          this.global_start_snap = this.snapshots[Math.min( Math.floor(this.snapshots.length*0.6), this.snapshots.length-1)].snap_id;
          this.focus_start_snap = this.snapshots[Math.min(1, this.snapshots.length-1)].snap_id;
          this.focus_end_snap = this.snapshots[0].snap_id;
        }
      },
      error: (err:any) => {
        this.loadError = err?.message || 'Unable to load snapshots';
        this.loadingSnaps = false;
      }
    })
  }

  runAnalysis(){
    this.analysisError = '';
    this.analysisResult = null;
    if(!this.global_start_snap || !this.global_end_snap || !this.focus_start_snap || !this.focus_end_snap){
      this.analysisError = 'Select all snapshots before analysis';
      return;
    }

    const payload = {
      oracle_user: this.oracle_user,
      oracle_password: this.oracle_password,
      oracle_dsn: this.oracle_dsn,
      global_start_snap: Number(this.global_start_snap),
      global_end_snap: Number(this.global_end_snap),
      focus_start_snap: Number(this.focus_start_snap),
      focus_end_snap: Number(this.focus_end_snap),
      top_n_sql: Number(this.top_n_sql || 5)
    };

    this.analyzing = true;
    this.api.analyzeIntervals(payload).subscribe({
      next: (res:any) => {
        this.analysisResult = res;
        this.analyzing = false;
      },
      error: (err:any) => {
        this.analysisError = err?.message || 'Analysis failed';
        this.analyzing = false;
      }
    })
  }

  formatSnap(s:any){
    if(!s) return '';
    return `${s.snap_id} — ${s.begin_interval_time || s.end_interval_time}`;
  }
}
```

### src/app/app.component.html

```html
<div class="app-shell">
  <div class="header">
    <div class="logo">TA</div>
    <div>
      <div class="title">Oracle Tuning Advisor</div>
      <div class="small">AWR snapshots explorer & AI-assisted tuning (manual advisor)</div>
    </div>
  </div>

  <div class="grid">
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

      <ng-container *ngIf="snapshots.length">
        <div style="margin-top:14px">
          <div class="small">Show {{ snapshots.length }} snapshots (most recent first)</div>
        </div>
      </ng-container>
    </div>

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

  <div style="margin-top:18px">
    <div *ngIf="analysisResult" class="card">
      <h3>Result</h3>
      <div class="small">Top SQLs</div>
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

      <div style="margin-top:12px">
        <div class="small">Advisor Report</div>
        <pre class="report">{{ analysisResult.advisor_report }}</pre>
      </div>
      <div class="footer">Snapshots used: {{ analysisResult.focus_begin_snap }} → {{ analysisResult.focus_end_snap }}</div>
    </div>
  </div>
</div>
```

---

# Production notes & checklist

1. **CORS** — assure-toi que `ALLOWED_ORIGINS` dans le backend contient l’URL de prod (ex: `https://tuning.example.com`).
2. **Sécurité des credentials** — actuellement le front envoie user/password/dsn à chaque requête :

   * en prod, préfère utiliser un catalogue côté backend (login + encrypted saved connections) plutôt que l’envoi des creds brutes depuis le navigateur.
3. **TLS** — déployer le backend derrière un reverse-proxy (nginx) avec TLS et configurar CORS.
4. **Rate limiting & auth** — ajoute une couche d’auth (token JWT) si l’outil sera exposé publiquement.
5. **Build** : `npm ci && npm run build` -> servir `dist/tuning-advisor`.

---

Si tu veux, je peux maintenant :

* générer un `docker-compose` pour build+serve le frontend statique et le backend (avec Oracle XE mock) — réponds `docker`.
* ou créer une **version qui n’envoie pas les credentials depuis le front** (catalogue + login) — réponds `catalog`.
