import oracledb
import json

def to_json(rows, cursor):
    """Convertit toute requête SQL en JSON propre."""
    col_names = [c[0] for c in cursor.description]
    return [dict(zip(col_names, row)) for row in rows]

def get_connection(user, password, dsn):
    return oracledb.connect(
        user=user,
        password=password,
        dsn=dsn
    )

# ------------------------------
#     FONCTIONS SQL
# ------------------------------

def run_query(conn, sql, params=None):
    cur = conn.cursor()
    cur.execute(sql, params or {})
    rows = cur.fetchall()
    return to_json(rows, cur)

def get_top_sql(conn):
    return run_query(conn, """
        SELECT sql_id, parsing_schema_name, elapsed_time, cpu_time,
               buffer_gets, executions, sql_fulltext
        FROM (
            SELECT *
            FROM v$sql
            ORDER BY elapsed_time DESC
        )
        WHERE ROWNUM <= 3
    """)

def get_top_wait_events(conn):
    return run_query(conn, """
        SELECT event, total_waits, time_waited, average_wait
        FROM (
            SELECT *
            FROM v$system_event
            ORDER BY time_waited DESC
        )
        WHERE ROWNUM <= 5
    """)

def get_top_sessions(conn):
    return run_query(conn, """
        SELECT sid, serial#, username, status, event,
               wait_class, blocking_session
        FROM v$session
        WHERE username IS NOT NULL
        ORDER BY status DESC, wait_class DESC
    """)

def get_execution_plan(conn, sql_id):
    cur = conn.cursor()
    cur.execute("""
        SELECT *
        FROM TABLE(DBMS_XPLAN.DISPLAY_CURSOR(:sql_id, NULL, 'ALLSTATS LAST'))
    """, sql_id=sql_id)
    return [line[0] for line in cur.fetchall()]

def get_ash(conn):
    return run_query(conn, """
        SELECT sample_time, session_id, session_state, event,
               sql_id, wait_class
        FROM v$active_session_history
        WHERE sample_time > SYSDATE - (1/24)
        ORDER BY sample_time DESC
    """)

def get_modified_parameters(conn):
    return run_query(conn, """
        SELECT name, value, ismodified
        FROM v$parameter
        WHERE ismodified <> 'FALSE'
    """)

def get_atp_metrics(conn):
    return run_query(conn, """
        SELECT name, value
        FROM v$sysmetric
        WHERE name IN (
            'Host CPU Utilization (%)',
            'Database CPU Time Ratio',
            'Physical Read Total IO Requests Per Sec',
            'Physical Write Total IO Requests Per Sec'
        )
    """)

# ------------------------------
#     MÉTHODE GLOBALE JSON
# ------------------------------

def run_full_diagnostic_json(user, password, dsn):
    conn = get_connection(user, password, dsn)

    result = {
        "top_sql": get_top_sql(conn),
        "top_wait_events": get_top_wait_events(conn),
        "top_sessions": get_top_sessions(conn),
        "execution_plans": {},
        "ash": get_ash(conn),
        "modified_parameters": get_modified_parameters(conn),
        "atp_metrics": get_atp_metrics(conn)
    }

    # Ajouter les plans d’exécution
    for entry in result["top_sql"]:
        sql_id = entry["SQL_ID"]
        result["execution_plans"][sql_id] = get_execution_plan(conn, sql_id)

    conn.close()

    # Retour JSON
    return json.dumps(result, indent=2, ensure_ascii=False)
