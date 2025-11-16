Super — j’ajoute **l’intégration Oracle (cx_Oracle)** côté backend et je fournis une **UI Angular 17** complète (remplaçant la petite UI React).
Tu as maintenant :

* Backend FastAPI capable de se connecter à Oracle, trouver les snapshots AWR, extraire AWR & top SQLs, et appeler l’advisor (sans RAG — utilise les docs locales).
* Frontend Angular 17 prêt à coller/coller (avec bouton **AI Tuning Advisor**) — inputs datetime-local, top N, etc.
* Tous les fichiers `docs/` (extraits de tuning).
* Requêtes SQL AWR exemplaires.
* Instructions pour lancer.

Tout est en texte brut — copie/colle chaque bloc dans le fichier correspondant.

---

## 🗂 Arborescence recommandée (rappel)

```
tuning-advisor/
├── backend/
│   ├── .env.sample
│   ├── requirements.txt
│   ├── main.py
│   ├── awr_oracle.py
│   ├── documentation_loader.py
│   ├── heuristic_doc_selector.py
│   ├── sql_extractors.py
│   ├── tuning_advisor_manual.py
│   └── docs/ (txt files)
└── frontend-angular/
    ├── package.json
    ├── angular.json
    ├── tsconfig.json
    └── src/
        └── app/
            ├── app.module.ts
            ├── api.service.ts
            ├── app.component.ts
            ├── app.component.html
            └── app.component.css
```

---

# BACKEND — fichiers

### `backend/requirements.txt`

```
fastapi
uvicorn[standard]
python-dotenv
openai
cx_Oracle
pydantic
```

---

### `backend/.env.sample`

```
# copy to .env and fill
OPENAI_API_KEY=sk-...
ALLOWED_ORIGINS=http://localhost:4200
ORACLE_USER=your_user
ORACLE_PASSWORD=your_password
ORACLE_DSN=host:1521/SERVICE_NAME
```

---

### `backend/awr_oracle.py`

```python
# backend/awr_oracle.py
import os
import cx_Oracle
from dotenv import load_dotenv

load_dotenv()

ORACLE_USER = os.getenv("ORACLE_USER")
ORACLE_PASSWORD = os.getenv("ORACLE_PASSWORD")
ORACLE_DSN = os.getenv("ORACLE_DSN")

def get_db_connection():
    """
    Return a cx_Oracle connection using env vars.
    Requires Oracle Instant Client and cx_Oracle configured.
    """
    if not (ORACLE_USER and ORACLE_PASSWORD and ORACLE_DSN):
        raise RuntimeError("Oracle credentials not set in environment")
    return cx_Oracle.connect(ORACLE_USER, ORACLE_PASSWORD, ORACLE_DSN, encoding="UTF-8")

def get_db_info():
    """Return (dbid, instance_number)."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT dbid FROM v$database")
    dbid_row = cur.fetchone()
    dbid = dbid_row[0] if dbid_row else None

    cur.execute("SELECT instance_number FROM v$instance")
    inst_row = cur.fetchone()
    instance_number = inst_row[0] if inst_row else 1

    cur.close()
    conn.close()
    return dbid, instance_number

def find_snapshots(start_date: str, end_date: str, dbid: int, instance_number: int):
    """
    Find begin/end snap_id covering the supplied timestamps.
    Date strings expected like 'YYYY-MM-DDTHH:MM' or 'YYYY-MM-DDTHH:MM:SS'.
    Returns (begin_snap, end_snap) or (None, None).
    """
    conn = get_db_connection()
    cur = conn.cursor()

    q_begin = """
    SELECT snap_id
    FROM dba_hist_snapshot
    WHERE dbid = :dbid
      AND instance_number = :inst
      AND begin_interval_time >= TO_TIMESTAMP(:start, 'YYYY-MM-DD\"T\"HH24:MI:SS')
    ORDER BY begin_interval_time
    """
    # normalize to include seconds if missing
    def ensure_seconds(s):
        return s if len(s.split(":")) == 3 else s + ":00"

    start_ts = ensure_seconds(start_date)
    end_ts = ensure_seconds(end_date)

    cur.execute(q_begin, dbid=dbid, inst=instance_number, start=start_ts)
    row = cur.fetchone()
    begin_snap = row[0] if row else None

    q_end = """
    SELECT snap_id
    FROM dba_hist_snapshot
    WHERE dbid = :dbid
      AND instance_number = :inst
      AND end_interval_time <= TO_TIMESTAMP(:end, 'YYYY-MM-DD\"T\"HH24:MI:SS')
    ORDER BY end_interval_time DESC
    """
    cur.execute(q_end, dbid=dbid, inst=instance_number, end=end_ts)
    row = cur.fetchone()
    end_snap = row[0] if row else None

    # fallback heuristics
    if begin_snap is None:
        q_before = """
        SELECT snap_id
        FROM (
          SELECT snap_id, end_interval_time
          FROM dba_hist_snapshot
          WHERE dbid = :dbid AND instance_number = :inst
            AND end_interval_time <= TO_TIMESTAMP(:end, 'YYYY-MM-DD\"T\"HH24:MI:SS')
          ORDER BY end_interval_time DESC
        ) WHERE ROWNUM = 1
        """
        cur.execute(q_before, dbid=dbid, inst=instance_number, end=end_ts)
        r = cur.fetchone()
        if r:
            begin_snap = r[0]

    if end_snap is None:
        q_after = """
        SELECT snap_id
        FROM (
          SELECT snap_id, begin_interval_time
          FROM dba_hist_snapshot
          WHERE dbid = :dbid AND instance_number = :inst
            AND begin_interval_time >= TO_TIMESTAMP(:start, 'YYYY-MM-DD\"T\"HH24:MI:SS')
          ORDER BY begin_interval_time
        ) WHERE ROWNUM = 1
        """
        cur.execute(q_after, dbid=dbid, inst=instance_number, start=start_ts)
        r = cur.fetchone()
        if r:
            end_snap = r[0]

    cur.close()
    conn.close()

    if not begin_snap or not end_snap:
        return None, None

    begin_snap = int(begin_snap)
    end_snap = int(end_snap)
    if begin_snap > end_snap:
        begin_snap, end_snap = end_snap, begin_snap
    return begin_snap, end_snap

AWR_QUERY = """
WITH snap AS (
     SELECT dbid,
            instance_number,
            &begin_snap AS bid,
            &end_snap AS eid
     FROM   dba_hist_snapshot
     WHERE  dbid = &dbid
       AND  instance_number = &instance_number
     FETCH FIRST 1 ROWS ONLY
),
awr AS (
     SELECT rownum line, output
     FROM   TABLE (
        dbms_workload_repository.awr_report_text(
           l_dbid       => (SELECT dbid FROM snap),
           l_inst_num   => (SELECT instance_number FROM snap),
           l_bid        => (SELECT bid FROM snap),
           l_eid        => (SELECT eid FROM snap),
           l_options    => 1+4+8
        )
     )
),
awr_sections AS (
    SELECT
        IGNORE NULLS OVER (ORDER BY line) section,
        output
    FROM awr
)
SELECT output
FROM awr_sections
WHERE regexp_like(section, :section, 'i')
"""

def get_awr_report(begin_snap: int, end_snap: int, dbid: int, inst: int, section_pattern: str = ".*"):
    conn = get_db_connection()
    cur = conn.cursor()
    sql = (AWR_QUERY
           .replace("&begin_snap", str(begin_snap))
           .replace("&end_snap", str(end_snap))
           .replace("&dbid", str(dbid))
           .replace("&instance_number", str(inst)))

    cur.execute(sql, section=section_pattern)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return "\n".join([r[0] for r in rows if r[0]])

def get_top_sqls_between_snaps(begin_snap: int, end_snap: int, dbid: int, inst: int, limit: int = 10):
    """
    Return list of dicts for top SQL by elapsed_time_delta between given snaps.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    q = """
    SELECT ss.sql_id,
           ss.parsing_schema_name,
           ss.module,
           SUM(ss.elapsed_time_delta) elapsed_time_delta,
           SUM(ss.buffer_gets_delta) buffer_gets_delta,
           SUM(ss.disk_reads_delta) disk_reads_delta,
           SUM(ss.executions_delta) executions_delta
    FROM dba_hist_sqlstat ss
    JOIN dba_hist_snapshot s ON ss.snap_id = s.snap_id AND ss.dbid = s.dbid
    WHERE ss.dbid = :dbid
      AND ss.instance_number = :inst
      AND ss.snap_id BETWEEN :b AND :e
    GROUP BY ss.sql_id, ss.parsing_schema_name, ss.module
    ORDER BY SUM(ss.elapsed_time_delta) DESC
    """
    cur.execute(q, dbid=dbid, inst=inst, b=begin_snap, e=end_snap)
    rows = cur.fetchmany(limit)
    result = []
    for r in rows:
        result.append({
            "sql_id": r[0],
            "parsing_schema": r[1],
            "module": r[2],
            "elapsed_time_delta": int(r[3] or 0),
            "buffer_gets_delta": int(r[4] or 0),
            "disk_reads_delta": int(r[5] or 0),
            "executions_delta": int(r[6] or 0)
        })
    cur.close()
    conn.close()
    return result

def get_sql_text(sql_id: str, dbid: int, inst: int, snap_id: int = None):
    conn = get_db_connection()
    cur = conn.cursor()
    q = "SELECT sql_text FROM dba_hist_sqltext WHERE sql_id = :sql_id AND dbid = :dbid"
    if snap_id:
        q += " AND snap_id = :snap"
        cur.execute(q, sql_id=sql_id, dbid=dbid, snap=snap_id)
    else:
        cur.execute(q, sql_id=sql_id, dbid=dbid)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    if not rows:
        return ""
    return "\n".join([r[0] for r in rows if r[0]])

def get_sql_plan(sql_id: str, dbid: int, inst: int, limit: int = 2000):
    conn = get_db_connection()
    cur = conn.cursor()
    q = """
    SELECT sql_id, plan_hash_value, plan_line
    FROM (
      SELECT sql_id, plan_hash_value, plan_line
      FROM dba_hist_sql_plan
      WHERE sql_id = :sql_id AND dbid = :dbid
      ORDER BY capture_time DESC
    ) WHERE ROWNUM <= :lim
    """
    cur.execute(q, sql_id=sql_id, dbid=dbid, lim=limit)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    if not rows:
        return ""
    return "\n".join([r[2] for r in rows if r[2]])
```

---

### `backend/documentation_loader.py`

```python
# backend/documentation_loader.py
def load_doc(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"[ERROR] Unable to load {path}: {e}"
```

---

### `backend/heuristic_doc_selector.py`

```python
# backend/heuristic_doc_selector.py
import os
from documentation_loader import load_doc

def select_relevant_docs(awr_global: str, awr_focus: str, sql_texts: dict, sql_plans: dict, docs_folder: str = "docs") -> str:
    ctx = []

    def add(name):
        full = os.path.join(docs_folder, name)
        if os.path.exists(full):
            ctx.append(load_doc(full))

    wait_text = (awr_focus or "").lower()

    if any(ev in wait_text for ev in ["sequential read", "scattered read", "direct path read", "db file sequential read"]):
        add("io_contention.txt")

    if any(ev in wait_text for ev in ["temp", "sort", "direct path read temp", "direct path write temp"]):
        add("temp_and_sorts.txt")

    if any(ev in wait_text for ev in ["latch", "buffer busy", "library cache", "enq:"]):
        add("latch_and_mutex.txt")

    if any(kw in wait_text for kw in ["cpu", "%cpu", "cpu usage"]):
        add("cpu_tuning.txt")

    for sql_id, plan in (sql_plans or {}).items():
        pl = (plan or "").lower()
        if "full table" in pl or "table access full" in pl:
            add("execution_plan_patterns.txt")
        if "cartesian" in pl or "cartesian join" in pl:
            add("join_issues.txt")
        if "px" in pl or "parallel" in pl:
            add("parallel_execution.txt")

    add("common_oracle_issues.txt")
    return "\n\n".join(ctx)
```

---

### `backend/sql_extractors.py`

```python
# backend/sql_extractors.py
def build_sql_block(sql_texts: dict, sql_plans: dict) -> str:
    blocks = []
    for sql_id in (sql_texts or {}).keys():
        text = sql_texts.get(sql_id, "")
        plan = sql_plans.get(sql_id, "")
        blocks.append(f"--- SQL ID: {sql_id} ---\nSQL TEXT:\n{text}\n\nPLAN:\n{plan}\n")
    return "\n\n".join(blocks)
```

---

### `backend/tuning_advisor_manual.py`

```python
# backend/tuning_advisor_manual.py
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

def build_prompt(awr_global: str, awr_focus: str, sql_blocks: str, docs_block: str) -> str:
    return f"""
You are a senior Oracle Database Performance Tuning advisor. Use ONLY the information provided.

INSTRUCTIONS:
- Compare the GLOBAL AWR interval and the FOCUS AWR interval.
- Identify anomalies that are present or amplified in the FOCUS interval.
- If no issues are found, explicitly reply exactly: "No issues found in the focus interval."
- Otherwise provide concise:
  - [SUMMARY]
  - [PROBLEMS]
  - [ROOT_CAUSES]
  - [RECOMMENDATIONS] (include SQL DDL examples if relevant)
  - [PRIORITY] (High/Medium/Low)
  - [EVIDENCE] (point to AWR excerpts or SQL IDs)
- Keep responses actionable and concise.
- Language: French (unless asked otherwise).

---- AWR GLOBAL ----
{awr_global}

---- AWR FOCUS ----
{awr_focus}

---- SQL (TEXTS & PLANS) ----
{sql_blocks}

---- DOCUMENTATION (selected extracts) ----
{docs_block}

End the message.
"""

def run_tuning(awr_global: str, awr_focus: str, sql_blocks: str, docs_block: str) -> str:
    prompt = build_prompt(awr_global, awr_focus, sql_blocks, docs_block)
    resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "You are an Oracle tuning expert."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.05,
        max_tokens=2500
    )
    try:
        return resp.choices[0].message.content
    except Exception:
        return str(resp)
```

---

### `backend/main.py`

```python
# backend/main.py
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from awr_oracle import get_db_info, find_snapshots, get_awr_report, get_top_sqls_between_snaps, get_sql_text, get_sql_plan
from heuristic_doc_selector import select_relevant_docs
from sql_extractors import build_sql_block
from tuning_advisor_manual import run_tuning

load_dotenv()

app = FastAPI(title="Oracle Tuning Advisor - No RAG (with Oracle)")

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:4200").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in ALLOWED_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class IntervalReq(BaseModel):
    global_start_date: str
    global_end_date: str
    focus_start_date: str
    focus_end_date: str
    section_pattern: str = ".*"
    top_n_sql: int = 5

@app.post("/analyze-intervals")
def analyze_intervals(req: IntervalReq):
    dbid, inst = get_db_info()

    g_begin, g_end = find_snapshots(req.global_start_date, req.global_end_date, dbid, inst)
    if not g_begin:
        return {"error": "No snapshots found in global interval."}

    f_begin, f_end = find_snapshots(req.focus_start_date, req.focus_end_date, dbid, inst)
    if not f_begin:
        return {"error": "No snapshots found in focus interval."}

    awr_global = get_awr_report(g_begin, g_end, dbid, inst, req.section_pattern)
    awr_focus  = get_awr_report(f_begin, f_end, dbid, inst, req.section_pattern)

    # get top SQLs for the focus interval
    top_sqls = get_top_sqls_between_snaps(f_begin, f_end, dbid, inst, limit=req.top_n_sql)

    # get SQL texts & plans
    sql_texts = {}
    sql_plans = {}
    for s in top_sqls:
        sid = s["sql_id"]
        sql_texts[sid] = get_sql_text(sid, dbid, inst)
        sql_plans[sid] = get_sql_plan(sid, dbid, inst)

    # select doc fragments
    docs_block = select_relevant_docs(awr_global, awr_focus, sql_texts, sql_plans)

    sql_block = build_sql_block(sql_texts, sql_plans)

    advisor_report = run_tuning(awr_global, awr_focus, sql_block, docs_block)

    return {
        "global_begin_snap": g_begin,
        "global_end_snap": g_end,
        "focus_begin_snap": f_begin,
        "focus_end_snap": f_end,
        "top_sqls": top_sqls,
        "advisor_report": advisor_report,
        "docs_sent": bool(docs_block)
    }
```

---

## backend/docs/ (tous les fichiers)

Crée le dossier `backend/docs/` puis crée ces fichiers (contenu résumé — remplace par ta doc complète si tu veux).

`common_oracle_issues.txt`

```
COMMON ORACLE ISSUES - Summary
- Check top waits and their trend in focus interval vs global
- Identify unexpected FULL TABLE SCANS
- Identify sudden spikes in DB CPU %
- Check temp tablespace usage and large sorts
- Check latch contention (library cache, row cache)
- Check parallel execution spikes
```

`io_contention.txt`

```
IO CONTENTION - Guidelines
- Identify top SQL by buffer_gets and disk_reads.
- Look for high 'db file sequential read' (random single-block) or 'db file scattered read' (multi-block).
- Remediations: Add indexes, partitioning, storage tuning, DB_FILE_MULTIBLOCK_READ_COUNT tuning.
Examples:
CREATE INDEX idx_col ON table(col);
```

`temp_and_sorts.txt`

```
TEMP & SORT Issues
- If many 'direct path read temp' or 'direct path write temp', queries spill to TEMP.
Remediations:
- Increase PGA_AGGREGATE_TARGET or use automatic PGA.
- Increase temp tablespace / add temp files.
- Rewrite GROUP BY / ORDER BY to use indexes when possible.
```

`latch_and_mutex.txt`

```
LATCH & MUTEX Issues
- Symptoms: buffer busy waits, library cache latch, row cache contention.
Remediations:
- Reduce hard parsing (use bind variables).
- Increase shared pool if library cache thrashing.
- Investigate hot blocks.
```

`cpu_tuning.txt`

```
HIGH CPU - Guidelines
- Check top SQL by CPU time.
- Detect expensive functions or PL/SQL loops.
Remediations:
- Rewrite heavy queries, add indexes, offload computations.
```

`parallel_execution.txt`

```
PARALLEL EXECUTION - Guidelines
- If many PX waits, check DOP and interconnect.
Remediations:
- Adjust PARALLEL_DEGREE_POLICY, use RESOURCE_MANAGER for caps.
```

`execution_plan_patterns.txt`

```
EXECUTION PLAN PATTERNS
- Full table scans might be OK on very selective operations; otherwise add index/partition.
- Cartesian joins indicate missing join predicates.
- Hash join vs nested loops: choose appropriate join order.
Examples and hints included.
```

`join_issues.txt`

```
JOIN ISSUES
- Check predicates to avoid cartesian products.
- Prefer joining on indexed columns or change driving table.
```

`awr_queries.sql`

```sql
-- Example AWR extraction snippets (requires privileges)
SELECT * FROM dba_hist_sysmetric_summary WHERE begin_interval_time BETWEEN :start AND :end;
SELECT * FROM dba_hist_system_event WHERE begin_interval_time BETWEEN :start AND :end;
SELECT * FROM dba_hist_active_sess_history WHERE sample_time BETWEEN :start AND :end;
SELECT * FROM dba_hist_sqlstat WHERE snap_id BETWEEN :b AND :e;
SELECT * FROM dba_hist_sqltext WHERE sql_id IN (SELECT DISTINCT sql_id FROM dba_hist_sqlstat WHERE snap_id BETWEEN :b AND :e);
SELECT * FROM dba_hist_sql_plan WHERE sql_id IN (SELECT DISTINCT sql_id FROM dba_hist_sqlstat WHERE snap_id BETWEEN :b AND :e);
```

---

# FRONTEND — Angular 17

> Les fichiers ci-dessous sont pour une application Angular 17 minimale.
> Assure-toi d’avoir `@angular/cli` compatible et Node >= 18.

### `frontend-angular/package.json`

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

### `frontend-angular/src/app/app.module.ts`

```ts
// src/app/app.module.ts
import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { HttpClientModule } from '@angular/common/http';
import { FormsModule } from '@angular/forms';

import { AppComponent } from './app.component';
import { ApiService } from './api.service';

@NgModule({
  declarations: [AppComponent],
  imports: [BrowserModule, HttpClientModule, FormsModule],
  providers: [ApiService],
  bootstrap: [AppComponent]
})
export class AppModule {}
```

---

### `frontend-angular/src/app/api.service.ts`

```ts
// src/app/api.service.ts
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

interface IntervalPayload {
  global_start_date: string;
  global_end_date: string;
  focus_start_date: string;
  focus_end_date: string;
  section_pattern?: string;
  top_n_sql?: number;
}

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private BASE = 'http://localhost:8000';

  constructor(private http: HttpClient) {}

  analyzeIntervals(payload: IntervalPayload): Observable<any> {
    return this.http.post(`${this.BASE}/analyze-intervals`, payload);
  }
}
```

---

### `frontend-angular/src/app/app.component.ts`

```ts
// src/app/app.component.ts
import { Component } from '@angular/core';
import { ApiService } from './api.service';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent {
  globalStart = '';
  globalEnd = '';
  focusStart = '';
  focusEnd = '';
  sectionPattern = '.*';
  topN = 5;

  advisorReport: string | null = null;
  topSqls: any[] = [];
  loading = false;

  constructor(private api: ApiService) {}

  runAdvisor() {
    this.advisorReport = null;
    this.topSqls = [];
    this.loading = true;

    this.api.analyzeIntervals({
      global_start_date: this.globalStart,
      global_end_date: this.globalEnd,
      focus_start_date: this.focusStart,
      focus_end_date: this.focusEnd,
      section_pattern: this.sectionPattern,
      top_n_sql: this.topN
    }).subscribe({
      next: (res) => {
        this.topSqls = res.top_sqls || [];
        this.advisorReport = res.advisor_report;
        this.loading = false;
      },
      error: (err) => {
        this.advisorReport = JSON.stringify(err);
        this.loading = false;
      }
    });
  }
}
```

---

### `frontend-angular/src/app/app.component.html`

```html
<!-- src/app/app.component.html -->
<div class="container">
  <h2>Oracle AWR Analyzer & Manual AI Tuning Advisor</h2>

  <section>
    <h4>Global interval (context)</h4>
    <label>Start: <input type="datetime-local" [(ngModel)]="globalStart"></label>
    <label style="margin-left:12px;">End: <input type="datetime-local" [(ngModel)]="globalEnd"></label>
  </section>

  <section style="margin-top:12px;">
    <h4>Focus interval (suspected)</h4>
    <label>Start: <input type="datetime-local" [(ngModel)]="focusStart"></label>
    <label style="margin-left:12px;">End: <input type="datetime-local" [(ngModel)]="focusEnd"></label>
  </section>

  <div style="margin-top:12px;">
    <label>Section pattern: <input type="text" [(ngModel)]="sectionPattern" placeholder="e.g. SQL ordered|Wait Event"></label>
    <label style="margin-left:12px;">Top N SQLs: <input type="number" [(ngModel)]="topN" min="1" max="50"></label>
  </div>

  <div style="margin-top:12px;">
    <button (click)="runAdvisor()" [disabled]="loading">AI Tuning Advisor</button>
    <span *ngIf="loading" style="margin-left:12px;">Working...</span>
  </div>

  <div *ngIf="topSqls && topSqls.length" style="margin-top:18px;">
    <h3>Top SQLs in Focus Interval</h3>
    <table style="width:100%; border-collapse:collapse;">
      <thead>
        <tr><th>SQL_ID</th><th>Elapsed delta</th><th>Buffer gets</th><th>Disk reads</th></tr>
      </thead>
      <tbody>
        <tr *ngFor="let s of topSqls">
          <td>{{ s.sql_id }}</td>
          <td>{{ s.elapsed_time_delta }}</td>
          <td>{{ s.buffer_gets_delta }}</td>
          <td>{{ s.disk_reads_delta }}</td>
        </tr>
      </tbody>
    </table>
  </div>

  <div *ngIf="advisorReport" style="margin-top:18px;">
    <h3>AI Tuning Advisor Report</h3>
    <pre>{{ advisorReport }}</pre>
  </div>
</div>
```

---

### `frontend-angular/src/app/app.component.css`

```css
/* src/app/app.component.css */
.container { max-width:1000px; margin:20px auto; padding:20px; border:1px solid #ddd; border-radius:8px; background:#fff; }
input, textarea { padding:6px; font-size:14px; }
button { padding:8px 12px; font-size:14px; }
h2, h3, h4 { margin:8px 0; }
table td, table th { padding:6px; text-align:left; border-bottom:1px solid #eee; }
pre { background:#f9f9f9; padding:12px; white-space:pre-wrap; }
```

---

# Instructions d’installation et lancement

## Backend (Oracle + FastAPI)

1. Installer Oracle Instant Client compatible et `cx_Oracle` (voir docs Oracle). Sur Linux, installer `oracle-instantclient-basic` et définir `LD_LIBRARY_PATH` si nécessaire.
2. Créer venv et installer dépendances:

```bash
cd tuning-advisor/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Copier `.env.sample` → `.env` et remplir `OPENAI_API_KEY`, `ORACLE_*`.
4. Lancer FastAPI:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Endpoints:

* `POST /analyze-intervals` avec JSON (voir frontend usage).

Payload example:

```json
{
  "global_start_date": "2025-11-10T00:00",
  "global_end_date": "2025-11-15T23:59",
  "focus_start_date": "2025-11-14T10:00",
  "focus_end_date": "2025-11-14T11:00",
  "section_pattern": "SQL ordered|Wait Event",
  "top_n_sql": 5
}
```

## Frontend (Angular)

1. Créer projet Angular ou coller `frontend-angular` dossier.
2. Installer deps et lancer:

```bash
cd tuning-advisor/frontend-angular
npm install
npm start
# ouvre http://localhost:4200
```

---

# Notes importantes / caveats

* L’accès à `DBA_HIST_*` et `DBMS_WORKLOAD_REPOSITORY.AWR_REPORT_TEXT` nécessite privilèges (DBA or select on related views).
* `cx_Oracle` nécessite Oracle Instant Client installé sur la machine d’exécution.
* OpenAI client (utilisé ici `OpenAI(api_key=...)`) suppose la version moderne — si tu utilises une autre version du package `openai`, adapte l’appel (je peux le faire pour toi si tu me dis la version).
* Le prompt force l’output exact `"No issues found in the focus interval."` si aucun problème.
* Si tu veux logs, auth, rate-limit, ou une UI différente — dis-le et je l’ajoute.

---

Si tu veux maintenant :

* que je **génère un Docker Compose** (backend + frontend) — dis “docker”,
* que je **fournisse un script de migration** pour remplacer les docs summarised par ta doc complète — dis “doc import”,
* ou que je **teste/valide** des exemples (ex: payload sample remplis) — dis “exemples”.

Je peux aussi fournir une **version du backend sans OpenAI** pour tests locaux (mock). Quelle suite ?
