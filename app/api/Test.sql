SELECT snap_id, begin_interval_time, end_interval_time
FROM dba_hist_snapshot
WHERE dbid = &dbid
  AND instance_number = &inst_num
ORDER BY snap_id;
