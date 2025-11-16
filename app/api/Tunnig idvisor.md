Great — I built the **full manual AI Tuning Advisor** and converted everything to **English**.
Below you get the complete, ready-to-copy code for:

* Backend (FastAPI + Oracle AWR + RAG/Chroma + OpenAI + Manual AI Tuning Advisor)
* Frontend (Angular 17) with a button **“AI Tuning Advisor”**
* CORS enabled for local dev
* Uses your Chroma indexing code (included)
* Prompt explicitly returns **"No issues found in the focus interval."** when nothing is detected

Follow the README steps at the bottom to run locally. Paste files into your project.

---

# ✅ Backend — Python / FastAPI

## Folder structure (recommended)

```
backend/
 ├── main.py
 ├── awr_oracle.py
 ├── rag_chroma.py
 ├── tuning_advisor.py
 ├── index_rag_corpus_chroma.py
 ├── requirements.txt
 └── rag_corpus/   # put your .txt files here (the ones you already prepared)
```

---

## `requirements.txt`

```
fastapi
uvicorn[standard]
cx_Oracle
chromadb
openai
python-dotenv
pydantic
```

---

## `.env` (put in `backend/`)

```
OPENAI_API_KEY=sk-...
ORACLE_USER=your_user
ORACLE_PASSWORD=your_password
ORACLE_DSN=host:1521/SERVICE_NAME
CHROMA_PATH=./chroma_db
COLLECTION_NAME=oracle_rag_docs
ALLOWED_ORIGINS=http://localhost:4200
```

---

## `awr_oracle.py` — Oracle connection, snapshot discovery, AWR extraction, top-SQL extraction

```python
# backend/awr_oracle.py
import os
import cx_Oracle
from dotenv import load_dotenv

load_dotenv()

ORACLE_USER = os.getenv("ORACLE_USER", "system")
ORACLE_PASSWORD = os.getenv("ORACLE_PASSWORD", "oracle")
ORACLE_DSN = os.getenv("ORACLE_DSN", "localhost:1521/ORCLPDB1")

def get_db_connection():
    """Return a cx_Oracle connection using env vars."""
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


def find_snapshots(start_date, end_date, dbid, instance_number):
    """
    Find begin/end snap_id covering the supplied timestamps.
    Expect date strings in 'YYYY-MM-DDTHH:MM' or 'YYYY-MM-DDTHH:MM:SS'.
    Returns (begin_snap, end_snap) or (None, None) if none found.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    q_begin = """
    SELECT snap_id
    FROM dba_hist_snapshot
    WHERE dbid = :dbid
      AND instance_number = :inst
      AND begin_interval_time >= TO_TIMESTAMP(:start, 'YYYY-MM-DD"T"HH24:MI:SS')
    ORDER BY begin_interval_time
    """
    cur.execute(q_begin, dbid=dbid, inst=instance_number, start=start_date)
    row = cur.fetchone()
    begin_snap = row[0] if row else None

    q_end = """
    SELECT snap_id
    FROM dba_hist_snapshot
    WHERE dbid = :dbid
      AND instance_number = :inst
      AND end_interval_time <= TO_TIMESTAMP(:end, 'YYYY-MM-DD"T"HH24:MI:SS')
    ORDER BY end_interval_time DESC
    """
    cur.execute(q_end, dbid=dbid, inst=instance_number, end=end_date)
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
            AND end_interval_time <= TO_TIMESTAMP(:end, 'YYYY-MM-DD"T"HH24:MI:SS')
          ORDER BY end_interval_time DESC
        ) WHERE ROWNUM = 1
        """
        cur.execute(q_before, dbid=dbid, inst=instance_number, end=end_date)
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
            AND begin_interval_time >= TO_TIMESTAMP(:start, 'YYYY-MM-DD"T"HH24:MI:SS')
          ORDER BY begin_interval_time
        ) WHERE ROWNUM = 1
        """
        cur.execute(q_after, dbid=dbid, inst=instance_number, start=start_date)
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

def get_awr_report(begin_snap, end_snap, dbid, inst, section_pattern=".*"):
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
    return "\n".join([r[0] for r in rows if r[0] is not None])


# -------------------------
# Extract top SQL between snap range
# -------------------------
def get_top_sqls_between_snaps(begin_snap, end_snap, dbid, inst, limit=10):
    """
    Return list of dicts for top SQL by elapsed_time_delta between given snaps.
    Uses DBA_HIST_SQLSTAT to aggregate deltas.
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


def get_sql_text(sql_id, dbid, inst, snap_id=None):
    """
    Retrieve SQL text from DBA_HIST_SQLTEXT for a SQL_ID.
    Optionally limit to a snap_id if present.
    """
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
    # concatenate pieces
    return "\n".join([r[0] for r in rows if r[0]])

def get_sql_plan(sql_id, dbid, inst, snap_id=None, limit=2000):
    """
    Pull historic plan fragments (DBA_HIST_SQL_PLAN) for SQL_ID.
    Returns concatenated plan_text.
    """
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
    # simplest representation - join plan_line
    return "\n".join([r[2] for r in rows if r[2]])
```

---

## `rag_chroma.py` — Chroma client, RAG retrieval, LLM wrappers

```python
# backend/rag_chroma.py
import os
from dotenv import load_dotenv
import chromadb
from chromadb.utils import embedding_functions
from openai import OpenAI
from typing import List

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "oracle_rag_docs")

client = chromadb.PersistentClient(path=CHROMA_PATH)

embed_fn = embedding_functions.OpenAIEmbeddingFunction(
    api_key=OPENAI_API_KEY,
    model_name="text-embedding-3-large"
)

collection = client.get_or_create_collection(
    name=COLLECTION_NAME,
    embedding_function=embed_fn
)

client_llm = OpenAI(api_key=OPENAI_API_KEY)


def _retrieve_context(text: str, top_k: int = 5) -> List[str]:
    """Return top_k retrieved documents (strings)."""
    try:
        res = collection.query(query_texts=[text], n_results=top_k)
        docs = res.get("documents", [[]])
        return docs[0] if docs and len(docs) > 0 else []
    except Exception:
        return []


def compare_intervals_with_rag(awr_global: str, awr_focus: str, top_k: int = 5) -> str:
    """
    Comparative prompt: returns LLM string. If LLM determines no issue,
    it must say 'No issues found in the focus interval.' explicitly.
    """
    context_docs = _retrieve_context(awr_focus, top_k=top_k)
    rag_context = "\n\n".join(context_docs)

    prompt = f"""
You are an experienced Oracle DBA. Compare two AWR intervals and identify anomalies in the FOCUS interval.

[GLOBAL INTERVAL]
{awr_global}

[FOCUS INTERVAL]
{awr_focus}

[RAG KNOWLEDGE]
{rag_context}

Task:
1) Compare focus vs global.
2) Identify anomalies present or amplified in focus.
3) If no anomaly exists, explicitly reply: "No issues found in the focus interval."
4) Otherwise provide:
   - concise findings
   - probable root causes
   - prioritized remediation steps (quick wins first)
   - citations (AWR excerpts)

Response format:
---
[COMPARATIVE_ANALYSIS]
<...>

[FOCUS_ANOMALIES]
<...>

[ROOT_CAUSES]
<...>

[RECOMMENDATIONS]
<...>

[EVIDENCE]
<...>
---
"""
    resp = client_llm.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1
    )
    try:
        return resp.choices[0].message.content
    except Exception:
        return getattr(resp, "text", str(resp))


def enrich_with_rag_and_llm(prompt_body: str, top_k: int = 5) -> str:
    """
    Generic helper: augment prompt with RAG context from prompt_body and call LLM.
    """
    context = "\n\n".join(_retrieve_context(prompt_body, top_k))
    prompt = f"{prompt_body}\n\n[RAG CONTEXT]\n{context}"
    resp = client_llm.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.15
    )
    try:
        return resp.choices[0].message.content
    except Exception:
        return getattr(resp, "text", str(resp))
```

---

## `tuning_advisor.py` — manual AI tuning advisor logic

```python
# backend/tuning_advisor.py
from awr_oracle import (
    get_db_info,
    find_snapshots,
    get_awr_report,
    get_top_sqls_between_snaps,
    get_sql_text,
    get_sql_plan
)
from rag_chroma import enrich_with_rag_and_llm

def build_advisor_prompt(awr_global, awr_focus, top_sqls, sql_texts_and_plans):
    """
    Construct a well-structured prompt for the LLM tuning advisor.
    Will ask LLM to explicitly say "No issues found in the focus interval." if none found.
    """
    top_sql_lines = []
    for s in top_sqls:
        top_sql_lines.append(
            f"SQL_ID: {s['sql_id']}, elapsed_delta: {s['elapsed_time_delta']}, buffer_gets_delta: {s['buffer_gets_delta']}, disk_reads_delta: {s['disk_reads_delta']}, executions_delta: {s['executions_delta']}"
        )
    top_sql_block = "\n".join(top_sql_lines)

    sql_blocks = []
    for sid, data in sql_texts_and_plans.items():
        sql_blocks.append(f"--- SQL_ID: {sid} ---\nSQL_TEXT:\n{data.get('text','')[:3000]}\n\nPLAN:\n{data.get('plan','')[:4000]}\n")
    sql_block = "\n\n".join(sql_blocks)

    prompt = f"""
You are an Oracle tuning advisor (senior DBA). Analyze the following information and produce a prioritized tuning plan.

[GLOBAL AWR CONTEXT]
{awr_global}

[FOCUS AWR CONTEXT]
{awr_focus}

[TOP SQLS IN FOCUS INTERVAL]
{top_sql_block}

[SQL TEXTS AND PLANS]
{sql_block}

Task:
1) Analyze differences between focus and global intervals.
2) For each top SQL, identify if it is problematic (explain why).
3) If no significant problems are found in the focus interval, explicitly state: "No issues found in the focus interval."
4) Otherwise, provide:
   - short summary of problem(s)
   - probable root causes
   - actionable recommendations (index DDL, SQL rewrites, quick config changes)
   - priority (High/Medium/Low)
   - estimated impact if possible

Format:
---
[SUMMARY]
[PROBLEMS]
[ROOT_CAUSES]
[RECOMMENDATIONS]
[PRIORITY]
[EVIDENCE]
---
"""
    return prompt


def tuning_advisor_manual(global_awr, focus_awr, dbid, inst, f_begin, f_end, top_n=5):
    """
    Manual advisor called from FastAPI: uses the focus interval to get top SQLs, their texts and plans,
    then constructs a prompt and passes it to LLM augmented by RAG.
    """
    top_sqls = get_top_sqls_between_snaps(f_begin, f_end, dbid, inst, limit=top_n)

    sql_texts_and_plans = {}
    for s in top_sqls:
        sid = s['sql_id']
        text = get_sql_text(sid, dbid, inst)
        plan = get_sql_plan(sid, dbid, inst)
        sql_texts_and_plans[sid] = {"text": text, "plan": plan}

    prompt = build_advisor_prompt(global_awr, focus_awr, top_sqls, sql_texts_and_plans)
    # enrich with RAG and call LLM
    advice = enrich_with_rag_and_llm(prompt, top_k=6)
    return {
        "top_sqls": top_sqls,
        "advisor_report": advice
    }
```

---

## `index_rag_corpus_chroma.py` (your provided corpus indexer — unchanged)

```python
# backend/index_rag_corpus_chroma.py
import glob
import os
import chromadb
from chromadb.utils import embedding_functions

CHROMA_PATH = "./chroma_db"
CORPUS_DIR = "./rag_corpus"
COLLECTION_NAME = "oracle_rag_docs"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = chromadb.PersistentClient(path=CHROMA_PATH)

embed_fn = embedding_functions.OpenAIEmbeddingFunction(
    api_key=OPENAI_API_KEY,
    model_name="text-embedding-3-large"
)

collection = client.get_or_create_collection(
    name=COLLECTION_NAME,
    embedding_function=embed_fn
)

def index_corpus():
    files = glob.glob(os.path.join(CORPUS_DIR, "*.txt"))
    docs, ids = [], []

    for i, fpath in enumerate(files):
        with open(fpath, "r", encoding="utf-8") as f:
            docs.append(f.read())
            ids.append(f"doc_{i}")

    collection.add(documents=docs, ids=ids)
    print(f"[OK] Indexed {len(docs)} documents.")

if __name__ == "__main__":
    index_corpus()
```

---

## `main.py` — FastAPI (endpoints + CORS)

```python
# backend/main.py
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from awr_oracle import get_db_info, find_snapshots, get_awr_report
from rag_chroma import compare_intervals_with_rag
from tuning_advisor import tuning_advisor_manual

app = FastAPI(title="Oracle AWR + RAG + AI Tuning Advisor")

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:4200").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in ALLOWED_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DoubleIntervalReq(BaseModel):
    global_start_date: str
    global_end_date: str
    focus_start_date: str
    focus_end_date: str
    section_pattern: str = ".*"

@app.post("/analyze-intervals")
def analyze_intervals(req: DoubleIntervalReq):
    dbid, inst = get_db_info()

    g_begin, g_end = find_snapshots(req.global_start_date, req.global_end_date, dbid, inst)
    if not g_begin:
        return {"error": "No snapshots found in global interval."}

    f_begin, f_end = find_snapshots(req.focus_start_date, req.focus_end_date, dbid, inst)
    if not f_begin:
        return {"error": "No snapshots found in focus interval."}

    awr_global = get_awr_report(g_begin, g_end, dbid, inst, req.section_pattern)
    awr_focus  = get_awr_report(f_begin, f_end, dbid, inst, req.section_pattern)

    analysis = compare_intervals_with_rag(awr_global, awr_focus)

    return {
        "global_begin_snap": g_begin,
        "global_end_snap": g_end,
        "focus_begin_snap": f_begin,
        "focus_end_snap": f_end,
        "analysis": analysis
    }

class TuningReq(BaseModel):
    global_start_date: str
    global_end_date: str
    focus_start_date: str
    focus_end_date: str
    section_pattern: str = ".*"
    top_n_sql: int = 5

@app.post("/tuning-advisor")
def tuning_advisor_endpoint(req: TuningReq):
    dbid, inst = get_db_info()

    g_begin, g_end = find_snapshots(req.global_start_date, req.global_end_date, dbid, inst)
    if not g_begin:
        return {"error": "No snapshots found in global interval."}

    f_begin, f_end = find_snapshots(req.focus_start_date, req.focus_end_date, dbid, inst)
    if not f_begin:
        return {"error": "No snapshots found in focus interval."}

    awr_global = get_awr_report(g_begin, g_end, dbid, inst, req.section_pattern)
    awr_focus  = get_awr_report(f_begin, f_end, dbid, inst, req.section_pattern)

    report = tuning_advisor_manual(awr_global, awr_focus, dbid, inst, f_begin, f_end, top_n=req.top_n_sql)

    return {
        "global_begin_snap": g_begin,
        "global_end_snap": g_end,
        "focus_begin_snap": f_begin,
        "focus_end_snap": f_end,
        "top_sqls": report["top_sqls"],
        "advisor_report": report["advisor_report"]
    }
```

---

# ✅ Frontend — Angular 17

Place these files in your Angular app under `src/app/`.

---

## `api.service.ts`

```ts
// src/app/api.service.ts
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

interface DoubleInterval {
  global_start_date: string;
  global_end_date: string;
  focus_start_date: string;
  focus_end_date: string;
  section_pattern?: string;
}

interface TuningRequest extends DoubleInterval {
  top_n_sql?: number;
}

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private BASE = 'http://localhost:8000';

  constructor(private http: HttpClient) {}

  analyzeIntervals(payload: DoubleInterval): Observable<any> {
    return this.http.post(`${this.BASE}/analyze-intervals`, payload);
  }

  tuningAdvisor(payload: TuningRequest): Observable<any> {
    return this.http.post(`${this.BASE}/tuning-advisor`, payload);
  }
}
```

---

## `app.component.ts`

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

  analysisResult: string | null = null;
  advisorResult: string | null = null;
  topSqls: any[] = [];
  loading = false;

  constructor(private api: ApiService) {}

  analyze() {
    this.analysisResult = null;
    this.loading = true;
    this.api.analyzeIntervals({
      global_start_date: this.globalStart,
      global_end_date: this.globalEnd,
      focus_start_date: this.focusStart,
      focus_end_date: this.focusEnd,
      section_pattern: this.sectionPattern
    }).subscribe({
      next: (res) => {
        this.analysisResult = res.analysis;
        this.loading = false;
      },
      error: (err) => {
        this.analysisResult = JSON.stringify(err);
        this.loading = false;
      }
    });
  }

  runAdvisor() {
    this.advisorResult = null;
    this.topSqls = [];
    this.loading = true;
    this.api.tuningAdvisor({
      global_start_date: this.globalStart,
      global_end_date: this.globalEnd,
      focus_start_date: this.focusStart,
      focus_end_date: this.focusEnd,
      section_pattern: this.sectionPattern,
      top_n_sql: this.topN
    }).subscribe({
      next: (res) => {
        this.topSqls = res.top_sqls || [];
        this.advisorResult = res.advisor_report;
        this.loading = false;
      },
      error: (err) => {
        this.advisorResult = JSON.stringify(err);
        this.loading = false;
      }
    });
  }
}
```

---

## `app.component.html`

```html
<!-- src/app/app.component.html -->
<div style="max-width:1000px; margin:20px auto; padding:20px; border:1px solid #ddd; border-radius:8px;">
  <h2>Oracle AWR Analyzer & Manual AI Tuning Advisor</h2>

  <section style="margin-top:12px;">
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
    <button (click)="analyze()" [disabled]="loading">Analyze Intervals</button>
    <button (click)="runAdvisor()" [disabled]="loading" style="margin-left:8px;">AI Tuning Advisor (Manual)</button>
    <span *ngIf="loading" style="margin-left:12px;">Working...</span>
  </div>

  <div *ngIf="analysisResult" style="margin-top:18px;">
    <h3>Comparative Analysis</h3>
    <pre style="white-space:pre-wrap; background:#f4f4f4; padding:12px;">{{ analysisResult }}</pre>
  </div>

  <div *ngIf="topSqls && topSqls.length" style="margin-top:18px;">
    <h3>Top SQLs in Focus Interval</h3>
    <table style="width:100%; border-collapse:collapse;">
      <thead>
        <tr><th style="border-bottom:1px solid #ccc">SQL_ID</th><th style="border-bottom:1px solid #ccc">Elapsed delta</th><th style="border-bottom:1px solid #ccc">Buffer gets</th><th style="border-bottom:1px solid #ccc">Disk reads</th></tr>
      </thead>
      <tbody>
        <tr *ngFor="let s of topSqls">
          <td style="border-bottom:1px solid #eee">{{ s.sql_id }}</td>
          <td style="border-bottom:1px solid #eee">{{ s.elapsed_time_delta }}</td>
          <td style="border-bottom:1px solid #eee">{{ s.buffer_gets_delta }}</td>
          <td style="border-bottom:1px solid #eee">{{ s.disk_reads_delta }}</td>
        </tr>
      </tbody>
    </table>
  </div>

  <div *ngIf="advisorResult" style="margin-top:18px;">
    <h3>AI Tuning Advisor Report</h3>
    <pre style="white-space:pre-wrap; background:#f9f9f9; padding:12px;">{{ advisorResult }}</pre>
  </div>
</div>
```

---

## `app.component.css` (optional)

```css
/* src/app/app.component.css */
input { padding:6px; font-size:14px; }
button { padding:8px 12px; font-size:14px; margin-bottom:6px; }
h2, h3, h4 { margin:8px 0; }
table td, table th { padding:6px; text-align:left; }
```

---

# 🧭 How to run

### Backend

1. Create a virtualenv and install deps:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Create `.env` with `OPENAI_API_KEY`, `ORACLE_*`, `CHROMA_PATH`, `ALLOWED_ORIGINS`.
3. Index your rag_corpus (once):

```bash
python index_rag_corpus_chroma.py
```

4. Run FastAPI:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

* Put Angular files into your Angular 17 app (or create a new app with `ng new`), ensure `HttpClientModule` & `FormsModule` are set in `AppModule`.
* Run `ng serve` (default `http://localhost:4200`).

CORS allows `http://localhost:4200` by default (see `.env`).

---

# ⚠️ Notes & small caveats

* The Oracle queries use `DBA_HIST_*` views and `DBMS_WORKLOAD_REPOSITORY.AWR_REPORT_TEXT`. Your account must have access (usually requires DBA privilege or appropriate grants).
* Date inputs from `<input type="datetime-local">` produce `YYYY-MM-DDTHH:MM` (no seconds). The Oracle queries use `TO_TIMESTAMP(...,'YYYY-MM-DD"T"HH24:MI:SS')`. If you pass `YYYY-MM-DDTHH:MM`, Oracle will parse it but to be safe you can extend with `:00` seconds or update the frontend to append `:00` automatically.
* LLM prompts rely on `gpt-4.1-mini` via the `openai` client. Ensure the installed `openai` package works with the `OpenAI` client as used. If your environment uses a different client, adapt the call (the code follows the modern OpenAI client call pattern used earlier).
* The advisor returns `top_sqls` and a textual `advisor_report`. The prompt instructs the model to explicitly say `"No issues found in the focus interval."` when appropriate.
* For production, add rate-limiting, authentication, and logging.

---

If you want, I can now:

* Add a simple **snapshot listing endpoint** to let the UI show available snapshots (handy to pick exact snap ids),
* Append seconds to frontend datetime inputs automatically,
* Provide a **docker-compose** (without Oracle image — you must provide a reachable Oracle DB),
* Tweak prompts for a different style (more actionable vs. more verbose).

Which of the above do you want next?
