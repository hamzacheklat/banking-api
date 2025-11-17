def find_snapshots(start_date: str, end_date: str, dbid: int, instance_number: int):
    """
    Normalize input timestamps and find snapshot boundaries.
    Accepts:
      - 'YYYY-MM-DDTHH:MM'
      - 'YYYY-MM-DDTHH:MM:SS'
      - 'YYYY-MM-DD HH:MM'
      - 'YYYY-MM-DD HH:MM:SS'
    """

    import re
    def normalize(ts: str) -> str:
        if "T" in ts:
            ts = ts.replace("T", " ")
        # If no seconds, add :00
        if re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$", ts):
            ts += ":00"
        return ts

    start_ts = normalize(start_date)
    end_ts = normalize(end_date)

    conn = get_db_connection()
    cur = conn.cursor()

    q_begin = """
        SELECT snap_id
        FROM dba_hist_snapshot
        WHERE dbid = :dbid
          AND instance_number = :inst
          AND begin_interval_time >= TO_TIMESTAMP(:start_ts, 'YYYY-MM-DD HH24:MI:SS')
        ORDER BY begin_interval_time
    """

    q_end = """
        SELECT snap_id
        FROM dba_hist_snapshot
        WHERE dbid = :dbid
          AND instance_number = :inst
          AND end_interval_time <= TO_TIMESTAMP(:end_ts, 'YYYY-MM-DD HH24:MI:SS')
        ORDER BY end_interval_time DESC
    """

    cur.execute(q_begin, dbid=dbid, inst=instance_number, start_ts=start_ts)
    row = cur.fetchone()
    begin_snap = row[0] if row else None

    cur.execute(q_end, dbid=dbid, inst=instance_number, end_ts=end_ts)
    row = cur.fetchone()
    end_snap = row[0] if row else None

    # Fallbacks if no match
    if begin_snap is None:
        cur.execute("""
            SELECT snap_id
            FROM (
                SELECT snap_id, end_interval_time
                FROM dba_hist_snapshot
                WHERE dbid = :dbid
                  AND instance_number = :inst
                  AND end_interval_time <= TO_TIMESTAMP(:end_ts, 'YYYY-MM-DD HH24:MI:SS')
                ORDER BY end_interval_time DESC
            ) WHERE ROWNUM = 1
        """, dbid=dbid, inst=instance_number, end_ts=end_ts)
        r = cur.fetchone()
        if r:
            begin_snap = r[0]

    if end_snap is None:
        cur.execute("""
            SELECT snap_id
            FROM (
                SELECT snap_id, begin_interval_time
                FROM dba_hist_snapshot
                WHERE dbid = :dbid
                  AND instance_number = :inst
                  AND begin_interval_time >= TO_TIMESTAMP(:start_ts, 'YYYY-MM-DD HH24:MI:SS')
                ORDER BY begin_interval_time
            ) WHERE ROWNUM = 1
        """, dbid=dbid, inst=instance_number, start_ts=start_ts)
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
