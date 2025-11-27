Voici **le projet complet** (backend + frontend) prêt à coller.
J’ai rassemblé **tous** les fichiers nécessaires — backend FastAPI utilisant `oracledb`, et frontend Angular avec le composant *card* pour charger les snapshots, choisir start/end focus & global et lancer l’analyse.
Vérifie d’abord les dépendances et adapte les `host`, `ports` ou chemins si besoin.

---

## ➤ RÉPERTOIRE recommandé

```
project/
├─ backend/
│  ├─ app/
│  │  ├─ __init__.py
│  │  ├─ db_connection.py
│  │  ├─ utils.py
│  │  ├─ metrics.py
│  │  ├─ services.py
│  │  └─ main.py
│  └─ requirements.txt
└─ frontend/
   └─ awr-analyzer-angular/
      ├─ package.json
      └─ src/
         ├─ index.html
         ├─ main.ts
         ├─ styles.css
         └─ app/
            ├─ app.module.ts
            ├─ app.component.ts
            ├─ services/awr.service.ts
            └─ components/
               └─ report-card/
                  ├─ report-card.component.ts
                  ├─ report-card.component.html
                  └─ report-card.component.css
```

---

## BACKEND — `backend/requirements.txt`

```txt
fastapi
uvicorn
oracledb
pydantic
python-dateutil
```

---

### `backend/app/__init__.py`

```python
# package marker
```

---

### `backend/app/db_connection.py`

```python
import oracledb

def init_oracle_client_if_needed(lib_dir: str | None = None):
    """
    Optional init for thick mode. Call before any connection if needed.
    """
    try:
        if lib_dir:
            oracledb.init_oracle_client(lib_dir=lib_dir)
        else:
            # if environment already provides Instant Client, this is safe/no-op
            oracledb.init_oracle_client()
    except Exception:
        # ignore if already initialized or using thin mode
        pass

def get_connection(dsn: str, username: str, password: str):
    """
    Create and return an oracledb connection.
    dsn can be 'host:port/service' or a TNS string.
    """
    try:
        if ":" in dsn and "/" in dsn:
            # parse host:port/service
            host, rest = dsn.split(":", 1)
            port_str, service = rest.split("/", 1)
            port = int(port_str)
            tns = oracledb.makedsn(host, port, service_name=service)
            conn = oracledb.connect(user=username, password=password, dsn=tns)
        else:
            conn = oracledb.connect(user=username, password=password, dsn=dsn)
        return conn
    except Exception as e:
        raise RuntimeError(f"Oracle connection failed: {e}")
```

---

### `backend/app/utils.py`

```python
from datetime import datetime, timedelta
from typing import List

def get_snap_ids(conn, dbid: int, inst: int, start_time: datetime, end_time: datetime) -> List[int]:
    """
    Return snap_id list between start_time (inclusive) and end_time (inclusive).
    """
    cur = conn.cursor()
    cur.execute("""
        SELECT snap_id
        FROM dba_hist_snapshot
        WHERE dbid = :dbid
          AND instance_number = :inst
          AND begin_interval_time >= :start_time
          AND begin_interval_time <= :end_time
        ORDER BY begin_interval_time
    """, {"dbid": dbid, "inst": inst, "start_time": start_time, "end_time": end_time})
    rows = [int(r[0]) for r in cur.fetchall()]
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

### `backend/app/metrics.py`

```python
import json
from collections import defaultdict
from typing import List
from cx_Oracle import Cursor  # type: ignore

def fetch_awr_sql(cursor: Cursor, dbid: int, inst: int, snaps: List[int]):
    """
    Aggregate elapsed time per sql_id across provided snaps using DBA_HIST_SQLSTAT.
    """
    sql_metrics = defaultdict(int)
    if not snaps:
        return sql_metrics
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
    session_metrics = defaultdict(int)
    if not snaps:
        return session_metrics
    cur_from = min(snaps)
    cur_to = max(snaps)
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
        val = int(cpu_sum or samples or 0)
        session_metrics[session_id] += val
    return session_metrics

def compare_metrics(focus_metrics: dict, global_metrics: dict, top_n: int = 3):
    result = []
    keys = set(list(focus_metrics.keys()) + list(global_metrics.keys()))
    for key in keys:
        focus_total = focus_metrics.get(key, 0)
        global_total = global_metrics.get(key, 0)
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

### `backend/app/services.py`

```python
from datetime import datetime
import json
from typing import List
from .utils import get_snap_ids, generate_hourly_intervals
from .metrics import detect_problematic_metrics
from cx_Oracle import Connection  # type: ignore

def analyze_hourly_awr(conn: Connection, dbid: int, inst: int,
                       focus_start: datetime, focus_end: datetime,
                       global_start: datetime, global_end: datetime, top_n: int = 3):
    """
    Split focus into hourly intervals; use precomputed global snaps for comparison.
    """
    intervals = generate_hourly_intervals(focus_start, focus_end)
    reports = []
    global_snaps = get_snap_ids(conn, dbid, inst, global_start, global_end)

    for start, end in intervals:
        focus_snaps = get_snap_ids(conn, dbid, inst, start, end)
        if not focus_snaps:
            reports.append({
                "interval_start": start.isoformat(),
                "interval_end": end.isoformat(),
                "report": {"problematic_sql": [], "problematic_waits": [], "problematic_sessions": []}
            })
            continue

        report_json = detect_problematic_metrics(conn, dbid, inst, focus_snaps, global_snaps, top_n=top_n)
        report = json.loads(report_json)

        # Enrich causes (heuristics)
        cur = conn.cursor()
        for s in report.get("problematic_sql", []):
            s["probable_cause"] = []
            try:
                cur.execute("""
                    SELECT COUNT(DISTINCT plan_hash_value)
                    FROM dba_hist_sql_plan
                    WHERE sql_id = :sql_id
                """, {"sql_id": s["key"]})
                row = cur.fetchone()
                if row and row[0] and row[0] > 1:
                    s["probable_cause"].append("Changement de plan d'exécution détecté")
            except Exception:
                pass
            if s["delta_percent"] > 100:
                s["probable_cause"].append("Elapsed_time élevé")
            if not s["probable_cause"]:
                s["probable_cause"].append("Non déterminé")

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
            se["probable_cause"] = ["Session CPU élevée"] if se["delta_percent"] > 100 else ["Non déterminé"]
            # try to find top sql for that session in focus period
            try:
                cur.execute("""
                    SELECT ash.sql_id, SUM(NVL(ash.cpu_time,0)) AS cpu_sum
                    FROM dba_hist_active_sess_history ash
                    WHERE ash.session_id = :sid
                      AND ash.sample_time BETWEEN (
                        SELECT MIN(begin_interval_time) FROM dba_hist_snapshot WHERE snap_id BETWEEN :from_snap AND :to_snap
                      ) AND (
                        SELECT MAX(end_interval_time) FROM dba_hist_snapshot WHERE snap_id BETWEEN :from_snap AND :to_snap
                      )
                    GROUP BY ash.sql_id
                    ORDER BY cpu_sum DESC
                """, {"sid": se["key"], "from_snap": min(focus_snaps), "to_snap": max(focus_snaps)})
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

### `backend/app/main.py`

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from .db_connection import get_connection
from .services import analyze_hourly_awr
from .utils import get_snap_ids
from .metrics import detect_problematic_metrics
import json

app = FastAPI(title="Oracle AWR Analyzer")

class SnapsRequest(BaseModel):
    dsn: str
    username: str
    password: str
    dbid: int
    inst: int
    start_time: datetime
    end_time: datetime

@app.post("/awr/snaps")
def list_snaps(req: SnapsRequest):
    try:
        conn = get_connection(req.dsn, req.username, req.password)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Connection failed: {e}")

    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT snap_id, begin_interval_time, end_interval_time
            FROM dba_hist_snapshot
            WHERE dbid = :dbid
              AND instance_number = :inst
              AND begin_interval_time >= :start_time
              AND begin_interval_time <= :end_time
            ORDER BY begin_interval_time
        """, {"dbid": req.dbid, "inst": req.inst, "start_time": req.start_time, "end_time": req.end_time})
        rows = [{"snap_id": int(r[0]), "begin": r[1].isoformat() if r[1] else None, "end": r[2].isoformat() if r[2] else None} for r in cur.fetchall()]
        cur.close()
        conn.close()
        return {"snaps": rows}
    except Exception as e:
        try:
            conn.close()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))

class HourlySnapsRequest(BaseModel):
    dsn: str
    username: str
    password: str
    dbid: int
    inst: int
    focus_snaps: Optional[List[int]] = None
    global_snaps: Optional[List[int]] = None
    focus_start: Optional[datetime] = None
    focus_end: Optional[datetime] = None
    global_start: Optional[datetime] = None
    global_end: Optional[datetime] = None
    top_n: Optional[int] = 3

@app.post("/awr/hourly-report")
def hourly_report_snaps(req: HourlySnapsRequest):
    try:
        conn = get_connection(req.dsn, req.username, req.password)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        # determine global_snaps
        if req.global_snaps:
            global_snaps = req.global_snaps
        elif req.global_start and req.global_end:
            global_snaps = get_snap_ids(conn, req.dbid, req.inst, req.global_start, req.global_end)
        else:
            raise HTTPException(status_code=400, detail="Provide global_snaps or global_start/global_end")

        # if focus_snaps provided -> single-shot analysis
        if req.focus_snaps:
            report_json = detect_problematic_metrics(conn, req.dbid, req.inst, req.focus_snaps, global_snaps, top_n=req.top_n)
            report = json.loads(report_json)
            # enrich similar to services (quick heuristic)
            # call same enrichment as in services if desired - for concision we return raw report
            conn.close()
            return {"interval_start": None, "interval_end": None, "report": report}
        else:
            # hourly analysis using focus_start/focus_end
            if not (req.focus_start and req.focus_end):
                raise HTTPException(status_code=400, detail="Provide focus_snaps or focus_start/focus_end")
            reports = analyze_hourly_awr(conn, req.dbid, req.inst, req.focus_start, req.focus_end, req.global_start, req.global_end, top_n=req.top_n)
            conn.close()
            return reports
    except HTTPException:
        try:
            conn.close()
        except:
            pass
        raise
    except Exception as e:
        try:
            conn.close()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))
```

---

## FRONTEND — Angular

Install Angular & dependencies:

```bash
cd frontend/awr-analyzer-angular
npm install
npm install chart.js ng2-charts
```

---

### `frontend/awr-analyzer-angular/package.json`

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
    "ng2-charts": "^4.1.1"
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

### `frontend/awr-analyzer-angular/src/index.html`

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

### `frontend/awr-analyzer-angular/src/main.ts`

```typescript
import { platformBrowserDynamic } from '@angular/platform-browser-dynamic';
import { AppModule } from './app/app.module';

platformBrowserDynamic().bootstrapModule(AppModule)
  .catch(err => console.error(err));
```

---

### `frontend/awr-analyzer-angular/src/styles.css`

```css
body { font-family: Arial, Helvetica, sans-serif; margin: 20px; background: #f5f7fa; }
```

---

### `frontend/awr-analyzer-angular/src/app/app.module.ts`

```typescript
import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { FormsModule } from '@angular/forms';
import { HttpClientModule } from '@angular/common/http';
import { NgChartsModule } from 'ng2-charts';

import { AppComponent } from './app.component';
import { ReportCardComponent } from './components/report-card/report-card.component';
import { AwrService } from './services/awr.service';

@NgModule({
  declarations: [
    AppComponent,
    ReportCardComponent
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

### `frontend/awr-analyzer-angular/src/app/app.component.ts`

```typescript
import { Component } from '@angular/core';

@Component({
  selector: 'app-root',
  template: `<app-report-card></app-report-card>`
})
export class AppComponent {}
```

---

### `frontend/awr-analyzer-angular/src/app/services/awr.service.ts`

```typescript
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class AwrService {
  private apiUrl = 'http://localhost:8000';

  constructor(private http: HttpClient) {}

  listSnaps(body: any): Observable<any> {
    return this.http.post(`${this.apiUrl}/awr/snaps`, body);
  }

  postHourlyReport(body: any): Observable<any> {
    return this.http.post(`${this.apiUrl}/awr/hourly-report`, body);
  }
}
```

---

### `frontend/awr-analyzer-angular/src/app/components/report-card/report-card.component.ts`

```typescript
import { Component } from '@angular/core';
import { AwrService } from '../../services/awr.service';

interface SnapItem {
  snap_id: number;
  begin: string | null;
  end: string | null;
  label: string;
}

@Component({
  selector: 'app-report-card',
  templateUrl: './report-card.component.html',
  styleUrls: ['./report-card.component.css']
})
export class ReportCardComponent {
  dsn = '';
  username = '';
  password = '';
  dbid: number | null = null;
  inst: number | null = null;

  snapsStart = '';
  snapsEnd = '';
  snapsList: SnapItem[] = [];
  snapsCount = 0;

  globalStart: number | null = null;
  globalEnd: number | null = null;
  focusStart: number | null = null;
  focusEnd: number | null = null;

  loadingSnaps = false;
  loadingAnalyze = false;
  error: string | null = null;

  analysisResult: any = null;

  constructor(private awr: AwrService) {}

  loadSnaps() {
    this.error = null;
    if (!this.dsn || !this.username || !this.password || !this.dbid || !this.inst || !this.snapsStart || !this.snapsEnd) {
      this.error = 'Remplis DSN / user / password / dbid / inst / plage de dates.';
      return;
    }
    this.loadingSnaps = true;
    this.snapsList = [];
    const body = {
      dsn: this.dsn,
      username: this.username,
      password: this.password,
      dbid: Number(this.dbid),
      inst: Number(this.inst),
      start_time: this.snapsStart,
      end_time: this.snapsEnd
    };
    this.awr.listSnaps(body).subscribe({
      next: (res) => {
        const snaps = res?.snaps || [];
        this.snapsList = snaps.map((s: any) => {
          const begin = s.begin ?? null;
          const label = `${s.snap_id} — ${begin ? (new Date(begin)).toLocaleString() : 'no-time'}`;
          return { snap_id: Number(s.snap_id), begin, end: s.end ?? null, label };
        }).sort((a, b) => b.snap_id - a.snap_id);
        this.snapsCount = this.snapsList.length;
        if (this.snapsList.length) {
          this.globalStart = this.snapsList[this.snapsList.length - 1].snap_id;
          this.globalEnd = this.snapsList[0].snap_id;
          this.focusStart = this.snapsList[Math.max(1, this.snapsList.length - 2)].snap_id;
          this.focusEnd = this.snapsList[this.snapsList.length - 1].snap_id;
        }
        this.loadingSnaps = false;
      },
      error: (err) => {
        this.loadingSnaps = false;
        this.error = err?.error?.detail || err.message || 'Erreur lors du chargement des snapshots';
      }
    });
  }

  clearSnaps() {
    this.snapsList = [];
    this.snapsCount = 0;
    this.globalStart = this.globalEnd = this.focusStart = this.focusEnd = null;
  }

  runAnalysisUsingSnaps() {
    this.error = null;
    if (!this.globalStart || !this.globalEnd || !this.focusStart || !this.focusEnd) {
      this.error = 'Sélectionne global start/end et focus start/end.';
      return;
    }
    this.loadingAnalyze = true;
    const body = {
      dsn: this.dsn,
      username: this.username,
      password: this.password,
      dbid: Number(this.dbid),
      inst: Number(this.inst),
      global_snaps: [Number(this.globalStart), Number(this.globalEnd)],
      focus_snaps: [Number(this.focusStart), Number(this.focusEnd)],
      top_n: 3
    };
    this.awr.postHourlyReport(body).subscribe({
      next: (res) => {
        this.analysisResult = res;
        this.loadingAnalyze = false;
      },
      error: (err) => {
        this.loadingAnalyze = false;
        this.error = err?.error?.detail || err.message || 'Erreur analyse';
      }
    });
  }
}
```

---

### `frontend/awr-analyzer-angular/src/app/components/report-card/report-card.component.html`

```html
<div class="card">
  <h2>AWR analysis between focus and global interval</h2>

  <div class="row">
    <div class="col">
      <h3>Connection & Snapshots</h3>

      <label>DSN (host:port/service)
        <input [(ngModel)]="dsn" placeholder="host:1521/service" />
      </label>

      <label>Username
        <input [(ngModel)]="username" />
      </label>

      <label>Password
        <input type="password" [(ngModel)]="password" />
      </label>

      <label>DBID
        <input type="number" [(ngModel)]="dbid" />
      </label>

      <label>Instance
        <input type="number" [(ngModel)]="inst" />
      </label>

      <div class="snap-range">
        <label>Start (snap range)
          <input type="datetime-local" [(ngModel)]="snapsStart" />
        </label>
        <label>End (snap range)
          <input type="datetime-local" [(ngModel)]="snapsEnd" />
        </label>
      </div>

      <div class="actions">
        <button (click)="loadSnaps()" [disabled]="loadingSnaps">Load snapshots</button>
        <button (click)="clearSnaps()" type="button">Clear</button>
      </div>

      <p *ngIf="loadingSnaps" class="muted">Loading snapshots…</p>
      <p *ngIf="!loadingSnaps">Show {{ snapsCount }} snapshots (most recent first)</p>
    </div>

    <div class="col">
      <h3>Analyze</h3>

      <label>Global start
        <select [(ngModel)]="globalStart">
          <option [ngValue]="null">-- choose --</option>
          <option *ngFor="let s of snapsList" [ngValue]="s.snap_id">{{ s.label }}</option>
        </select>
      </label>

      <label>Global end
        <select [(ngModel)]="globalEnd">
          <option [ngValue]="null">-- choose --</option>
          <option *ngFor="let s of snapsList" [ngValue]="s.snap_id">{{ s.label }}</option>
        </select>
      </label>

      <label>Focus start
        <select [(ngModel)]="focusStart">
          <option [ngValue]="null">-- choose --</option>
          <option *ngFor="let s of snapsList" [ngValue]="s.snap_id">{{ s.label }}</option>
        </select>
      </label>

      <label>Focus end
        <select [(ngModel)]="focusEnd">
          <option [ngValue]="null">-- choose --</option>
          <option *ngFor="let s of snapsList" [ngValue]="s.snap_id">{{ s.label }}</option>
        </select>
      </label>

      <div class="actions">
        <button (click)="runAnalysisUsingSnaps()" [disabled]="loadingAnalyze">Run AI Tuning Advisor</button>
        <button (click)="clearSnaps()" type="button">Clear</button>
      </div>

      <p *ngIf="loadingAnalyze" class="muted">Running analysis…</p>
      <p *ngIf="error" class="error">{{ error }}</p>
    </div>
  </div>

  <div *ngIf="analysisResult" class="result">
    <h3>Result</h3>
    <pre>{{ analysisResult | json }}</pre>
  </div>
</div>
```

---

### `frontend/awr-analyzer-angular/src/app/components/report-card/report-card.component.css`

```css
.card {
  background: #fff;
  border-radius: 8px;
  padding: 18px;
  box-shadow: 0 2px 6px rgba(0,0,0,0.06);
  max-width: 1100px;
  margin: 10px auto;
  font-family: "Segoe UI", Roboto, Arial, sans-serif;
}

.row { display: flex; gap: 20px; }
.col { flex: 1; min-width: 320px; }

h2 { color: #16a085; margin-bottom: 12px; }
h3 { margin-top: 0; color: #333; }

label { display:block; margin: 8px 0; font-size: 14px; color:#333; }
input[type="text"], input[type="password"], input[type="number"], input[type="datetime-local"], select {
  width: 100%;
  padding: 8px 10px;
  margin-top: 6px;
  border: 1px solid #ddd;
  border-radius: 6px;
  box-sizing: border-box;
}

.snap-range { display:flex; gap:8px; }
.snap-range label { flex:1; }

.actions { margin-top: 12px; }
button {
  padding: 8px 14px;
  background: #2d9cdb;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  margin-right: 8px;
}
button[disabled] { opacity: 0.6; cursor: not-allowed; }

.muted { color: #777; font-size: 13px; }
.error { color: #c0392b; font-weight: 600; margin-top: 10px; }

.result { margin-top: 18px; background:#f7f9fb; padding: 12px; border-radius:6px; }
pre { max-height: 400px; overflow: auto; }
```

---

## LANCEMENT

**Backend**

1. Crée un venv Python.
2. `pip install -r backend/requirements.txt`
3. Si tu veux le mode thick, configure Instant Client et appelle `init_oracle_client_if_needed()` (optionnel).
4. Lancer :

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend**

1. `cd frontend/awr-analyzer-angular`
2. `npm install`
3. `npm start` (ou `ng serve`)

---

## Notes pratiques & sécurité

* En prod : utilise HTTPS, ne logge pas les passwords, et sécurise l’API (auth/token).
* Les requêtes aux vues AWR/ASH nécessitent privilèges et licence Diagnostic Pack.
* Pour grandes plages de snaps, la requête peut être lourde — surveille les temps d’exécution et ajoute paginations/timeouts si nécessaire.
* Si tu veux stocker des connexions présélectionnées (profiles), fais-le côté backend avec chiffrement.

---

Si tu veux je peux maintenant :

* fournir un **docker-compose** pour le backend (avec oracledb thick si tu fournis Instant Client);
* améliorer l’UI (timeline, multi-select range, preview des snaps sélectionnés);
* ajouter export CSV / intégration Prometheus.

Que veux-tu en suivant ?
