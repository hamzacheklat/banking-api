# Backend — Full files (Version D, no Mongo)

Ce document contient **tous** les fichiers backend prêts à être copiés dans `backend/`.

---


## backend/requirements.txt
```
fastapi
uvicorn[standard]
python-dotenv
openai
cx_Oracle
pydantic
```

---

## backend/.env.sample
```
# copy to .env and fill
OPENAI_API_KEY=sk-...
ALLOWED_ORIGINS=http://localhost:4200
# optional default Oracle creds (overridable from frontend request)
ORACLE_USER=your_user
ORACLE_PASSWORD=your_password
ORACLE_DSN=host:1521/SERVICE_NAME
```

---

## backend/awr_oracle.py
```python
# backend/awr_oracle.py
import os
from typing import Optional, List, Dict, Tuple
from dotenv import load_dotenv
import cx_Oracle

load_dotenv()

ORACLE_USER = os.getenv("ORACLE_USER")
ORACLE_PASSWORD = os.getenv("ORACLE_PASSWORD")
ORACLE_DSN = os.getenv("ORACLE_DSN")


def get_db_connection(user: Optional[str] = None, password: Optional[str] = None, dsn: Optional[str] = None):
    """
    Return a cx_Oracle connection using env vars or provided params.
    """
    u = user or ORACLE_USER
    p = password or ORACLE_PASSWORD
    d = dsn or ORACLE_DSN
    if not (u and p and d):
        raise RuntimeError("Oracle credentials not set (env or params)")
    return cx_Oracle.connect(u, p, d, encoding="UTF-8")


def get_db_info_from_conn(conn) -> Tuple[int, int]:
    cur = conn.cursor()
    cur.execute("SELECT dbid FROM v$database")
    dbid_row = cur.fetchone()
    dbid = dbid_row[0] if dbid_row else None

    cur.execute("SELECT instance_number FROM v$instance")
    inst_row = cur.fetchone()
    instance_number = inst_row[0] if inst_row else 1

    cur.close()
    return dbid, instance_number


def fetch_snapshots(user: Optional[str] = None, password: Optional[str] = None, dsn: Optional[str] = None, limit: int = 1000) -> List[Dict]:
    """
    Return list of snapshots: dict with snap_id, begin_interval_time, end_interval_time, dbid, instance_number
    Ordered by begin_interval_time DESC (most recent first)
    """
    conn = get_db_connection(user, password, dsn)
    cur = conn.cursor()
    q = """
    SELECT snap_id, begin_interval_time, end_interval_time, dbid, instance_number
    FROM dba_hist_snapshot
    ORDER BY begin_interval_time DESC
    """
    cur.execute(q)
    rows = cur.fetchmany(limit)
    res = []
    for r in rows:
        begin = r[1]
        end = r[2]
        res.append({
            "snap_id": int(r[0]),
            "begin_interval_time": begin.strftime('%Y-%m-%dT%H:%M:%S') if begin else None,
            "end_interval_time": end.strftime('%Y-%m-%dT%H:%M:%S') if end else None,
            "dbid": int(r[3]) if r[3] else None,
            "instance_number": int(r[4]) if r[4] else None,
        })
    cur.close()
    conn.close()
    return res


# AWR report / Top SQL helpers (same semantics as earlier)
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


def get_awr_report(begin_snap: int, end_snap: int, dbid: int, inst: int, user: Optional[str] = None, password: Optional[str] = None, dsn: Optional[str] = None, section_pattern: str = ".*") -> str:
    conn = get_db_connection(user, password, dsn)
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
    return "
".join([r[0] for r in rows if r[0]])


def get_top_sqls_between_snaps(begin_snap: int, end_snap: int, dbid: int, inst: int, user: Optional[str] = None, password: Optional[str] = None, dsn: Optional[str] = None, limit: int = 10) -> List[Dict]:
    conn = get_db_connection(user, password, dsn)
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


def get_sql_text(sql_id: str, dbid: int, inst: int, user: Optional[str] = None, password: Optional[str] = None, dsn: Optional[str] = None, snap_id: int = None) -> str:
    conn = get_db_connection(user, password, dsn)
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
    return "
".join([r[0] for r in rows if r[0]])


def get_sql_plan(sql_id: str, dbid: int, inst: int, user: Optional[str] = None, password: Optional[str] = None, dsn: Optional[str] = None, limit: int = 2000) -> str:
    conn = get_db_connection(user, password, dsn)
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
    return "
".join([r[2] for r in rows if r[2]])
```

---

## backend/documentation_loader.py
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

## backend/heuristic_doc_selector.py
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
    return "

".join(ctx)
```

---

## backend/sql_extractors.py
```python
# backend/sql_extractors.py
def build_sql_block(sql_texts: dict, sql_plans: dict) -> str:
    blocks = []
    for sql_id in (sql_texts or {}).keys():
        text = sql_texts.get(sql_id, "")
        plan = sql_plans.get(sql_id, "")
        blocks.append(f"--- SQL ID: {sql_id} ---
SQL TEXT:
{text}

PLAN:
{plan}
")
    return "

".join(blocks)
```

---

## backend/tuning_advisor_manual.py
```python
# backend/tuning_advisor_manual.py
import os
from dotenv import load_dotenv
from openai import OpenAI

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
""".strip()


def run_tuning(awr_global: str, awr_focus: str, sql_blocks: str, docs_block: str) -> str:
    prompt = build_prompt(awr_global, awr_focus, sql_blocks, docs_block)
    # Use low temperature for deterministic output
    try:
        resp = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "You are an Oracle tuning expert."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.05,
            max_tokens=2500
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"[ERROR] OpenAI call failed: {e}"
```

---

## backend/main.py
```python
# backend/main.py
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from awr_oracle import (
    fetch_snapshots,
    get_awr_report,
    get_top_sqls_between_snaps,
    get_sql_text,
    get_sql_plan,
    get_db_connection,
    get_db_info_from_conn
)
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

class DBCreds(BaseModel):
    oracle_user: str
    oracle_password: str
    oracle_dsn: str

class SnapRequest(DBCreds):
    limit: int = 500

class AnalyzeReq(DBCreds):
    global_start_snap: int
    global_end_snap: int
    focus_start_snap: int
    focus_end_snap: int
    top_n_sql: int = 5

@app.post("/snapshots")
def list_snapshots(req: SnapRequest):
    try:
        snaps = fetch_snapshots(req.oracle_user, req.oracle_password, req.oracle_dsn, limit=req.limit)
        return {"snapshots": snaps}
    except Exception as e:
        return {"error": str(e)}

@app.post("/analyze-intervals")
def analyze_intervals(req: AnalyzeReq):
    try:
        # open a connection using the provided creds
        conn = get_db_connection(req.oracle_user, req.oracle_password, req.oracle_dsn)
        dbid, inst = get_db_info_from_conn(conn)
    except Exception as e:
        return {"error": f"Unable to connect to Oracle with provided credentials: {e}"}

    try:
        awr_global = get_awr_report(req.global_start_snap, req.global_end_snap, dbid, inst, req.oracle_user, req.oracle_password, req.oracle_dsn)
        awr_focus  = get_awr_report(req.focus_start_snap, req.focus_end_snap, dbid, inst, req.oracle_user, req.oracle_password, req.oracle_dsn)

        # get top SQLs for the focus interval
        top_sqls = get_top_sqls_between_snaps(req.focus_start_snap, req.focus_end_snap, dbid, inst, req.oracle_user, req.oracle_password, req.oracle_dsn, limit=req.top_n_sql)

        # get SQL texts & plans
        sql_texts = {}
        sql_plans = {}
        for s in top_sqls:
            sid = s["sql_id"]
            sql_texts[sid] = get_sql_text(sid, dbid, inst, req.oracle_user, req.oracle_password, req.oracle_dsn)
            sql_plans[sid] = get_sql_plan(sid, dbid, inst, req.oracle_user, req.oracle_password, req.oracle_dsn)

        # select doc fragments
        docs_block = select_relevant_docs(awr_global, awr_focus, sql_texts, sql_plans)
        sql_block = build_sql_block(sql_texts, sql_plans)

        advisor_report = run_tuning(awr_global, awr_focus, sql_block, docs_block)

        return {
            "global_begin_snap": req.global_start_snap,
            "global_end_snap": req.global_end_snap,
            "focus_begin_snap": req.focus_start_snap,
            "focus_end_snap": req.focus_end_snap,
            "top_sqls": top_sqls,
            "advisor_report": advisor_report,
            "docs_sent": bool(docs_block)
        }
    except Exception as e:
        return {"error": str(e)}
```

---

## backend/docs/ (fichiers d'exemples)

Crée le dossier `backend/docs/` avec ces fichiers résumés (déjà fournis dans la version précédente). Copie-colle le contenu de `common_oracle_issues.txt`, `io_contention.txt`, `temp_and_sorts.txt`, `latch_and_mutex.txt`, `cpu_tuning.txt`, `parallel_execution.txt`, `execution_plan_patterns.txt`, `join_issues.txt`, `awr_queries.sql`.

---

## Notes & recommandations

- Toutes les routes acceptent maintenant les identifiants Oracle envoyés depuis le frontend (multi-base). Les fonctions d'`awr_oracle` utilisent ces identifiants pour se connecter.
- `section_pattern` a été retiré de l'API `analyze-intervals` (comme demandé).
- L'appel OpenAI est conservé dans `tuning_advisor_manual.py`. Si tu veux un fallback local (mock) pour tester sans clé, je peux ajouter un mode `MOCK_ADVISOR=true`.
- `cx_Oracle` nécessite l'Oracle Instant Client installé sur la machine d'exécution.

---

Si tu veux que je :
- ajoute un fichier `run.sh` pour lancer uvicorn facilement — dis `runsh`,
- génère un `docker-compose` (backend + frontend + oracle-xe) — dis `docker`,
- fournis un mode `mock` (OpenAI off / fake responses) — dis `mock`.


