Parfait — **je te génère intégralement tous les fichiers `.txt` prêts à être indexés dans Chroma**, avec le contenu propre, compressé, optimisé pour un RAG performant.

Voici **tous les fichiers déjà remplis**, prêts à copier-coller dans ton projet.

---

# ✅ Structure

```
rag_corpus/
 ├── sql_indexing.txt
 ├── sql_execution_plans.txt
 ├── sql_performance_patterns.txt
 ├── db_io_and_storage.txt
 ├── concurrency_and_locks.txt
 ├── buffer_cache_and_working_set.txt
 ├── cpu_waits_and_parallelism.txt
 ├── general_db_performance_principles.txt
 └── troubleshooting_checklist.txt
```

---

# 📘 **sql_indexing.txt**

```
Indexing Strategy & Access Path Selection

Index basics:
Indexes are sorted structures accelerating row location by key. B-tree indexes support equality conditions, range scans, and prefix matches. Good selectivity (<5–10%) usually encourages index usage; low selectivity often triggers full table scans.

Common index anti-patterns:
- Functions on indexed columns (UPPER(col), TRIM(col)) break index usage.
- Leading wildcards ("%abc") prevent range scan.
- OR conditions on the same column often disable index usage; rewrite as UNION ALL or IN().
- Implicit datatype conversions on indexed columns cause full scans.

Composite index rules:
Predicates must match leading columns for range scans. Equality conditions before range conditions yield maximum efficiency.

Fast full index scan:
Oracle can scan a full index instead of the table when sorting is required or the index contains the required columns.

Indexing OLTP:
Prefer highly selective single-column indexes. Too many indexes slow down writes.

Indexing analytics:
Use composite indexes following filtering order, and covering indexes to reduce table access.

AWR symptoms of indexing issues:
- High 'db file scattered read' (multiblock reads, full scans).
- SQL with large buffer gets.
- High elapsed time with low executions.
```

---

# 📙 **sql_execution_plans.txt**

```
Execution Plans, Joins, and Scan Types

Execution plan principles:
The optimizer chooses a plan based on cardinality, CPU cost, and I/O cost. A plan is a tree of operations executed bottom-up.

Scan types:
- Full table scan: used when indexes are unusable, unselective, or stats are stale.
- Index range scan: used for selective predicates.
- Index skip scan: used when leading column has few distinct values.
- Fast full index scan: reads entire index, ignores ordering, fully parallelizable.

Join methods:
Nested Loop: efficient for small outer rowsets and indexed inner tables.
Hash Join: good for large datasets; spills to TEMP when memory is insufficient.
Merge Join: requires sorted inputs; excellent with pre-sorted data or indexes.

AWR symptoms:
- 'direct path read temp' → hash join spills due to low PGA.
- High 'db file sequential read' → many single-block index reads.
- Full scans dominating → missing indexes or stale stats.
- High I/O per execution → poor filtering or cartesian join.

Optimizer mis-estimation often causes:
- Wrong join method.
- Full scan instead of index.
- Excessive TEMP I/O.
```

---

# 📗 **sql_performance_patterns.txt**

```
SQL Performance Patterns & Anti-Patterns

Slow SQL common causes:
- SELECT * in high-frequency queries.
- Missing LIMIT/OFFSET in exploration queries.
- Correlated subqueries executed repeatedly.
- Non-sargable predicates: WHERE LOWER(col)=‘x’, col+1=5, etc.
- OR logic instead of IN().
- Functions on indexed columns.

Parameter sniffing:
The plan generated from first execution may not fit later executions. Solutions: bind-aware cursor, hints, dynamic sampling.

Analytical workloads pitfalls:
- Window functions on large datasets.
- GROUP BY on unfiltered data.
- Poor table partitioning leading to skew or hotspots.
- Joins on unindexed columns.

AWR indicators:
- High buffer gets.
- Large physical reads.
- CPU spikes on specific SQL_ID.
- Full scans or hash joins spilling to TEMP.

Fix patterns:
- Add proper indexes.
- Rewrite predicates to be sargable.
- Refactor subqueries.
- Apply hints for correct join method (only when necessary).
```

---

# 📘 **db_io_and_storage.txt**

```
Database I/O, Filesystem, and Latency Troubleshooting

I/O basics:
Random reads use single-block I/O (index lookups).
Sequential reads use multiblock I/O (full scans).
Latency dominates random reads; throughput dominates sequential reads.

Common AWR wait events:
- 'db file sequential read' → single-block I/O, index lookup heavy.
- 'db file scattered read' → full table scans or index fast full scans.
- 'direct path read/write' → parallel execution or large temp operations.

I/O investigation checklist:
- Average read latency (<5 ms is good).
- Distinguish random vs sequential read patterns.
- Identify top files by reads in AWR.
- Inspect TEMP usage and growth.
- Look at physical reads per execution of top SQL.

Possible fixes:
- Add indexes to reduce full scans.
- Move hot data to faster storage.
- Increase SGA for better caching.
- Improve stats for better plan choice.
- Tune parallel degree for large scans.
```

---

# 📙 **concurrency_and_locks.txt**

```
Concurrency, Locks, and Wait Events

Lock types:
- Row locks (TX): normal for OLTP.
- TX row lock contention: caused by missing FK indexes or long transactions.
- TM table locks: caused by unindexed foreign keys or DDL during activity.

Symptoms:
- High 'enq: TX - row lock contention'.
- 'cursor: pin S wait on X' for shared cursor contention.
- 'latch: cache buffers chains' for hot block contention.

Root causes:
- Missing index on foreign key → parent table locked on updates.
- Long transactions → row-level locking.
- Hot blocks frequently read → cause latch contention.

Fixes:
- Always index foreign key columns.
- Keep transactions short.
- Reduce hotspot reads using hash partitioning or reverse key indexes.
```

---

# 📕 **buffer_cache_and_working_set.txt**

```
Buffer Cache, Memory, and Working Set Analysis

Buffer cache:
Logical reads are served from memory. Physical reads occur when block is not cached.

AWR indicators:
- High logical reads but low hit ratio → working set too large.
- Many physical reads per execution → inefficient filtering.
- Spikes in 'db file scattered read' → table scans causing cache churn.

Memory recommendations:
- Increase SGA target or specific buffer cache pools.
- Pin frequently accessed objects.
- Reduce full scans through proper indexing.

PGA/TEMP:
- Hash join spills cause 'direct path read temp'.
- Increase pga_aggregate_target.
- Improve join and aggregation selectivity.
```

---

# 📗 **cpu_waits_and_parallelism.txt**

```
CPU Bottlenecks and Parallel Execution

CPU bottlenecks:
High 'DB CPU' in AWR means CPU saturation. Investigate top SQL by CPU_TIME.

Common CPU-heavy operations:
- Full table scans on large tables.
- PL/SQL loops processing row-by-row.
- Non-indexed joins.
- Large sorts.

Parallel execution:
- Parallel full scans reduce elapsed time but consume CPU.
- Too high degree of parallelism (DOP) causes queuing.
- 'PX Deq' wait events indicate inter-process coordination.

Fixes:
- Add indexes to reduce scanning and sorting.
- Rewrite PL/SQL loops into bulk operations.
- Adjust parallel degree based on CPU count.
```

---

# 📘 **general_db_performance_principles.txt**

```
Core Database Performance Principles

Performance fundamentals:
- Filter early, join later, aggregate last.
- Cardinality estimates influence all optimizer decisions.
- Accurate statistics are essential.
- Minimize row movement through operations.
- Use sargable predicates.

Universally true patterns:
- Most slow queries stem from missing indexes or stale stats.
- Temp spills are almost always due to insufficient PGA or large unfiltered joins.
- Full scans appear when filters are weak or stats are incorrect.

General rules:
- Prefer explicit JOINs.
- Limit result sets aggressively.
- Avoid unnecessary function calls.
- Partition large tables properly.
```

---

# 📄 **troubleshooting_checklist.txt**

```
Unified Oracle AWR Troubleshooting Checklist

1. Identify top SQL by:
   - Elapsed time
   - CPU time
   - Logical reads
   - Physical reads
   - Executions

2. Examine wait events:
   - I/O waits (sequential/scattered)
   - CPU bottlenecks
   - Lock waits (TX, TM)
   - TEMP spills (direct path read temp)

3. Check memory:
   - Buffer cache hit ratio
   - PGA usage
   - TEMP allocation

4. Check storage:
   - I/O latency
   - Files with highest reads
   - Sequential vs random I/O distribution

5. Diagnose root cause:
   - Missing indexes → full scans
   - Poor stats → mis-estimated plans
   - Low PGA → hash join spills
   - Hot blocks → latch contention
   - High TX waits → FK indexes missing

6. Propose fixes:
   - Add or adjust indexes
   - Refresh statistics
   - Increase PGA/SGA
   - Partition or cluster data
   - Rewrite SQL for sargability
```

---

# ✅ Tous les fichiers sont fournis intégralement.

Si tu veux, je peux aussi te générer :

### ✔ Le **script Python complet** qui crée automatiquement ces `.txt` dans `rag_corpus/`

### ✔ Le **code pour indexer tout le corpus dans Chroma**

### ✔ Le **backend FastAPI complet**

### ✔ Le **frontend Angular 17 complet**

### ✔ Le **pipeline RAG + AWR + LLM final**

Dis-moi ce que tu veux comme prochaine étape.
