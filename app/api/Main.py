# backend/main.py
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from typing import List, Dict, Any

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

app = FastAPI(title="Oracle Tuning Advisor - Range & Sectioned LLM Orchestration")

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

class RangeAnalyzeReq(DBCreds):
    begin_snap: int
    end_snap: int
    top_n_sql: int = 5
    # Optional override: list of section regexes/names to iterate; if omitted use defaults below
    sections: List[str] = None

# Default sections to iterate (used as regexes passed to get_awr_report)
DEFAULT_SECTIONS = [
    "SQL ordered by Elapsed Time",       # SQL ordered by Elapsed Time
    "SQL ordered by CPU",                # SQL ordered by CPU Time
    "SQL ordered by Gets",               # SQL ordered by Gets
    "SQL ordered by Reads",              # SQL ordered by Reads
    "Wait Events",                        # Wait Events / Top Timed Events
    "System Statistics",                 # System Statistics
    "Instance Activity",                 # Instance Activity / IO stats
    "Latch Activity",                    # Latch Activity
    "Top Timed Events",                  # Alternative header
]

@app.post("/snapshots")
def list_snapshots(req: DBCreds):
    try:
        snaps = fetch_snapshots(req.oracle_user, req.oracle_password, req.oracle_dsn, limit=1000)
        return {"snapshots": snaps}
    except Exception as e:
        return {"error": str(e)}

@app.post("/analyze-range")
def analyze_range(req: RangeAnalyzeReq):
    """
    Orchestrates:
    - For begin..end: creates intervals (b -> b+1)
    - For each interval, for each section:
        - fetch GLOBAL section (begin..end) and FOCUS section (b..b+1)
        - collect top SQLs for focus and SQL texts/plans
        - call LLM per-section
    - After sections for an interval are processed -> call LLM to produce interval-level report
    - After all intervals -> call LLM to produce global report aggregating interval reports
    Returns JSON with per-interval reports and final global report.
    """
    # sanity
    if req.end_snap <= req.begin_snap:
        return {"error": "end_snap must be greater than begin_snap"}

    sections = req.sections or DEFAULT_SECTIONS

    # connect once to get dbid/inst and validate creds
    try:
        conn = get_db_connection(req.oracle_user, req.oracle_password, req.oracle_dsn)
        dbid, inst = get_db_info_from_conn(conn)
        conn.close()
    except Exception as e:
        return {"error": f"Unable to connect to Oracle with provided credentials: {e}"}

    # Fetch the GLOBAL AWR once (for global context)
    try:
        awr_global_full = get_awr_report(req.begin_snap, req.end_snap, dbid, inst, req.oracle_user, req.oracle_password, req.oracle_dsn)
    except Exception as e:
        return {"error": f"Unable to fetch global AWR: {e}"}

    per_interval_results = []
    interval_reports_texts = []  # for final global aggregation

    # iterate intervals: begin -> begin+1, ..., end-1 -> end
    for b in range(req.begin_snap, req.end_snap):
        e = b + 1
        interval_label = f"{b}->{e}"
        interval_entry: Dict[str, Any] = {
            "interval": {"begin_snap": b, "end_snap": e},
            "sections": {},
            "interval_report": None
        }

        section_summaries = []  # collect each section LLM response (text) for the interval

        for sec in sections:
            try:
                # fetch the section for GLOBAL (begin..end) and for FOCUS (b..e)
                sec_global_text = get_awr_report(req.begin_snap, req.end_snap, dbid, inst, req.oracle_user, req.oracle_password, req.oracle_dsn, section_pattern=sec)
                sec_focus_text = get_awr_report(b, e, dbid, inst, req.oracle_user, req.oracle_password, req.oracle_dsn, section_pattern=sec)
            except Exception as ex:
                # non-fatal: record error text and continue
                interval_entry["sections"][sec] = {"error": f"Error fetching section: {ex}"}
                continue

            # if both are empty, skip to next section
            if not (sec_global_text or sec_focus_text):
                # keep minimal note so frontend can display skipped sections
                interval_entry["sections"][sec] = {"skipped": True}
                continue

            # Get top SQLs for this focus interval (we fetch even if section isn't strictly SQL-related)
            try:
                top_sqls = get_top_sqls_between_snaps(b, e, dbid, inst, req.oracle_user, req.oracle_password, req.oracle_dsn, limit=req.top_n_sql)
            except Exception as ex:
                top_sqls = []
                # continue; we won't block analysis if SQLs fail

            # fetch sql texts & plans
            sql_texts = {}
            sql_plans = {}
            for s in top_sqls:
                sid = s.get("sql_id")
                if not sid:
                    continue
                try:
                    sql_texts[sid] = get_sql_text(sid, dbid, inst, req.oracle_user, req.oracle_password, req.oracle_dsn)
                except Exception:
                    sql_texts[sid] = ""
                try:
                    sql_plans[sid] = get_sql_plan(sid, dbid, inst, req.oracle_user, req.oracle_password, req.oracle_dsn)
                except Exception:
                    sql_plans[sid] = ""

            # select docs relevant to this section (heuristic)
            docs_block = select_relevant_docs(sec_global_text, sec_focus_text, sql_texts, sql_plans)

            # build sql block (text+plans)
            sql_block = build_sql_block(sql_texts, sql_plans)

            # call the LLM for this section (use run_tuning)
            try:
                section_report = run_tuning(sec_global_text or awr_global_full, sec_focus_text or "", sql_block, docs_block)
            except Exception as ex:
                section_report = f"[ERROR] LLM section call failed: {ex}"

            # store results for this section
            interval_entry["sections"][sec] = {
                "global_sent": bool(sec_global_text),
                "focus_sent": bool(sec_focus_text),
                "top_sqls": top_sqls,
                "section_report": section_report
            }

            # collect for later interval-level aggregation
            section_summaries.append(f"--- Section: {sec} ---\n{section_report}")

        # After all sections processed for this interval, produce an interval-level report
        try:
            combined_section_reports_text = "\n\n".join(section_summaries) if section_summaries else ""
            # For the interval-level final call, we send:
            # - awr_global_full as "GLOBAL"
            # - combined_section_reports_text as "FOCUS summary for this interval"
            interval_report = run_tuning(awr_global_full, combined_section_reports_text, "", "")  # SQL/docs already embedded in section reports
        except Exception as ex:
            interval_report = f"[ERROR] Interval LLM summarization failed: {ex}"

        interval_entry["interval_report"] = interval_report
        per_interval_results.append(interval_entry)
        interval_reports_texts.append(f"--- Interval {interval_label} ---\n{interval_report}")

    # After looping all intervals → final global aggregation
    try:
        all_intervals_combined = "\n\n".join(interval_reports_texts)
        final_global_report = run_tuning(awr_global_full, all_intervals_combined, "", "")
    except Exception as ex:
        final_global_report = f"[ERROR] Global LLM summarization failed: {ex}"

    return {
        "range_begin": req.begin_snap,
        "range_end": req.end_snap,
        "num_intervals": req.end_snap - req.begin_snap,
        "per_interval": per_interval_results,
        "global_awr_sent": bool(awr_global_full),
        "global_report": final_global_report
    }
