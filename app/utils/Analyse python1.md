Parfait ! Voici **une version complète backend + frontend**, prête à coller, qui utilise **les vraies tables AWR** pour extraire SQL / Wait / Sessions et comparer focus vs global, avec génération automatique de rapports horaires.

---

# **1️⃣ Backend FastAPI complet**

### **Structure**

```
backend/
├─ app/
│  ├─ __init__.py
│  ├─ main.py
│  ├─ db.py
│  ├─ utils.py
│  └─ metrics.py
├─ requirements.txt
```

---

### **requirements.txt**

```txt
fastapi
uvicorn
cx_Oracle
pydantic
python-dateutil
```

---

### **app/**init**.py**

```python
# fichier vide
```

---

### **app/db.py**

```python
import cx_Oracle

def get_db_connection():
    dsn = cx_Oracle.makedsn("host", 1521, service_name="orclpdb1")
    return cx_Oracle.connect(user="user", password="pass", dsn=dsn)
```

---

### **app/utils.py**

```python
from datetime import datetime, timedelta
from typing import List

def get_snap_ids(conn, dbid: int, inst: int, start_time: datetime, end_time: datetime) -> List[int]:
    """Récupère les snapshots entre start_time et end_time"""
    cur = conn.cursor()
    cur.execute("""
        SELECT snap_id
        FROM dba_hist_snapshot
        WHERE dbid = :dbid AND instance_number = :inst
          AND begin_interval_time BETWEEN :start AND :end
        ORDER BY snap_id
    """, {"dbid": dbid, "inst": inst, "start": start_time, "end": end_time})
    return [r[0] for r in cur.fetchall()]

def generate_hourly_intervals(start_time: datetime, end_time: datetime):
    """Découpe la période en intervalles horaires"""
    intervals = []
    current = start_time
    while current < end_time:
        next_hour = current + timedelta(hours=1)
        intervals.append((current, min(next_hour, end_time)))
        current = next_hour
    return intervals
```

---

### **app/metrics.py**

```python
import json
from collections import defaultdict
from typing import List
from cx_Oracle import Cursor

def fetch_awr_sql(cursor: Cursor, dbid: int, inst: int, snaps: List[int]):
    sql_metrics = defaultdict(int)
    for snap_id in snaps:
        cursor.execute("""
            SELECT sql_id, elapsed_time_total
            FROM dba_hist_sqlstat
            WHERE dbid = :dbid AND instance_number = :inst AND snap_id = :snap
        """, {"dbid": dbid, "inst": inst, "snap": snap_id})
        for sql_id, elapsed in cursor.fetchall():
            sql_metrics[sql_id] += elapsed
    return sql_metrics

def fetch_awr_waits(cursor: Cursor, dbid: int, inst: int, snaps: List[int]):
    wait_metrics = defaultdict(int)
    for snap_id in snaps:
        cursor.execute("""
            SELECT event, total_waits
            FROM dba_hist_system_event
            WHERE dbid = :dbid AND instance_number = :inst AND snap_id = :snap
        """, {"dbid": dbid, "inst": inst, "snap": snap_id})
        for event, total_waits in cursor.fetchall():
            wait_metrics[event] += total_waits
    return wait_metrics

def fetch_awr_sessions(cursor: Cursor, dbid: int, inst: int, snaps: List[int]):
    session_metrics = defaultdict(int)
    for snap_id in snaps:
        cursor.execute("""
            SELECT session_id, COUNT(*)
            FROM dba_hist_active_sess_history
            WHERE dbid = :dbid AND instance_number = :inst AND snap_id = :snap
            GROUP BY session_id
        """, {"dbid": dbid, "inst": inst, "snap": snap_id})
        for session_id, count in cursor.fetchall():
            session_metrics[session_id] += count
    return session_metrics

def compare_metrics(focus_metrics: dict, global_metrics: dict, top_n: int = 3):
    result = []
    keys = set(focus_metrics.keys()).union(global_metrics.keys())
    for key in keys:
        focus_total = focus_metrics.get(key, 0)
        global_total = global_metrics.get(key, 0)
        delta_percent = ((focus_total - global_total) / global_total * 100) if global_total else 100
        result.append({
            "key": key,
            "focus_total": focus_total,
            "global_total": global_total,
            "delta_percent": delta_percent
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
    return json.dumps(result, ensure_ascii=False, indent=2)

def enrich_with_cause(conn, problematic_report: dict):
    for sql in problematic_report.get("problematic_sql", []):
        sql["probable_cause"] = ["Changement de plan ou temps d’exécution élevé"] if sql["delta_percent"] > 100 else ["Non déterminé"]

    for wait in problematic_report.get("problematic_waits", []):
        if "db file" in wait["key"].lower() or "io" in wait["key"].lower():
            wait["probable_cause"] = ["Attente IO / disque"]
        elif "latch" in wait["key"].lower():
            wait["probable_cause"] = ["Contention mémoire / latch"]
        else:
            wait["probable_cause"] = ["Autre cause de wait"]

    for sess in problematic_report.get("problematic_sessions", []):
        sess["probable_cause"] = ["Session fortement augmentée"] if sess["delta_percent"] > 100 else ["Non déterminé"]

    return problematic_report
```

---

### **app/main.py**

```python
from fastapi import FastAPI
from datetime import datetime
import json

from app.db import get_db_connection
from app.metrics import detect_problematic_metrics, enrich_with_cause
from app.utils import get_snap_ids, generate_hourly_intervals

app = FastAPI(title="Oracle AWR Analyzer")

@app.get("/report/hourly")
def hourly_report(
    dbid: int,
    inst: int,
    focus_start: datetime,
    focus_end: datetime,
    global_start: datetime,
    global_end: datetime,
    top_n: int = 3
):
    conn = get_db_connection()
    intervals = generate_hourly_intervals(focus_start, focus_end)
    reports = []

    for start, end in intervals:
        focus_snaps = get_snap_ids(conn, dbid, inst, start, end)
        global_snaps = get_snap_ids(conn, dbid, inst, global_start, global_end)

        report_json = detect_problematic_metrics(conn, dbid, inst, focus_snaps, global_snaps, top_n)
        report = json.loads(report_json)
        reports.append({
            "interval_start": start,
            "interval_end": end,
            "report": enrich_with_cause(conn, report)
        })

    return reports

@app.get("/report/global")
def global_report(
    dbid: int,
    inst: int,
    global_start: datetime,
    global_end: datetime,
    top_n: int = 3
):
    conn = get_db_connection()
    snaps = get_snap_ids(conn, dbid, inst, global_start, global_end)
    report_json = detect_problematic_metrics(conn, dbid, inst, snaps, snaps, top_n)
    report = json.loads(report_json)
    return enrich_with_cause(conn, report)
```

---

# **2️⃣ Frontend Angular complet**

### **Structure**

```
frontend/awr-analyzer-angular/
├─ src/
│  ├─ app/
│  │  ├─ services/awr.service.ts
│  │  ├─ components/report/report.component.ts
│  │  ├─ components/report/report.component.html
│  │  ├─ components/report/report.component.css
│  │  └─ app.module.ts
│  └─ main.ts
├─ package.json
```

---

### **awr.service.ts**

```typescript
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class AwrService {
  private apiUrl = 'http://localhost:8000';

  constructor(private http: HttpClient) {}

  getHourlyReport(params: any): Observable<any> {
    return this.http.get(`${this.apiUrl}/report/hourly`, { params });
  }

  getGlobalReport(params: any): Observable<any> {
    return this.http.get(`${this.apiUrl}/report/global`, { params });
  }
}
```

---

### **report.component.ts**

```typescript
import { Component } from '@angular/core';
import { AwrService } from '../../services/awr.service';

@Component({
  selector: 'app-report',
  templateUrl: './report.component.html',
  styleUrls: ['./report.component.css']
})
export class ReportComponent {
  dbid = 1;
  inst = 1;
  focusStart = '';
  focusEnd = '';
  globalStart = '';
  globalEnd = '';
  reports: any[] = [];

  constructor(private awrService: AwrService) {}

  fetchReport() {
    const params = {
      dbid: this.dbid,
      inst: this.inst,
      focus_start: this.focusStart,
      focus_end: this.focusEnd,
      global_start: this.globalStart,
      global_end: this.globalEnd
    };
    this.awrService.getHourlyReport(params).subscribe(res => this.reports = res);
  }
}
```

---

### **report.component.html**

```html
<div>
  <h1>Oracle AWR Analyzer</h1>

  <div>
    <label>DBID: <input [(ngModel)]="dbid" type="number" /></label>
    <label>Instance: <input [(ngModel)]="inst" type="number" /></label>
    <label>Focus Start: <input [(ngModel)]="focusStart" type="datetime-local" /></label>
    <label>Focus End: <input [(ngModel)]="focusEnd" type="datetime-local" /></label>
    <label>Global Start: <input [(ngModel)]="globalStart" type="datetime-local" /></label>
    <label>Global End: <input [(ngModel)]="globalEnd" type="datetime-local" /></label>
    <button (click)="fetchReport()">Charger le rapport</button>
  </div>

  <div *ngFor="let interval of reports">
    <h3>{{interval.interval_start | date:'short'}} - {{interval.interval_end | date:'short'}}</h3>

    <h4>SQL problématiques</h4>
    <ul>
      <li *ngFor="let sql of interval.report.problematic_sql">
        {{ sql.key }} - Delta: {{ sql.delta_percent.toFixed(1) }}% - Causes: {{ sql.probable_cause.join(', ') }}
      </li>
    </ul>

    <h4>Wait Events problématiques</h4>
    <ul>
      <li *ngFor="let wait of interval.report.problematic_waits">
        {{ wait.key }} - Delta: {{ wait.delta_percent.toFixed(1) }}% - Causes: {{ wait.probable_cause.join(', ') }}
      </li>
    </ul>

    <h4>Sessions problématiques</h4>
    <ul>
      <li *ngFor="let sess of interval.report.problematic_sessions">
        {{ sess.key }} - Delta: {{ sess.delta_percent.toFixed(1) }}% - Causes: {{ sess.probable_cause.join(', ') }}
      </li>
    </ul>
  </div>
</div>
```

---

### **report.component.css**

```css
h1 { color: #2c3e50; margin-bottom: 20px; }
label { display: inline-block; margin-right: 15px; margin-bottom: 10px; }
input { margin-left: 5px; }
button {
  margin-top: 10px;
  padding: 5px 15px;
  background-color: #3498db;
  color: white;
  border: none;
  cursor: pointer;
  border-radius: 4px;
}
button:hover { background-color: #2980b9; }
ul { margin: 5px 0 15px 20px; }
h3, h4 { color: #34495e; }
```

---

### **app.module.ts**

```typescript
import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { FormsModule } from '@angular/forms';
import { HttpClientModule } from '@angular/common/http';

import { AppComponent } from './app.component';
import { ReportComponent } from './components/report/report.component';

@NgModule({
  declarations: [
    AppComponent,
    ReportComponent
  ],
  imports: [
    BrowserModule,
    FormsModule,
    HttpClientModule
  ],
  providers: [],
  bootstrap: [AppComponent]
})
export class AppModule { }
```

---

### **main.ts**

```typescript
import { platformBrowserDynamic } from '@angular/platform-browser-dynamic';
import { AppModule } from './app/app.module';

platformBrowserDynamic().bootstrapModule(AppModule)
  .catch(err => console.error(err));
```

---

✅ Avec cette version :

* **Toutes les fonctions Python récupèrent les vraies données AWR**
* **Top 3 SQL / Wait / Sessions par delta %**
* **Rapports horaires comparant focus vs global**
* **Frontend Angular complet avec CSS et affichage clair**

---

Si tu veux, je peux maintenant **ajouter des graphiques avec `ng2-charts`** pour visualiser les tendances par heure directement dans le frontend Angular, ce qui rendra l’analyse encore plus pratique pour un DBA.

Veux‑tu que je fasse ça ?
