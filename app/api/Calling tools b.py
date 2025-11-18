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


# -----------------------------
# Top SQL / Text / Plan
# -----------------------------
def get_top_sqls_between_snaps(begin_snap: int, end_snap: int, dbid: int, inst: int,
                               user: Optional[str] = None, password: Optional[str] = None, dsn: Optional[str] = None, limit: int = 10) -> List[Dict]:
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
                 user: Optional[str] = None, password: Optional[str] = None, dsn: Optional[str] = None, snap_id: int = None) -> str:
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
    return "\n".join([r[0] for r in rows if r[0]])


def get_sql_plan(sql_id: str, dbid: int, inst: int,
                 user: Optional[str] = None, password: Optional[str] = None, dsn: Optional[str] = None, limit: int = 2000) -> str:
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
    return "\n".join([r[2] for r in rows if r[2]])


# -----------------------------
# AWR / Section extraction
# -----------------------------
def get_awr_report(begin_snap: int, end_snap: int, dbid: int, inst: int,
                   user: Optional[str] = None, password: Optional[str] = None, dsn: Optional[str] = None, section_pattern: str = ".*") -> str:
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


# -----------------------------
# New Oracle tools for Function Calling
# -----------------------------
def get_latch_stats(snap_start, snap_end, dbid, inst, user, password, dsn):
    conn = get_db_connection(user, password, dsn)
    cur = conn.cursor()
    q = f"""
    SELECT event, total_waits, time_waited
    FROM dba_hist_event
    WHERE snap_id BETWEEN {snap_start} AND {snap_end}
      AND instance_number = {inst}
      AND dbid = {dbid}
      AND event LIKE 'latch%'
    """
    cur.execute(q)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(event=r[0], total_waits=r[1], time_waited=r[2]) for r in rows]


def get_wait_events(snap_start, snap_end, dbid, inst, user, password, dsn):
    conn = get_db_connection(user, password, dsn)
    cur = conn.cursor()
    q = f"""
    SELECT event, total_waits, time_waited
    FROM dba_hist_event
    WHERE snap_id BETWEEN {snap_start} AND {snap_end}
      AND instance_number = {inst}
      AND dbid = {dbid}
    ORDER BY time_waited DESC
    """
    cur.execute(q)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(event=r[0], total_waits=r[1], time_waited=r[2]) for r in rows]


def get_segment_stats(snap_start, snap_end, dbid, inst, user, password, dsn):
    conn = get_db_connection(user, password, dsn)
    cur = conn.cursor()
    q = f"""
    SELECT segment_name, tablespace_name, blocks, buffer_gets
    FROM dba_hist_segstat
    WHERE snap_id BETWEEN {snap_start} AND {snap_end}
      AND instance_number = {inst}
      AND dbid = {dbid}
    """
    cur.execute(q)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(segment=r[0], tablespace=r[1], blocks=r[2], buffer_gets=r[3]) for r in rows]


def get_memory_stats(snap_start, snap_end, dbid, inst, user, password, dsn):
    conn = get_db_connection(user, password, dsn)
    cur = conn.cursor()
    q = f"""
    SELECT statistic_name, value
    FROM dba_hist_sysstat
    WHERE snap_id BETWEEN {snap_start} AND {snap_end}
      AND instance_number = {inst}
      AND dbid = {dbid}
      AND statistic_name IN ('session pga memory', 'sga memory')
    """
    cur.execute(q)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(stat=r[0], value=r[1]) for r in rows]


def get_advisory_stats(snap_start, snap_end, dbid, inst, user, password, dsn):
    conn = get_db_connection(user, password, dsn)
    cur = conn.cursor()
    q = f"""
    SELECT name, value
    FROM dba_hist_advisory
    WHERE snap_id BETWEEN {snap_start} AND {snap_end}
      AND instance_number = {inst}
      AND dbid = {dbid}
    """
    cur.execute(q)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(name=r[0], value=r[1]) for r in rows]


def get_time_model_stats(snap_start, snap_end, dbid, inst, user, password, dsn):
    conn = get_db_connection(user, password, dsn)
    cur = conn.cursor()
    q = f"""
    SELECT stat_name, value
    FROM dba_hist_time_model
    WHERE snap_id BETWEEN {snap_start} AND {snap_end}
      AND instance_number = {inst}
      AND dbid = {dbid}
    """
    cur.execute(q)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(stat=r[0], value=r[1]) for r in rows]
