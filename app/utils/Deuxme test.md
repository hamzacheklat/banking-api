Super — je te fournis **le projet complet (backend FastAPI + frontend Angular)**, prêt à coller. J’ai organisé chaque fichier, avec code concret pour :

* connexion Oracle **dynamique** (DSN/username/password envoyés depuis le frontend)
* extraction **réelle** des métriques AWR (SQL / Wait / Sessions) depuis `DBA_HIST_*` & `DBA_HIST_ACTIVE_SESS_HISTORY`
* génération de rapports **horaire** (découpe focus en heures)
* détection des anomalies + enrichissement des causes probables
* endpoints FastAPI POST/GET (expose `/awr/hourly-report`)
* frontend Angular qui envoie credentials, dates, affiche listes + graphiques (ng2-charts)

> ⚠️ Avant d’exécuter : installe `cx_Oracle` et configure Oracle Instant Client sur la machine backend, et installe les dépendances Angular (`npm install`).
> Aussi : vérifie que ton installation Oracle autorise les vues AWR/ASH (licence Diagnostic Pack).

Je fournis tout le code ; copie chaque fichier dans l’arborescence indiquée.

---

## Backend — arborescence

```
backend/
├─ app/
│  ├─ __init__.py
│  ├─ main.py
│  ├─ db_connection.py
│  ├─ utils.py
│  ├─ metrics.py
│  └─ services.py
├─ requirements.txt
```

### backend/requirements.txt

```txt
fastapi
uvicorn
cx_Oracle
pydantic
python-dateutil
```

---

### backend/app/**init**.py

```python
# package marker
```

---

### backend/app/db_connection.py

```python
import cx_Oracle

def get_connection(dsn: str, username: str, password: str):
    """
    Retourne une connexion cx_Oracle avec les credentials passés.
    dsn: 'host:port/service_name' ou TNS string
    """
    try:
        # si dsn contient host:port/service -> makedsn
        if ":" in dsn and "/" in dsn:
            host, rest = dsn.split(":", 1)
            port, service = rest.split("/", 1)
            port = int(port)
            tns = cx_Oracle.makedsn(host, port, service_name=service)
            conn = cx_Oracle.connect(user=username, password=password, dsn=tns, encoding="UTF-8")
        else:
            # assume tns string / easy connect
            conn = cx_Oracle.connect(user=username, password=password, dsn=dsn, encoding="UTF-8")
        return conn
    except Exception as e:
        raise RuntimeError(f"Oracle connection failed: {e}")
```

---

### backend/app/utils.py

```python
from datetime import datetime, timedelta
from typing import List

def get_snap_ids(conn, dbid: int, inst: int, start_time: datetime, end_time: datetime) -> List[int]:
    """
    Retourne la liste des snap_id entre start_time (inclusive) et end_time (exclusive).
    """
    cur = conn.cursor()
    cur.execute("""
        SELECT snap_id
        FROM dba_hist_snapshot
        WHERE dbid = :dbid
          AND instance_number = :inst
          AND begin_interval_time >= :start_time
          AND begin_interval_time < :end_time
        ORDER BY snap_id
    """, {"dbid": dbid, "inst": inst, "start_time": start_time, "end_time": end_time})
    rows = [r[0] for r in cur.fetchall()]
    cur.close()
    return rows

def generate_hourly_intervals(start_time: datetime, end_time: datetime):
    intervals = []
    current = start_time
    while current < end_time:
        next_hour = current + timedelta(hours=1)
        intervals.append((current, min(next_hour, end_time)))
        current = next_hour
    return intervals
```

---

### backend/app/metrics.py

```python
import json
from collections import defaultdict
from typing import List
from cx_Oracle import Cursor

# ---- Fetchers (use real AWR tables) ----
def fetch_awr_sql(cursor: Cursor, dbid: int, inst: int, snaps: List[int]):
    """
    Agrège elapsed_time_delta (ou elapsed_time_total selon version) par sql_id sur la plage de snapshots.
    """
    sql_metrics = defaultdict(int)
    if not snaps:
        return sql_metrics
    # use BETWEEN min and max snap
    cur_from = min(snaps)
    cur_to = max(snaps)
    cursor.execute("""
        SELECT ss.sql_id, SUM(NVL(ss.elapsed_time_delta, ss.elapsed_time_total, 0)) AS elapsed
        FROM dba_hist_sqlstat ss
        WHERE ss.dbid = :dbid AND ss.instance_number = :inst
          AND ss.snap_id BETWEEN :from_snap AND :to_snap
        GROUP BY ss.sql_id
    """, {"dbid": dbid, "inst": inst, "from_snap": cur_from, "to_snap": cur_to})
    for sql_id, elapsed in cursor.fetchall():
        sql_metrics[sql_id] += int(elapsed or 0)
    return sql_metrics

def fetch_awr_waits(cursor: Cursor, dbid: int, inst: int, snaps: List[int]):
    wait_metrics = defaultdict(int)
    if not snaps:
        return wait_metrics
    cur_from = min(snaps)
    cur_to = max(snaps)
    cursor.execute("""
        SELECT event, SUM(NVL(time_waited_delta, 0)) AS time_waited
        FROM dba_hist_system_event
        WHERE dbid = :dbid AND instance_number = :inst
          AND snap_id BETWEEN :from_snap AND :to_snap
        GROUP BY event
    """, {"dbid": dbid, "inst": inst, "from_snap": cur_from, "to_snap": cur_to})
    for event, time_waited in cursor.fetchall():
        wait_metrics[event] += int(time_waited or 0)
    return wait_metrics

def fetch_awr_sessions(cursor: Cursor, dbid: int, inst: int, snaps: List[int]):
    """
    Utilise DBA_HIST_ACTIVE_SESS_HISTORY pour compter échantillons par session_id.
    """
    session_metrics = defaultdict(int)
    if not snaps:
        return session_metrics
    # sample_time approach: map snap ids to times could be expensive, but use snap range to catch samples in interval
    cur_from = min(snaps)
    cur_to = max(snaps)
    # Get begin/end times for range
    cursor.execute("""
        SELECT MIN(begin_interval_time), MAX(end_interval_time)
        FROM dba_hist_snapshot
        WHERE dbid = :dbid AND instance_number = :inst
          AND snap_id BETWEEN :from_snap AND :to_snap
    """, {"dbid": dbid, "inst": inst, "from_snap": cur_from, "to_snap": cur_to})
    row = cursor.fetchone()
    if not row or row[0] is None:
        return session_metrics
    begin_time, end_time = row
    cursor.execute("""
        SELECT session_id, SUM(NVL(cpu_time,0)) AS cpu_sum, COUNT(*) AS samples
        FROM dba_hist_active_sess_history ash
        WHERE ash.dbid = :dbid AND ash.instance_number = :inst
          AND ash.sample_time BETWEEN :begin_time AND :end_time
        GROUP BY session_id
    """, {"dbid": dbid, "inst": inst, "begin_time": begin_time, "end_time": end_time})
    for session_id, cpu_sum, samples in cursor.fetchall():
        # metric can be cpu_sum or samples; choose cpu_sum if present else samples
        val = int(cpu_sum or samples or 0)
        session_metrics[session_id] += val
    return session_metrics

# ---- Comparison / detection ----
def compare_metrics(focus_metrics: dict, global_metrics: dict, top_n: int = 3):
    result = []
    keys = set(focus_metrics.keys()).union(global_metrics.keys())
    for key in keys:
        focus_total = focus_metrics.get(key, 0)
        global_total = global_metrics.get(key, 0)
        # avoid division by zero: if global_total == 0 and focus_total >0 -> big delta -> set 9999 or 100%
        if global_total:
            delta_percent = ((focus_total - global_total) / global_total) * 100.0
        else:
            delta_percent = 9999.0 if focus_total > 0 else 0.0
        result.append({
            "key": str(key),
            "focus_total": int(focus_total),
            "global_total": int(global_total),
            "delta_percent": float(delta_percent)
        })
    result.sort(key=lambda x: x["delta_percent"], reverse=True)
    return result[:top_n]

def detect_problematic_metrics(conn, dbid: int, inst: int, focus_snaps: List[int], global_snaps: List[int], top_n: int = 3):
    """
    Retourne un JSON string contenant top problematic SQL / waits / sessions.
    """
    cur = conn.cursor()
    focus_sql = fetch_awr_sql(cur, dbid, inst, focus_snaps)
    global_sql = fetch_awr_sql(cur, dbid, inst, global_snaps)

    focus_wait = fetch_awr_waits(cur, dbid, inst, focus_snaps)
    global_wait = fetch_awr_waits(cur, dbid, inst, global_snaps)

    focus_sess = fetch_awr_sessions(cur, dbid, inst, focus_snaps)
    global_sess = fetch_awr_sessions(cur, dbid, inst, global_snaps)

    result = {
        "problematic_sql": compare_metrics(focus_sql, global_sql, top_n),
        "problematic_waits": compare_metrics(focus_wait, global_wait, top_n),
        "problematic_sessions": compare_metrics(focus_sess, global_sess, top_n)
    }
    cur.close()
    return json.dumps(result, ensure_ascii=False, indent=2)
```

---

### backend/app/services.py

```python
from datetime import datetime
import json
from typing import List
from .utils import get_snap_ids, generate_hourly_intervals
from .metrics import detect_problematic_metrics, fetch_awr_sql, fetch_awr_waits, fetch_awr_sessions
from cx_Oracle import Connection

def analyze_hourly_awr(conn: Connection, dbid: int, inst: int,
                       focus_start: datetime, focus_end: datetime,
                       global_start: datetime, global_end: datetime, top_n: int = 3):
    """
    Découpe la période focus en heures, pour chaque heure calcule top problematic metrics vs global
    """
    intervals = generate_hourly_intervals(focus_start, focus_end)
    reports = []

    # precompute global snaps once
    global_snaps = get_snap_ids(conn, dbid, inst, global_start, global_end)

    for start, end in intervals:
        focus_snaps = get_snap_ids(conn, dbid, inst, start, end)
        if not focus_snaps:
            # no data for this hour
            reports.append({
                "interval_start": start.isoformat(),
                "interval_end": end.isoformat(),
                "report": {"problematic_sql": [], "problematic_waits": [], "problematic_sessions": []}
            })
            continue

        report_json = detect_problematic_metrics(conn, dbid, inst, focus_snaps, global_snaps, top_n=top_n)
        report = json.loads(report_json)

        # enrich probable causes heuristically
        for s in report.get("problematic_sql", []):
            s["probable_cause"] = []
            # check plan change quickly by checking plan_hash_value count in history for that sql_id
            cur = conn.cursor()
            cur.execute("""
                SELECT COUNT(DISTINCT plan_hash_value)
                FROM dba_hist_sql_plan
                WHERE sql_id = :sql_id
            """, {"sql_id": s["key"]})
            row = cur.fetchone()
            try:
                if row and row[0] and row[0] > 1:
                    s["probable_cause"].append("Changement de plan d'exécution détecté")
            except Exception:
                pass
            if s["delta_percent"] > 100:
                s["probable_cause"].append("Elapsed_time élevé")
            if not s["probable_cause"]:
                s["probable_cause"].append("Non déterminé")
            cur.close()

        for w in report.get("problematic_waits", []):
            key = w["key"].lower()
            causes = []
            if "db file" in key or "io" in key:
                causes.append("Attente IO / disque")
            if "latch" in key:
                causes.append("Contention mémoire / latch")
            if "network" in key or "tcp" in key:
                causes.append("Latence réseau")
            if not causes:
                causes.append("Autre attente")
            w["probable_cause"] = causes

        for se in report.get("problematic_sessions", []):
            se["probable_cause"] = []
            if se["delta_percent"] > 100:
                se["probable_cause"].append("Session CPU / activité élevée")
            else:
                se["probable_cause"].append("Non déterminé")
            # try to attach top SQL for that session in the global interval (best-effort)
            cur = conn.cursor()
            try:
                cur.execute("""
                    SELECT ash.sql_id, SUM(NVL(ash.cpu_time,0)) AS cpu_sum
                    FROM dba_hist_active_sess_history ash
                    WHERE ash.session_id = :sid
                      AND ash.sample_time BETWEEN (
                          SELECT MIN(begin_interval_time) FROM dba_hist_snapshot WHERE dbid=:dbid AND instance_number=:inst AND snap_id=:from_snap
                      ) AND (
                          SELECT MAX(end_interval_time) FROM dba_hist_snapshot WHERE dbid=:dbid AND instance_number=:inst AND snap_id=:to_snap
                      )
                    GROUP BY ash.sql_id
                    ORDER BY cpu_sum DESC
                    FETCH FIRST 1 ROWS ONLY
                """, {"sid": se["key"], "dbid": dbid, "inst": inst, "from_snap": min(focus_snaps), "to_snap": max(focus_snaps)})
                r = cur.fetchone()
                if r and r[0]:
                    se["top_sql_for_session"] = r[0]
            except Exception:
                pass
            cur.close()

        reports.append({
            "interval_start": start.isoformat(),
            "interval_end": end.isoformat(),
            "report": report
        })

    return reports
```

---

### backend/app/main.py

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from .db_connection import get_connection
from .services import analyze_hourly_awr

app = FastAPI(title="Oracle AWR Analyzer")

class HourlyAwrRequest(BaseModel):
    dsn: str
    username: str
    password: str
    dbid: int
    inst: int
    focus_start: datetime
    focus_end: datetime
    global_start: datetime
    global_end: datetime
    top_n: Optional[int] = 3

@app.post("/awr/hourly-report")
def hourly_report(req: HourlyAwrRequest):
    try:
        conn = get_connection(req.dsn, req.username, req.password)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        reports = analyze_hourly_awr(
            conn,
            req.dbid,
            req.inst,
            req.focus_start,
            req.focus_end,
            req.global_start,
            req.global_end,
            top_n=req.top_n
        )
        conn.close()
        return reports
    except Exception as e:
        try:
            conn.close()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))
```

---

## Backend — instructions d’exécution

1. Installer Oracle Instant Client et `cx_Oracle` (consulte doc cx_Oracle).
2. Créer un environnement Python, installer `pip install -r requirements.txt`.
3. Lancer :

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Frontend Angular — arborescence

```
frontend/awr-analyzer-angular/
├─ package.json
├─ src/
│  ├─ main.ts
│  ├─ index.html
│  ├─ styles.css
│  └─ app/
│     ├─ app.module.ts
│     ├─ app.component.ts
│     └─ components/
│        └─ report/
│           ├─ report.component.ts
│           ├─ report.component.html
│           └─ report.component.css
│     └─ services/
│        └─ awr.service.ts
```

### frontend/package.json

```json
{
  "name": "awr-analyzer-angular",
  "version": "1.0.0",
  "private": true,
  "dependencies": {
    "@angular/animations": "~15.0.0",
    "@angular/common": "~15.0.0",
    "@angular/compiler": "~15.0.0",
    "@angular/core": "~15.0.0",
    "@angular/forms": "~15.0.0",
    "@angular/platform-browser": "~15.0.0",
    "@angular/platform-browser-dynamic": "~15.0.0",
    "rxjs": "~7.5.0",
    "tslib": "^2.3.0",
    "zone.js": "~0.12.0",
    "chart.js": "^4.3.0",
    "ng2-charts": "^4.1.1",
    "axios": "^1.4.0"
  },
  "devDependencies": {
    "@angular/cli": "~15.0.0",
    "typescript": "~4.8.4"
  },
  "scripts": {
    "start": "ng serve --open"
  }
}
```

---

### frontend/src/main.ts

```typescript
import { platformBrowserDynamic } from '@angular/platform-browser-dynamic';
import { AppModule } from './app/app.module';

platformBrowserDynamic().bootstrapModule(AppModule)
  .catch(err => console.error(err));
```

---

### frontend/src/index.html

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>AWR Analyzer</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
  </head>
  <body>
    <app-root></app-root>
  </body>
</html>
```

---

### frontend/src/styles.css

```css
body {
  font-family: Arial, Helvetica, sans-serif;
  margin: 20px;
}
.connection-box, .config-box {
  margin-bottom: 12px;
  padding: 8px;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  background: #fafafa;
}
label { display:inline-block; margin-right:10px; }
input { margin-left:6px; }
button { padding:6px 12px; background:#007bff; color:white; border-radius:4px; border:none; cursor:pointer;}
button:hover { background:#0056b3;}
.chart-container { max-width: 900px; margin-top: 20px; }
```

---

### frontend/src/app/app.module.ts

```typescript
import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { FormsModule } from '@angular/forms';
import { HttpClientModule } from '@angular/common/http';
import { NgChartsModule } from 'ng2-charts';

import { AppComponent } from './app.component';
import { ReportComponent } from './components/report/report.component';
import { AwrService } from './services/awr.service';

@NgModule({
  declarations: [
    AppComponent,
    ReportComponent
  ],
  imports: [
    BrowserModule,
    FormsModule,
    HttpClientModule,
    NgChartsModule
  ],
  providers: [AwrService],
  bootstrap: [AppComponent]
})
export class AppModule { }
```

---

### frontend/src/app/app.component.ts

```typescript
import { Component } from '@angular/core';

@Component({
  selector: 'app-root',
  template: `<app-report></app-report>`
})
export class AppComponent {}
```

---

### frontend/src/app/services/awr.service.ts

```typescript
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable()
export class AwrService {
  private apiUrl = 'http://localhost:8000';

  constructor(private http: HttpClient) {}

  postHourlyReport(body: any): Observable<any> {
    return this.http.post(`${this.apiUrl}/awr/hourly-report`, body);
  }
}
```

---

### frontend/src/app/components/report/report.component.ts

```typescript
import { Component } from '@angular/core';
import { AwrService } from '../../services/awr.service';
import { ChartConfiguration, ChartOptions } from 'chart.js';

@Component({
  selector: 'app-report',
  templateUrl: './report.component.html',
  styleUrls: ['./report.component.css']
})
export class ReportComponent {
  dsn = '';
  username = '';
  password = '';
  dbid = 0;
  inst = 1;
  focusStart = '';
  focusEnd = '';
  globalStart = '';
  globalEnd = '';
  topN = 3;

  reports: any[] = [];

  // charts
  sqlChartData: ChartConfiguration<'bar'>['data'] = { labels: [], datasets: [] };
  waitChartData: ChartConfiguration<'bar'>['data'] = { labels: [], datasets: [] };
  sessionChartData: ChartConfiguration<'bar'>['data'] = { labels: [], datasets: [] };
  chartOptions: ChartOptions<'bar'> = { responsive: true };

  constructor(private awrService: AwrService) {}

  fetchReport() {
    const body = {
      dsn: this.dsn,
      username: this.username,
      password: this.password,
      dbid: Number(this.dbid),
      inst: Number(this.inst),
      focus_start: this.focusStart,
      focus_end: this.focusEnd,
      global_start: this.globalStart,
      global_end: this.globalEnd,
      top_n: Number(this.topN)
    };
    this.awrService.postHourlyReport(body).subscribe((res: any[]) => {
      this.reports = res;
      this.updateCharts();
    }, err => {
      alert('Erreur: ' + (err?.error?.detail || err.message || err));
    });
  }

  updateCharts() {
    if (!this.reports || this.reports.length === 0) {
      this.sqlChartData = { labels: [], datasets: [] };
      this.waitChartData = { labels: [], datasets: [] };
      this.sessionChartData = { labels: [], datasets: [] };
      return;
    }

    const hours = this.reports.map(r => {
      const d = new Date(r.interval_start);
      return `${d.getHours()}h`;
    });

    // keys
    const sqlKeys = Array.from(new Set(this.reports.flatMap(r => (r.report?.problematic_sql || []).map(s => s.key))));
    const waitKeys = Array.from(new Set(this.reports.flatMap(r => (r.report?.problematic_waits || []).map(w => w.key))));
    const sessKeys = Array.from(new Set(this.reports.flatMap(r => (r.report?.problematic_sessions || []).map(s => s.key))));

    const randColor = () => '#' + Math.floor(Math.random()*16777215).toString(16);

    this.sqlChartData = {
      labels: hours,
      datasets: sqlKeys.map(k => ({
        label: k,
        data: this.reports.map(r => {
          const item = (r.report?.problematic_sql || []).find((x:any) => x.key === k);
          return item ? item.delta_percent : 0;
        }),
        backgroundColor: randColor()
      }))
    };

    this.waitChartData = {
      labels: hours,
      datasets: waitKeys.map(k => ({
        label: k,
        data: this.reports.map(r => {
          const item = (r.report?.problematic_waits || []).find((x:any) => x.key === k);
          return item ? item.delta_percent : 0;
        }),
        backgroundColor: randColor()
      }))
    };

    this.sessionChartData = {
      labels: hours,
      datasets: sessKeys.map(k => ({
        label: k,
        data: this.reports.map(r => {
          const item = (r.report?.problematic_sessions || []).find((x:any) => x.key === k);
          return item ? item.delta_percent : 0;
        }),
        backgroundColor: randColor()
      }))
    };
  }
}
```

---

### frontend/src/app/components/report/report.component.html

```html
<div>
  <h1>Oracle AWR Analyzer (multi-DB)</h1>

  <div class="connection-box">
    <h3>Connection Oracle</h3>
    <label>DSN (host:port/service) <input [(ngModel)]="dsn" /></label>
    <label>Username <input [(ngModel)]="username" /></label>
    <label>Password <input type="password" [(ngModel)]="password" /></label>
  </div>

  <div class="config-box">
    <label>DBID <input [(ngModel)]="dbid" type="number" /></label>
    <label>Instance <input [(ngModel)]="inst" type="number" /></label><br/>
    <label>Focus Start <input [(ngModel)]="focusStart" type="datetime-local" /></label>
    <label>Focus End <input [(ngModel)]="focusEnd" type="datetime-local" /></label><br/>
    <label>Global Start <input [(ngModel)]="globalStart" type="datetime-local" /></label>
    <label>Global End <input [(ngModel)]="globalEnd" type="datetime-local" /></label><br/>
    <label>Top N <input [(ngModel)]="topN" type="number" min="1" max="10" /></label>
    <button (click)="fetchReport()">Générer rapports horaires</button>
  </div>

  <div *ngIf="reports.length">
    <h2>Résumé horaire (delta %)</h2>

    <div class="chart-container">
      <h3>Top SQL</h3>
      <canvas baseChart
              [data]="sqlChartData"
              [options]="chartOptions"
              chartType="bar">
      </canvas>
    </div>

    <div class="chart-container">
      <h3>Top Wait Events</h3>
      <canvas baseChart
              [data]="waitChartData"
              [options]="chartOptions"
              chartType="bar">
      </canvas>
    </div>

    <div class="chart-container">
      <h3>Top Sessions</h3>
      <canvas baseChart
              [data]="sessionChartData"
              [options]="chartOptions"
              chartType="bar">
      </canvas>
    </div>

    <div *ngFor="let interval of reports">
      <h4>{{ interval.interval_start | date:'short' }} - {{ interval.interval_end | date:'short' }}</h4>

      <div><strong>SQL problématiques:</strong>
        <ul>
          <li *ngFor="let sql of interval.report.problematic_sql">
            {{ sql.key }} — delta: {{ sql.delta_percent | number:'1.0-1' }}% — causes: {{ sql.probable_cause.join(', ') }}
          </li>
        </ul>
      </div>

      <div><strong>Waits problématiques:</strong>
        <ul>
          <li *ngFor="let w of interval.report.problematic_waits">
            {{ w.key }} — delta: {{ w.delta_percent | number:'1.0-1' }}% — causes: {{ w.probable_cause.join(', ') }}
          </li>
        </ul>
      </div>

      <div><strong>Sessions problématiques:</strong>
        <ul>
          <li *ngFor="let s of interval.report.problematic_sessions">
            {{ s.key }} — delta: {{ s.delta_percent | number:'1.0-1' }}% — causes: {{ s.probable_cause.join(', ') }}
            <span *ngIf="s.top_sql_for_session"> — top SQL: {{ s.top_sql_for_session }}</span>
          </li>
        </ul>
      </div>
    </div>
  </div>
</div>
```

---

## Frontend — instructions d’exécution

1. `cd frontend/awr-analyzer-angular`
2. `npm install` (installe Angular CLI globally if needed)
3. `npm start` (or `ng serve`) — ouvre le navigateur sur `http://localhost:4200`

---

## Remarques pratiques & sécurité

* **Ne stocke pas** les credentials côté serveur ; dans cette version le frontend envoie dsn/username/password par POST.
* En production, utilise HTTPS + tokenisation (ou authentification centralisée) et ne log pas les passwords.
* Les requêtes sur AWR et ASH requièrent des droits (`SELECT_CATALOG_ROLE` ou rôle adapté) et la licence Diagnostic Pack.
* Si tu as plusieurs bases à scanner automatiquement, le frontend peut être adapté en liste de connexions, ou tu peux stocker des connexions chiffrées côté backend (avec précautions).

---

Si tu veux, je peux maintenant :

* a) te fournir un **script d’installation** (Dockerfile backend + docker-compose + Dockerfile frontend) ;
* b) ajouter des **filtres avancés** (filtrer out SQL internes, minimum threshold, etc.) ;
* c) produire des **prompts LLM** pour générer résumé narratif basé sur ces JSONs.

Que veux-tu en premier ?
