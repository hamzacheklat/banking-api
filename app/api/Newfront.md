C’est fait — j’ai ajouté **tous les fichiers frontend** dans la canvas (structure complète + contenu prêt à coller).

Tu peux maintenant :

* Ouvrir le document **Frontend-angular-structure** (à côté de la conversation) et copier-coller chaque fichier dans ton projet.
* Me demander d’ajouter des composants séparés, d’utiliser la syntaxe standalone, ou de préparer un `Dockerfile`/zip.

Que veux-tu que je fasse ensuite ? (par ex. `backend complet`, `docker`, `components`)


# Frontend Angular 17 - Full file set

> Tous les fichiers suivants sont prêts à copier/coller dans `frontend-angular/`.
> Structure utilisée : Angular 17 (standalone bootstrap), minimal sans CLI-specific schematics pour faciliter le copy & paste.

```
frontend-angular/
├── package.json
├── angular.json
├── tsconfig.json
├── tsconfig.app.json
├── src/
│   ├── index.html
│   ├── main.ts
│   ├── styles.css
│   └── app/
│       ├── app.component.ts
│       ├── app.component.html
│       ├── app.component.css
│       ├── api.service.ts
│       └── models.ts
```

---

## package.json

```json
{
  "name": "tuning-advisor-angular",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "start": "ng serve --host 0.0.0.0 --port 4200",
    "build": "ng build"
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
    "typescript": "~5.4.0"
  }
}
```

---

## angular.json

```json
{
  "version": 1,
  "projects": {
    "awr-ui": {
      "projectType": "application",
      "root": "",
      "sourceRoot": "src",
      "architect": {
        "build": {
          "builder": "@angular-devkit/build-angular:browser",
          "options": {
            "outputPath": "dist/awr-ui",
            "index": "src/index.html",
            "main": "src/main.ts",
            "tsConfig": "tsconfig.app.json",
            "assets": ["src/favicon.ico", "src/assets"],
            "styles": ["src/styles.css"],
            "scripts": []
          }
        },
        "serve": {
          "builder": "@angular-devkit/build-angular:dev-server",
          "options": { "browserTarget": "awr-ui:build" }
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
    "strict": true,
    "experimentalDecorators": true,
    "emitDecoratorMetadata": true,
    "skipLibCheck": true,
    "types": ["node"]
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

## src/index.html

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Oracle Tuning Advisor</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
  <app-root></app-root>
</body>
</html>
```

---

## src/main.ts

```ts
import { enableProdMode } from '@angular/core';
import { platformBrowserDynamic } from '@angular/platform-browser-dynamic';
import { AppModule } from './app/app.module';

platformBrowserDynamic().bootstrapModule(AppModule)
  .catch(err => console.error(err));
```

---

## src/styles.css

```css
:root{
  --bg: #f3f6fb;
  --card: #ffffff;
  --accent: #4a6ef2;
  --muted: #6b7280;
}

*{box-sizing:border-box}
body{margin:0;font-family:Inter, Roboto, Arial, sans-serif;background:var(--bg);color:#111}
.container{max-width:1000px;margin:24px auto;padding:20px}
.card{background:var(--card);padding:18px;border-radius:12px;box-shadow:0 6px 18px rgba(16,24,40,0.06);margin-bottom:16px}
.row{display:flex;gap:12px;flex-wrap:wrap}
.col{flex:1;min-width:200px}
label{display:block;font-size:13px;color:var(--muted);margin-bottom:6px}
input,select,button{width:100%;padding:10px;border-radius:8px;border:1px solid #e6e9ef;font-size:14px}
button{background:var(--accent);color:white;border:none;cursor:pointer}
button.ghost{background:transparent;color:var(--accent);border:1px solid rgba(74,110,242,0.15)}
.small{font-size:13px;color:var(--muted)}
pre{white-space:pre-wrap;background:#fafbff;padding:12px;border-radius:8px;border:1px solid #efefff}
@media (max-width:700px){.row{flex-direction:column}}
```

---

## src/app/app.module.ts

```ts
import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { FormsModule } from '@angular/forms';
import { HttpClientModule } from '@angular/common/http';

import { AppComponent } from './app.component';
import { ApiService } from './api.service';

@NgModule({
  declarations: [AppComponent],
  imports: [BrowserModule, FormsModule, HttpClientModule],
  providers: [ApiService],
  bootstrap: [AppComponent]
})
export class AppModule {}
```

---

## src/app/models.ts

```ts
export interface DBCreds {
  oracle_user: string;
  oracle_password: string;
  oracle_dsn: string;
}

export interface Snapshot {
  snap_id: number;
  begin_interval_time: string | null;
  end_interval_time: string | null;
  dbid?: number;
  instance_number?: number;
}
```

---

## src/app/api.service.ts

```ts
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { DBCreds, Snapshot } from './models';
import { Observable } from 'rxjs';

@Injectable({providedIn:'root'})
export class ApiService{
  private BASE = 'http://localhost:8000';
  constructor(private http: HttpClient){}

  fetchSnapshots(creds: DBCreds): Observable<{snapshots: Snapshot[]}>{
    return this.http.post<{snapshots: Snapshot[]}>(`${this.BASE}/snapshots`, {...creds});
  }

  analyzeIntervals(payload: any){
    return this.http.post(`${this.BASE}/analyze-intervals`, payload);
  }
}
```

---

## src/app/app.component.ts

```ts
import { Component } from '@angular/core';
import { ApiService } from './api.service';
import { DBCreds, Snapshot } from './models';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent{
  creds: DBCreds = {oracle_user:'', oracle_password:'', oracle_dsn:''};
  snapshots: Snapshot[] = [];
  loadingSnaps = false;
  error = '';

  // selected snap ids
  global_start = 0;
  global_end = 0;
  focus_start = 0;
  focus_end = 0;

  analyzing = false;
  result: any = null;

  constructor(private api: ApiService) {}

  loadSnapshots(){
    this.error = '';
    this.loadingSnaps = true;
    this.api.fetchSnapshots(this.creds).subscribe({
      next: res => { this.snapshots = res.snapshots || []; this.loadingSnaps = false; },
      error: err => { this.error = 'Unable to load snapshots: '+(err?.message||err); this.loadingSnaps = false; }
    });
  }

  runAnalysis(){
    this.error = '';
    if(!this.global_start || !this.global_end || !this.focus_start || !this.focus_end){
      this.error = 'Please select all 4 snapshots (global start/end and focus start/end).';
      return;
    }
    const payload = {
      ...this.creds,
      global_start_snap: Number(this.global_start),
      global_end_snap: Number(this.global_end),
      focus_start_snap: Number(this.focus_start),
      focus_end_snap: Number(this.focus_end),
      top_n_sql: 5
    };
    this.analyzing = true;
    this.api.analyzeIntervals(payload).subscribe({
      next: res => { this.result = res; this.analyzing = false; },
      error: err => { this.error = 'Analysis failed: '+(err?.message||err); this.analyzing = false; }
    });
  }
}
```

---

## src/app/app.component.html

```html
<div class="container">
  <div class="card">
    <h2>Oracle Tuning Advisor</h2>
    <p class="small">Connect to an Oracle instance and load AWR snapshots. Then choose global + focus intervals (by snap id) to run the advisor.</p>

    <div class="row">
      <div class="col">
        <label>Oracle User</label>
        <input [(ngModel)]="creds.oracle_user" placeholder="user">
      </div>
      <div class="col">
        <label>Oracle Password</label>
        <input type="password" [(ngModel)]="creds.oracle_password" placeholder="password">
      </div>
      <div class="col" style="min-width:260px;">
        <label>Oracle DSN</label>
        <input [(ngModel)]="creds.oracle_dsn" placeholder="host:1521/ORCL">
      </div>
    </div>

    <div style="margin-top:12px;display:flex;gap:8px;">
      <button (click)="loadSnapshots()" [disabled]="loadingSnaps">Load snapshots</button>
      <button class="ghost" (click)="snapshots=[]">Clear</button>
      <div style="flex:1"></div>
      <div class="small">Loaded: {{ snapshots.length }} snapshots</div>
    </div>

    <div *ngIf="loadingSnaps" style="margin-top:8px">Loading snapshots…</div>
    <div *ngIf="error" style="color:#b91c1c;margin-top:8px">{{ error }}</div>
  </div>

  <div *ngIf="snapshots.length" class="card">
    <h3>Select intervals</h3>
    <div class="row">
      <div class="col">
        <label>Global start snapshot</label>
        <select [(ngModel)]="global_start">
          <option [value]="0">-- select --</option>
          <option *ngFor="let s of snapshots" [value]="s.snap_id">{{s.snap_id}} — {{s.begin_interval_time}}</option>
        </select>
      </div>
      <div class="col">
        <label>Global end snapshot</label>
        <select [(ngModel)]="global_end">
          <option [value]="0">-- select --</option>
          <option *ngFor="let s of snapshots" [value]="s.snap_id">{{s.snap_id}} — {{s.end_interval_time}}</option>
        </select>
      </div>
    </div>

    <div class="row" style="margin-top:12px">
      <div class="col">
        <label>Focus start snapshot</label>
        <select [(ngModel)]="focus_start">
          <option [value]="0">-- select --</option>
          <option *ngFor="let s of snapshots" [value]="s.snap_id">{{s.snap_id}} — {{s.begin_interval_time}}</option>
        </select>
      </div>
      <div class="col">
        <label>Focus end snapshot</label>
        <select [(ngModel)]="focus_end">
          <option [value]="0">-- select --</option>
          <option *ngFor="let s of snapshots" [value]="s.snap_id">{{s.snap_id}} — {{s.end_interval_time}}</option>
        </select>
      </div>
    </div>

    <div style="margin-top:14px;display:flex;gap:8px;align-items:center">
      <button (click)="runAnalysis()" [disabled]="analyzing">Run AI Tuning Advisor</button>
      <div style="flex:1"></div>
      <div *ngIf="analyzing" class="small">Analyzing…</div>
    </div>
  </div>

  <div *ngIf="result" class="card">
    <h3>Result</h3>
    <pre>{{ result | json }}</pre>
  </div>
</div>
```

---

### Remarques
- Ces fichiers sont prêts pour un développement local. Tu peux coller directement dans `frontend-angular/`.
- Si tu veux, je peux aussi :
  - ajouter des composants séparés (SnapshotList, DbForm, ReportView) — dis "components",
  - générer une version avec Angular standalone components (plus moderne) — dis "standalone",
  - préparer un `Dockerfile` pour builder le front — dis "docker-front".



