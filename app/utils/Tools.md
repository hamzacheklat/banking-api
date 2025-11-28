Parfait — je t’ai préparé **la version complète et mise à jour de `backend/app/tools.py`** avec les **3 nouveaux outils prioritaires** que tu voulais :

* `get_sql_child_info` — info sur les children/child_number/plan_hash en mémoire (v$sql_child / v$sql).
* `get_sql_history_by_snap` — série temporelle d’elapsed/executions par snap pour un sql_id (correlation).
* `compare_plans_diff` — comparaison opérateur-par-opérateur (diff) entre deux plans (plan_hash A vs B) pour faciliter la lecture (operator-by-operator).

J’ai aussi ajouté :

* un **simple mécanisme d’audit/log** (append dans `tools_exec.log`) pour chaque exécution d’outil (outil, args, user ip optional, timestamp).
* une implémentation robuste (try/except) et retours JSON structurés.
* l’intégration dans la whitelist (tu n’as rien à changer côté frontend — l’endpoint `/tools/execute` reste le même).

---

## Remplace `backend/app/tools.py` par le fichier complet ci-dessous

> Copie-colle tout ce fichier (remplace l’ancien `tools.py`).

```python
# backend/app/tools.py
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from .db_connection import get_connection
import datetime
import json
import os

router = APIRouter()

LOG_PATH = os.getenv("TOOLS_EXEC_LOG", "/tmp/tools_exec.log")

# --- Request models ---
class ToolExecRequest(BaseModel):
    tool: str
    args: Dict[str, Any]
    dsn: str
    username: str
    password: str

# --- Helper: create conn and cursor ---
def _get_conn_cur(dsn: str, username: str, password: str):
    conn = get_connection(dsn, username, password)
    cur = conn.cursor()
    return conn, cur

def _audit_log(entry: Dict[str, Any]):
    try:
        entry_line = json.dumps(entry, default=str)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(entry_line + "\n")
    except Exception:
        # best-effort: do not break tool execution on logging error
        pass

# --- Tools implementations (read-only) ---
def tool_list_snaps(cur, args):
    dbid = args.get("dbid")
    inst = args.get("inst")
    start = args.get("start_time")
    end = args.get("end_time")
    limit = int(args.get("limit", 1000))
    if not all([dbid, inst, start, end]):
        raise ValueError("dbid, inst, start_time, end_time required")
    cur.execute("""
        SELECT snap_id, begin_interval_time, end_interval_time
        FROM dba_hist_snapshot
        WHERE dbid = :dbid
          AND instance_number = :inst
          AND begin_interval_time >= TO_TIMESTAMP(:start, 'YYYY-MM-DD\"T\"HH24:MI:SS')
          AND begin_interval_time <= TO_TIMESTAMP(:end, 'YYYY-MM-DD\"T\"HH24:MI:SS')
        ORDER BY begin_interval_time DESC
    """, {"dbid": dbid, "inst": inst, "start": start, "end": end})
    rows = cur.fetchmany(limit)
    snaps = [{"snap_id": int(r[0]), "begin": r[1].isoformat() if r[1] else None, "end": r[2].isoformat() if r[2] else None} for r in rows]
    return snaps

def tool_top_sql(cur, args):
    top_n = int(args.get("n", 10))
    if "snap_id" in args:
        from_snap = to_snap = int(args["snap_id"])
    elif "from_snap" in args and "to_snap" in args:
        from_snap = int(args["from_snap"]); to_snap = int(args["to_snap"])
    else:
        raise ValueError("snap_id or from_snap/to_snap required")
    cur.execute("""
        SELECT ss.sql_id, SUM(NVL(ss.elapsed_time_delta, ss.elapsed_time_total,0)) elapsed,
               SUM(NVL(ss.executions_delta,0)) execs
        FROM dba_hist_sqlstat ss
        WHERE ss.snap_id BETWEEN :from_snap AND :to_snap
        GROUP BY ss.sql_id
        ORDER BY elapsed DESC
    """, {"from_snap": from_snap, "to_snap": to_snap})
    rows = cur.fetchmany(top_n)
    return [{"sql_id": r[0], "elapsed": int(r[1] or 0), "executions": int(r[2] or 0)} for r in rows]

def tool_top_waits(cur, args):
    top_n = int(args.get("n", 10))
    if "snap_id" in args:
        from_snap = to_snap = int(args["snap_id"])
    elif "from_snap" in args and "to_snap" in args:
        from_snap = int(args["from_snap"]); to_snap = int(args["to_snap"])
    else:
        raise ValueError("snap_id or from_snap/to_snap required")
    cur.execute("""
        SELECT event, SUM(NVL(time_waited_delta,0)) time_waited, SUM(NVL(total_waits_delta,0)) total_waits
        FROM dba_hist_system_event
        WHERE snap_id BETWEEN :from_snap AND :to_snap
        GROUP BY event
        ORDER BY time_waited DESC
    """, {"from_snap": from_snap, "to_snap": to_snap})
    rows = cur.fetchmany(top_n)
    return [{"event": r[0], "time_waited": int(r[1] or 0), "total_waits": int(r[2] or 0)} for r in rows]

def tool_top_sessions(cur, args):
    top_n = int(args.get("n", 10))
    if "snap_id" in args:
        from_snap = to_snap = int(args["snap_id"])
    elif "from_snap" in args and "to_snap" in args:
        from_snap = int(args["from_snap"]); to_snap = int(args["to_snap"])
    else:
        raise ValueError("snap_id or from_snap/to_snap required")
    cur.execute("""
        SELECT MIN(begin_interval_time), MAX(end_interval_time)
        FROM dba_hist_snapshot
        WHERE snap_id BETWEEN :from_snap AND :to_snap
    """, {"from_snap": from_snap, "to_snap": to_snap})
    row = cur.fetchone()
    if not row or row[0] is None:
        return []
    begin_time, end_time = row
    cur.execute("""
        SELECT ash.session_id, COUNT(*) samples, SUM(NVL(ash.cpu_time,0)) cpu_sum
        FROM dba_hist_active_sess_history ash
        WHERE ash.sample_time BETWEEN :btime AND :etime
        GROUP BY ash.session_id
        ORDER BY cpu_sum DESC
    """, {"btime": begin_time, "etime": end_time})
    rows = cur.fetchmany(top_n)
    return [{"session_id": r[0], "samples": int(r[1] or 0), "cpu_sum": int(r[2] or 0)} for r in rows]

def tool_fetch_sql_text(cur, args):
    sql_id = args.get("sql_id")
    if not sql_id:
        raise ValueError("sql_id required")
    cur.execute("SELECT sql_text FROM dba_hist_sqltext WHERE sql_id = :sql_id FETCH FIRST 1 ROWS ONLY", {"sql_id": sql_id})
    r = cur.fetchone()
    if r and r[0]:
        return {"sql_text": r[0]}
    cur.execute("SELECT LISTAGG(text,'') WITHIN GROUP (ORDER BY piece) FROM v$sqltext WHERE sql_id = :sql_id", {"sql_id": sql_id})
    r = cur.fetchone()
    return {"sql_text": (r[0] if r and r[0] else "")}

def tool_get_plan(cur, args):
    sql_id = args.get("sql_id")
    plan_hash = args.get("plan_hash", None)
    if not sql_id:
        raise ValueError("sql_id required")
    if plan_hash:
        cur.execute("""
            SELECT operation || ' ' || NVL(options,'') || ' ' || NVL(object_name,'') plan_line
            FROM dba_hist_sql_plan
            WHERE sql_id = :sql_id AND plan_hash_value = :ph
            ORDER BY id
        """, {"sql_id": sql_id, "ph": plan_hash})
        rows = cur.fetchall()
        return {"plan_hash": plan_hash, "plan_lines": [r[0] for r in rows]}
    else:
        cur.execute("""
            SELECT plan_hash_value, operation || ' ' || NVL(options,'') || ' ' || NVL(object_name,'') plan_line
            FROM dba_hist_sql_plan
            WHERE sql_id = :sql_id
            ORDER BY plan_hash_value, id
        """, {"sql_id": sql_id})
        rows = cur.fetchall()
        out = {}
        for ph, line in rows:
            out.setdefault(str(ph), []).append(line)
        return {"plans": out}

def tool_get_table_stats(cur, args):
    obj = args.get("object")
    if not obj:
        raise ValueError("object required (SCHEMA.TABLE or TABLE)")
    owner = None
    tbl = obj
    if "." in obj:
        owner, tbl = obj.split(".",1)
    if owner:
        cur.execute("SELECT last_analyzed, num_rows FROM dba_tables WHERE owner=:owner AND table_name=:tbl", {"owner": owner, "tbl": tbl})
        rows = cur.fetchall()
        results = [{"owner": owner, "last_analyzed": (r[0].isoformat() if r[0] else None), "num_rows": int(r[1]) if r[1] is not None else None} for r in rows]
    else:
        cur.execute("SELECT owner, last_analyzed, num_rows FROM dba_tables WHERE table_name=:tbl", {"tbl": tbl})
        rows = cur.fetchall()
        results = [{"owner": r[0], "last_analyzed": (r[1].isoformat() if r[1] else None), "num_rows": int(r[2]) if r[2] is not None else None} for r in rows]
    return results

def tool_compare_plans(cur, args):
    sql_id = args.get("sql_id")
    plan_a = args.get("plan_a")
    plan_b = args.get("plan_b")
    if not sql_id or not plan_a or not plan_b:
        raise ValueError("sql_id, plan_a, plan_b required")
    cur.execute("""
        SELECT operation || ' ' || NVL(options,'') || ' ' || NVL(object_name,'') plan_line
        FROM dba_hist_sql_plan
        WHERE sql_id = :sql_id AND plan_hash_value = :ph
        ORDER BY id
    """, {"sql_id": sql_id, "ph": plan_a})
    a_lines = [r[0] for r in cur.fetchall()]
    cur.execute("""
        SELECT operation || ' ' || NVL(options,'') || ' ' || NVL(object_name,'') plan_line
        FROM dba_hist_sql_plan
        WHERE sql_id = :sql_id AND plan_hash_value = :ph
        ORDER BY id
    """, {"sql_id": sql_id, "ph": plan_b})
    b_lines = [r[0] for r in cur.fetchall()]
    return {"plan_a": a_lines, "plan_b": b_lines}

def tool_run_explain(cur, args):
    sql = args.get("sql")
    if not sql:
        raise ValueError("sql required")
    try:
        # try best-effort to use PLAN_TABLE
        cur.execute("BEGIN EXECUTE IMMEDIATE 'TRUNCATE TABLE PLAN_TABLE'; EXCEPTION WHEN OTHERS THEN NULL; END;")
    except Exception:
        pass
    cur.execute(f"EXPLAIN PLAN FOR {sql}")
    cur.execute("SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY('PLAN_TABLE', NULL, 'ALL'))")
    lines = [r[0] for r in cur.fetchall()]
    return {"explain": lines}

# ----- NEW TOOLS -----

def tool_get_sql_child_info(cur, args):
    """
    Returns child cursors info for given sql_id (v$sql and v$sql_child usage).
    args: { "sql_id": "...", "limit": 50 }
    """
    sql_id = args.get("sql_id")
    limit = int(args.get("limit", 50))
    if not sql_id:
        raise ValueError("sql_id required")
    # try v$sql to get child_number, plan_hash_value, parsing_schema_name, module, executions
    cur.execute("""
        SELECT child_number, plan_hash_value, parsing_schema_name, module, executions, elapsed_time
        FROM v$sql
        WHERE sql_id = :sql_id
        ORDER BY child_number
    """, {"sql_id": sql_id})
    rows = cur.fetchmany(limit)
    out = []
    for r in rows:
        out.append({
            "child_number": int(r[0]) if r[0] is not None else None,
            "plan_hash_value": int(r[1]) if r[1] is not None else None,
            "parsing_schema": r[2],
            "module": r[3],
            "executions": int(r[4]) if r[4] is not None else None,
            "elapsed_time": int(r[5]) if r[5] is not None else None
        })
    return {"children": out}

def tool_get_sql_history_by_snap(cur, args):
    """
    Returns timeseries of elapsed/executions per snap for a given sql_id between from_snap and to_snap.
    args: { "sql_id": "...", "from_snap": int, "to_snap": int }
    """
    sql_id = args.get("sql_id")
    from_snap = args.get("from_snap")
    to_snap = args.get("to_snap")
    if not sql_id or from_snap is None or to_snap is None:
        raise ValueError("sql_id, from_snap, to_snap required")
    cur.execute("""
        SELECT ss.snap_id, ss.dbid, ss.instance_number, SUM(NVL(ss.elapsed_time_delta, ss.elapsed_time_total,0)) elapsed,
               SUM(NVL(ss.executions_delta,0)) executions
        FROM dba_hist_sqlstat ss
        WHERE ss.sql_id = :sql_id AND ss.snap_id BETWEEN :from_snap AND :to_snap
        GROUP BY ss.snap_id, ss.dbid, ss.instance_number
        ORDER BY ss.snap_id
    """, {"sql_id": sql_id, "from_snap": from_snap, "to_snap": to_snap})
    rows = cur.fetchall()
    return [{"snap_id": int(r[0]), "dbid": int(r[1]) if r[1] is not None else None, "instance": int(r[2]) if r[2] is not None else None, "elapsed": int(r[3] or 0), "executions": int(r[4] or 0)} for r in rows]

def _normalize_plan_lines(lines: List[str]) -> List[str]:
    """Utility: normalize plan lines for diffing (strip whitespace, uppercase)."""
    return [l.strip() for l in lines if l and l.strip()]

def _operator_key(line: str) -> str:
    """Extract a simplified operator token to compare (heuristic)."""
    s = line.upper()
    # pick first 4-6 tokens as operator signature
    parts = s.split()
    return " ".join(parts[:4]) if parts else s

def tool_compare_plans_diff(cur, args):
    """
    Compare two plans operator-by-operator and return a diff.
    args: { "sql_id": "...", "plan_a": "123", "plan_b": "456" }
    """
    sql_id = args.get("sql_id")
    plan_a = args.get("plan_a")
    plan_b = args.get("plan_b")
    if not sql_id or not plan_a or not plan_b:
        raise ValueError("sql_id, plan_a, plan_b required")
    # fetch both plans
    cur.execute("""
        SELECT operation || ' ' || NVL(options,'') || ' ' || NVL(object_name,'') plan_line
        FROM dba_hist_sql_plan
        WHERE sql_id = :sql_id AND plan_hash_value = :ph
        ORDER BY id
    """, {"sql_id": sql_id, "ph": plan_a})
    a_lines = [r[0] for r in cur.fetchall()]
    cur.execute("""
        SELECT operation || ' ' || NVL(options,'') || ' ' || NVL(object_name,'') plan_line
        FROM dba_hist_sql_plan
        WHERE sql_id = :sql_id AND plan_hash_value = :ph
        ORDER BY id
    """, {"sql_id": sql_id, "ph": plan_b})
    b_lines = [r[0] for r in cur.fetchall()]

    a_norm = _normalize_plan_lines(a_lines)
    b_norm = _normalize_plan_lines(b_lines)

    # Build a simple line-by-line diff: align by operator key sequence
    diffs = []
    max_len = max(len(a_norm), len(b_norm))
    for i in range(max_len):
        la = a_norm[i] if i < len(a_norm) else None
        lb = b_norm[i] if i < len(b_norm) else None
        if la == lb:
            diffs.append({"pos": i+1, "type": "same", "a": la, "b": lb})
        else:
            # compute operator keys
            ka = _operator_key(la) if la else None
            kb = _operator_key(lb) if lb else None
            diffs.append({"pos": i+1, "type": "diff", "a": la, "b": lb, "op_a": ka, "op_b": kb})
    # Additionally, summarize main differences: access path changes (FULL -> INDEX), join method changes (NESTED -> HASH)
    summary = {"access_path_changes": [], "join_method_changes": []}
    for entry in diffs:
        if entry["type"] == "diff":
            a_upper = (entry.get("a") or "").upper()
            b_upper = (entry.get("b") or "").upper()
            # access path heuristics
            if "TABLE ACCESS FULL" in a_upper and "INDEX" in b_upper:
                summary["access_path_changes"].append({"pos": entry["pos"], "from": "TABLE ACCESS FULL", "to": "INDEX_SCAN"})
            if "INDEX" in a_upper and "TABLE ACCESS FULL" in b_upper:
                summary["access_path_changes"].append({"pos": entry["pos"], "from": "INDEX_SCAN", "to": "TABLE ACCESS FULL"})
            # join method heuristics
            join_types = ["NESTED LOOPS", "HASH JOIN", "MERGE JOIN"]
            for jt in join_types:
                if jt in a_upper and jt not in b_upper:
                    summary["join_method_changes"].append({"pos": entry["pos"], "from": jt, "to": "other"})
                if jt in b_upper and jt not in a_upper:
                    summary["join_method_changes"].append({"pos": entry["pos"], "from": "other", "to": jt})
    return {"plan_a": a_lines, "plan_b": b_lines, "diffs": diffs, "summary": summary}

# --- Router execute ---
@router.post("/execute")
async def tools_execute(req: ToolExecRequest, request: Request):
    allowed = {
        "list_snaps": tool_list_snaps,
        "top_sql": tool_top_sql,
        "top_waits": tool_top_waits,
        "top_sessions": tool_top_sessions,
        "fetch_sql_text": tool_fetch_sql_text,
        "get_plan": tool_get_plan,
        "get_table_stats": tool_get_table_stats,
        "compare_plans": tool_compare_plans,
        "run_explain": tool_run_explain,
        # new
        "get_sql_child_info": tool_get_sql_child_info,
        "get_sql_history_by_snap": tool_get_sql_history_by_snap,
        "compare_plans_diff": tool_compare_plans_diff
    }
    if req.tool not in allowed:
        raise HTTPException(status_code=400, detail=f"Tool {req.tool} not allowed")
    conn = None
    try:
        conn, cur = _get_conn_cur(req.dsn, req.username, req.password)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"DB connect failed: {e}")

    # audit entry (best-effort: capture client host if available)
    client_host = None
    try:
        client_host = request.client.host
    except Exception:
        client_host = None
    audit_entry = {
        "time": datetime.datetime.utcnow().isoformat(),
        "tool": req.tool,
        "args": req.args,
        "user": req.username,
        "client": client_host
    }
    _audit_log(audit_entry)

    try:
        func = allowed[req.tool]
        res = func(cur, req.args or {})
        return {"ok": True, "tool": req.tool, "result": res}
    except Exception as e:
        # log error
        audit_entry_error = {**audit_entry, "error": str(e)}
        _audit_log(audit_entry_error)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass
```

---

## Ce que j’ai ajouté exactement et pourquoi

* `tool_get_sql_child_info`: permet d’identifier **les différents children** d’un SQL en shared pool (child_number, plan_hash_value, parsing schema, module). Très utile pour repérer cursors multi-plan liés aux binds ou modules différents.
* `tool_get_sql_history_by_snap`: renvoie la **série temporelle** d’`elapsed`/`executions` par snap pour un sql_id — indispensable pour **corréler** un jump d’elapsed avec l’apparition d’un nouveau plan ou d’un évènement.
* `tool_compare_plans_diff`: fait une **comparaison lisible** opérateur-par-opérateur et extrait heuristiquement les changements d’`access path` (TABLE ACCESS FULL ↔ INDEX) et de méthode de jointure (HASH vs NESTED). Résultat structuré (`diffs` + `summary`) pour que le frontend/LLM le consomme facilement.
* Un petit **audit log** (`/tmp/tools_exec.log` par défaut) pour garder trace des exécutions.

---

## Intégration — points pratiques

1. **Inclure le router** dans ton `main.py` si ce n’est pas déjà fait (chemin `/tools/execute` changé en `/tools/execute` vs ancien `/tools/execute` — j’ai exposé router at `/tools` maybe previously you used `/tools/execute` route; to keep consistent, include with prefix `/tools`):

```python
# in backend/app/main.py (ou ton fichier principal)
from .tools import router as tools_router
app.include_router(tools_router, prefix="/tools")
```

L'appel final devient `POST http://<host>:8000/tools/execute` (body = ToolExecRequest JSON).

2. **Permissions** : certaines vues (`v$sql`, `dba_hist_*`, `dba_tables`) nécessitent des droits (SELECT_CATALOG_ROLE). Assure-toi d’utiliser un utilisateur disposant des droits nécessaires.

3. **Log file** : change `TOOLS_EXEC_LOG` env var si tu veux stocker ailleurs (ex: `/var/log/awr_tools.log`).

---

## Frontend : comment exploiter `compare_plans_diff` et `get_sql_history_by_snap`

* Quand LLM propose `compare_plans_diff` (plan_a, plan_b), appelle `/tools/execute` avec `tool: "compare_plans_diff", args: {sql_id, plan_a, plan_b}`.
* Affiche `result.summary` en haut et rende les `diffs` en table : position, type(same/diff), a_line, b_line, op_a/op_b.
* Pour `get_sql_history_by_snap`, affiche un petit time-series chart (hours vs elapsed) — tu peux réutiliser ng2-charts.

---

Souhaites-tu que je :

1. **Te fournisse aussi les modifications frontend** (ex : boutons dans la chat UI pour exécuter `get_sql_child_info`, `get_sql_history_by_snap`, `compare_plans_diff` et affichage nicifié du diff) — prêt à coller ?
2. **Ajoute la journalisation dans une table Oracle** (au lieu du fichier) pour audit centralisé ?
3. **Mieux affiner le diff** (opérateur matching basé sur indentation/ID au lieu de position simple) — plus précis mais plus long à implémenter ?

Dis-moi lequel tu veux en premier et je te fournis le code prêt à coller.
