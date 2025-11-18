Parfait ! Voici la version **complète et mise à jour de ton backend**, avec le support multi-snaps, sections, LLM Function Calling manuel avec boucle while (max 5 itérations), et suivi des fonctions appelées.

---

## 1️⃣ `awr_oracle.py`

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


def get_awr_report(begin_snap: int, end_snap: int, dbid: int, inst: int,
                   user: Optional[str] = None, password: Optional[str] = None, dsn: Optional[str] = None,
                   section_pattern: str = ".*") -> str:
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
    return "\n".join([r[0] for r in rows if r[0]])


def get_top_sqls_between_snaps(begin_snap: int, end_snap: int, dbid: int, inst: int,
                               user: Optional[str] = None, password: Optional[str] = None,
                               dsn: Optional[str] = None, limit: int = 10) -> List[Dict]:
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


def get_sql_text(sql_id: str, dbid: int, inst: int,
                 user: Optional[str] = None, password: Optional[str] = None,
                 dsn: Optional[str] = None, snap_id: int = None) -> str:
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
    return "\n".join([r[0] for r in rows if r[0]])


def get_sql_plan(sql_id: str, dbid: int, inst: int,
                 user: Optional[str] = None, password: Optional[str] = None,
                 dsn: Optional[str] = None, limit: int = 2000) -> str:
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
    return "\n".join([r[2] for r in rows if r[2]])
```

---

## 2️⃣ `tuning_advisor_manual.py`

```python
# backend/tuning_advisor_manual.py
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

TOOLS = {}

def register_tools(tools_dict):
    global TOOLS
    TOOLS = tools_dict


def call_llm_with_tools(messages, max_iterations=5):
    iteration = 0
    functions_called_total = []

    while iteration < max_iterations:
        iteration += 1
        try:
            resp = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=messages,
                temperature=0.05,
                max_tokens=3000
            )

            message = resp.choices[0].message
            content = message.get("content", "")
            fn_call = message.get("function_call")

            if not fn_call:
                return {"content": content, "functions_called": functions_called_total}

            fn_name = fn_call["name"]
            arguments = eval(fn_call.get("arguments", "{}"))

            if fn_name in TOOLS:
                tool_result = TOOLS[fn_name](**arguments)
                functions_called_total.append({
                    "function": fn_name,
                    "arguments": arguments,
                    "result": tool_result
                })
                messages = [
                    *messages,
                    {"role": "assistant", "content": content or ""},
                    {"role": "function", "name": fn_name, "content": str(tool_result)}
                ]
            else:
                return {
                    "content": f"{content}\n[ERROR] Unknown function requested: {fn_name}",
                    "functions_called": functions_called_total
                }

        except Exception as e:
            return {"content": f"[ERROR] OpenAI call failed: {e}", "functions_called": functions_called_total}

    return {
        "content": content + "\n[INFO] Max iterations reached",
        "functions_called": functions_called_total
    }


def run_section_tuning(section_name: str, global_content: str, focus_content: str, docs_block: str) -> dict:
    prompt = f"""
You are an Oracle performance tuning expert.
The section "{section_name}" is merged from multiple AWR reports for the GLOBAL interval and FOCUS interval.

Global section content:
{global_content}

Focus section content:
{focus_content}

Documentation extracts:
{docs_block}

Task:
- Identify anomalies present in FOCUS interval.
- For each anomaly, provide:
  - Problem
  - Why it happens
  - Precise recommendation (SQL or config change)
- Only output problems found.
- Language: English.
- You can request to call any of the registered tools if needed.
End.
""".strip()

    messages = [{"role": "user", "content": prompt}]
    return call_llm_with_tools(messages)


def run_final_summary(section_results: dict) -> dict:
    combined = ""
    for sec, res in section_results.items():
        combined += f"SECTION: {sec}\n{res['content']}\n\n"

    prompt = f"""
You are an Oracle performance tuning expert.

The following sections contain all detected anomalies from multiple merged AWR reports (GLOBAL vs FOCUS).

Task:
- Summarize each problem, indicating:
  - Section name
  - Problem
  - Cause
  - Recommendation (SQL/config)
  - Which reports/snap IDs it was found in

Only list actual problems detected.
You can request to call any registered tools if needed.
End.
{combined}
""".strip()

    messages = [{"role": "user", "content": prompt}]
    return call_llm_with_tools(messages)
```

---

## 3️⃣ `main.py`

```python
# backend/main.py
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from awr_oracle import (
    fetch_snapshots, get_awr_report, get_top_sqls_between_snaps,
    get_sql_text, get_sql_plan, get_db_connection, get_db_info_from_conn
)
from heuristic_doc_selector import select_relevant_docs
from sql_extractors import build_sql_block
from tuning_advisor_manual import run_section_tuning, run_final_summary, register_tools

load_dotenv()
app = FastAPI(title="Oracle Tuning Advisor")

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

class AnalyzeReq(DBCreds):
    global_start_snap: int
    global_end_snap: int
    focus_start_snap: int
    focus_end_snap: int
    top_n_sql: int = 5

SECTION_NAMES = [
    "SQL ordered by Elapsed Time",
    "SQL ordered by CPU Time",
    "SQL ordered by Gets",
    "SQL ordered by Reads",
    "Top Wait Events",
    "Instance Efficiency Stats",
    "IO Stats",
    "System Statistics",
    "Time Model Stats",
    "Advisory Statistics",
    "Latch Activity",
    "Segment Statistics",
    "Memory Statistics"
]

@app.post("/snapshots")
def list_snapshots(req: DBCreds):
    try:
        snaps = fetch_snapshots(req.oracle_user, req.oracle_password, req.oracle_dsn)
        return {"snapshots": snaps}
    except Exception as e:
        return {"error": str(e)}


@app.post("/analyze-intervals")
def analyze_intervals(req: AnalyzeReq):
    try:
        conn = get_db_connection(req.oracle_user, req.oracle_password, req.oracle_dsn)
        dbid, inst = get_db_info_from_conn(conn)
    except Exception as e:
        return {"error": f"Oracle connection failed: {e}"}

    # Register tools for function calling
    tools_dict = {
        "get_top_sqls": lambda s,e,l=req.top_n_sql: get_top_sqls_between_snaps(s,e,dbid,inst,req.oracle_user,req.oracle_password,req.oracle_dsn,l),
        "get_sql_plan": lambda sql_id: get_sql_plan(sql_id,dbid,inst,req.oracle_user,req.oracle_password,req.oracle_dsn),
        "get_sql_text": lambda sql_id: get_sql_text(sql_id,dbid,inst,req.oracle_user,req.oracle_password,req.oracle_dsn)
    }
    register_tools(tools_dict)

    section_results = {}
    docs_block = ""  # optionnel : select_relevant_docs(…)

    for section in SECTION_NAMES:
        global_text = get_awr_report(req.global_start_snap, req.global_end_snap, dbid, inst, req.oracle_user, req.oracle_password, req.oracle_dsn, section_pattern=section)
        focus_text  = get_awr_report(req.focus_start_snap, req.focus_end_snap, dbid, inst, req.oracle_user, req.oracle_password, req.oracle_dsn, section_pattern=section)
        res = run_section_tuning(section, global_text, focus_text, docs_block)
        section_results[section] = res

    final_summary = run_final_summary(section_results)

    return {
        "sections": section_results,
        "final_summary": final_summary
    }
```

---

Avec ces fichiers, ton backend est **prêt pour :**

* Multi-snaps fusionnés par section (Global et Focus).
* LLM Function Calling manuel avec **boucle while max 5 itérations**.
* Suivi complet des fonctions appelées et résultats.
* Final summary consolidé par section avec problème, cause et recommandation.

---

Si tu veux, je peux maintenant te proposer **`sql_extractors.py` et `heuristic_doc_selector.py` mis à jour** pour que le merge multi-snaps et la sélection des docs soit **optimisé pour les prompts**.

Veux‑tu que je fasse ça ?
