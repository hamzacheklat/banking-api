Parfait — je te fournis **tout ce qu’il faut** pour remplir ta base SQLite `awr.db` avec **20 snapshots synthétiques** (incluant la *problem window* où `db file sequential read` et `sql_hot` apparaissent).
Tu peux soit exécuter le **script Python** (recommandé), soit exécuter le **fichier SQL** fourni.

Je fournis :

* `create_and_populate_awr.py` — script Python complet (crée la DB + insère 20 snapshots, 3 sections par snapshot si tu veux les stocker en bloc texte).
* `simulate_data.sql` — version SQL brute si tu préfères l’importer.
* Commandes de vérification (SELECT) pour contrôler les données.

Tout en français — prêt à lancer.

---

## 1) Script Python (recommandé) — `create_and_populate_awr.py`

Copie-colle ce fichier et exécute `python create_and_populate_awr.py`.

```python
# create_and_populate_awr.py
import sqlite3
import os
from datetime import datetime, timedelta
import random
import textwrap

DB_PATH = "awr.db"

def create_schema(conn):
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = OFF;")
    cur.execute("DROP TABLE IF EXISTS snapshots;")
    cur.execute("""
    CREATE TABLE snapshots (
        snap_id INTEGER PRIMARY KEY AUTOINCREMENT,
        snap_time TEXT,
        cpu_usage REAL,
        io_latency REAL,
        top_sql TEXT,
        wait_events TEXT
    );
    """)
    conn.commit()

def make_iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S")

def normal_top_sql(i):
    sql_id = f"sql_{i}"
    return textwrap.dedent(f"""\
        SQL_ID={sql_id};
        CPU_TIME={random.randint(5,30)}ms;
        ELAPSED={random.randint(10,60)}ms;
        PLAN=INDEX RANGE SCAN on small_table;
        ROWS={random.randint(100,2000)};
    """)

def normal_waits(i):
    return textwrap.dedent(f"""\
        Top waits:
          db file scattered read: {random.randint(5,40)}ms
          SQL*Net message from client: {random.randint(5,40)}ms
    """)

def problem_top_sql(i):
    # problematic SQL: heavy CPU, full scan, sql_hot
    return textwrap.dedent(f"""\
        SQL_ID=sql_hot;
        CPU_TIME={random.randint(150,320)}ms;
        ELAPSED={random.randint(200,600)}ms;
        WAIT_EVENT=db file sequential read;
        PLAN=FULL TABLE SCAN on big_table;
        ROWS={random.randint(50000,200000)};
    """)

def problem_waits(i):
    return textwrap.dedent(f"""\
        Top waits:
          db file sequential read: {random.randint(120,400)}ms
          log file sync: {random.randint(10,120)}ms
    """)

def populate(conn, n_snapshots=20, problem_range=(7,12)):
    cur = conn.cursor()
    base_time = datetime(2025, 11, 15, 9, 0, 0)  # fixed time for reproducibility

    for i in range(1, n_snapshots + 1):
        ts = base_time + timedelta(minutes=3 * i)
        iso_ts = make_iso(ts)

        if problem_range[0] <= i <= problem_range[1]:
            cpu_usage = round(random.uniform(60, 95), 2)
            io_latency = round(random.uniform(4.0, 12.0), 2)
            top_sql = problem_top_sql(i)
            wait_events = problem_waits(i)
        else:
            cpu_usage = round(random.uniform(5, 40), 2)
            io_latency = round(random.uniform(0.8, 3.5), 2)
            top_sql = normal_top_sql(i)
            wait_events = normal_waits(i)

        cur.execute("""
            INSERT INTO snapshots (snap_time, cpu_usage, io_latency, top_sql, wait_events)
            VALUES (?, ?, ?, ?, ?)
        """, (iso_ts, cpu_usage, io_latency, top_sql, wait_events))

    conn.commit()

def main():
    # remove old DB if exists
    if os.path.exists(DB_PATH):
        print(f"[INFO] Removing existing {DB_PATH}")
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    create_schema(conn)
    populate(conn, n_snapshots=20, problem_range=(7,12))
    conn.close()
    print(f"[OK] Created {DB_PATH} with 20 snapshots (problem snapshots {7}..{12}).")
    print("Vérifier avec : sqlite3 awr.db \"SELECT COUNT(*) FROM snapshots;\"")
    print("Exemple: sqlite3 awr.db \"SELECT snap_id, snap_time, cpu_usage, io_latency, substr(top_sql,1,80) FROM snapshots ORDER BY snap_id;\"")

if __name__ == "__main__":
    main()
```

### Exécution

```bash
python create_and_populate_awr.py
```

Après exécution tu auras `awr.db` dans le répertoire courant.

---

## 2) Fichier SQL brut — `simulate_data.sql`

Si tu préfères importer via sqlite CLI, copie-colle ceci dans `simulate_data.sql` puis exécute `sqlite3 awr.db < simulate_data.sql`.

```sql
-- simulate_data.sql
PRAGMA foreign_keys = OFF;
DROP TABLE IF EXISTS snapshots;

CREATE TABLE snapshots (
  snap_id INTEGER PRIMARY KEY AUTOINCREMENT,
  snap_time TEXT,
  cpu_usage REAL,
  io_latency REAL,
  top_sql TEXT,
  wait_events TEXT
);

-- We'll insert 20 snapshots, with a problematic window between 7 and 12
BEGIN TRANSACTION;

INSERT INTO snapshots (snap_time, cpu_usage, io_latency, top_sql, wait_events) VALUES
('2025-11-15T09:03:00', 23.45, 1.85,
 'SQL_ID=sql_1; CPU_TIME=12ms; ELAPSED=20ms; PLAN=INDEX RANGE SCAN on small_table; ROWS=800;',
 'Top waits: db file scattered read: 12ms; SQL*Net message from client: 20ms;');

INSERT INTO snapshots (snap_time, cpu_usage, io_latency, top_sql, wait_events) VALUES
('2025-11-15T09:06:00', 18.12, 1.22,
 'SQL_ID=sql_2; CPU_TIME=8ms; ELAPSED=18ms; PLAN=INDEX RANGE SCAN on small_table; ROWS=640;',
 'Top waits: db file scattered read: 8ms; SQL*Net message from client: 25ms;');

-- snapshots 3..6 (normal)
INSERT INTO snapshots (snap_time, cpu_usage, io_latency, top_sql, wait_events) VALUES
('2025-11-15T09:09:00', 15.77, 1.75,
 'SQL_ID=sql_3; CPU_TIME=15ms; ELAPSED=25ms; PLAN=INDEX RANGE SCAN on small_table; ROWS=1200;',
 'Top waits: db file scattered read: 15ms; SQL*Net message from client: 36ms;');

INSERT INTO snapshots (snap_time, cpu_usage, io_latency, top_sql, wait_events) VALUES
('2025-11-15T09:12:00', 12.50, 0.98,
 'SQL_ID=sql_4; CPU_TIME=7ms; ELAPSED=12ms; PLAN=INDEX RANGE SCAN on small_table; ROWS=400;',
 'Top waits: db file scattered read: 6ms; SQL*Net message from client: 18ms;');

INSERT INTO snapshots (snap_time, cpu_usage, io_latency, top_sql, wait_events) VALUES
('2025-11-15T09:15:00', 30.05, 2.25,
 'SQL_ID=sql_5; CPU_TIME=20ms; ELAPSED=45ms; PLAN=INDEX RANGE SCAN on small_table; ROWS=1800;',
 'Top waits: db file scattered read: 22ms; SQL*Net message from client: 12ms;');

INSERT INTO snapshots (snap_time, cpu_usage, io_latency, top_sql, wait_events) VALUES
('2025-11-15T09:18:00', 28.90, 2.75,
 'SQL_ID=sql_6; CPU_TIME=18ms; ELAPSED=38ms; PLAN=INDEX RANGE SCAN on small_table; ROWS=1500;',
 'Top waits: db file scattered read: 18ms; SQL*Net message from client: 14ms;');

-- PROBLEM WINDOW start (7..12)
INSERT INTO snapshots (snap_time, cpu_usage, io_latency, top_sql, wait_events) VALUES
('2025-11-15T09:21:00', 68.12, 8.55,
 'SQL_ID=sql_hot; CPU_TIME=210ms; ELAPSED=450ms; WAIT_EVENT=db file sequential read; PLAN=FULL TABLE SCAN on big_table; ROWS=80000;',
 'Top waits: db file sequential read: 220ms; log file sync: 40ms;');

INSERT INTO snapshots (snap_time, cpu_usage, io_latency, top_sql, wait_events) VALUES
('2025-11-15T09:24:00', 72.34, 9.10,
 'SQL_ID=sql_hot; CPU_TIME=195ms; ELAPSED=420ms; WAIT_EVENT=db file sequential read; PLAN=FULL TABLE SCAN on big_table; ROWS=75000;',
 'Top waits: db file sequential read: 200ms; log file sync: 55ms;');

INSERT INTO snapshots (snap_time, cpu_usage, io_latency, top_sql, wait_events) VALUES
('2025-11-15T09:27:00', 75.00, 10.50,
 'SQL_ID=sql_hot; CPU_TIME=230ms; ELAPSED=520ms; WAIT_EVENT=db file sequential read; PLAN=FULL TABLE SCAN on big_table; ROWS=90000;',
 'Top waits: db file sequential read: 300ms; log file sync: 60ms;');

INSERT INTO snapshots (snap_time, cpu_usage, io_latency, top_sql, wait_events) VALUES
('2025-11-15T09:30:00', 64.33, 7.80,
 'SQL_ID=sql_hot; CPU_TIME=185ms; ELAPSED=380ms; WAIT_EVENT=db file sequential read; PLAN=FULL TABLE SCAN on big_table; ROWS=68000;',
 'Top waits: db file sequential read: 180ms; log file sync: 30ms;');

INSERT INTO snapshots (snap_time, cpu_usage, io_latency, top_sql, wait_events) VALUES
('2025-11-15T09:33:00', 70.21, 9.00,
 'SQL_ID=sql_hot; CPU_TIME=200ms; ELAPSED=410ms; WAIT_EVENT=db file sequential read; PLAN=FULL TABLE SCAN on big_table; ROWS=77000;',
 'Top waits: db file sequential read: 210ms; log file sync: 45ms;');

INSERT INTO snapshots (snap_time, cpu_usage, io_latency, top_sql, wait_events) VALUES
('2025-11-15T09:36:00', 66.84, 8.10,
 'SQL_ID=sql_hot; CPU_TIME=190ms; ELAPSED=400ms; WAIT_EVENT=db file sequential read; PLAN=FULL TABLE SCAN on big_table; ROWS=72000;',
 'Top waits: db file sequential read: 195ms; log file sync: 50ms;');

-- snapshots 13..20 (back to normal)
INSERT INTO snapshots (snap_time, cpu_usage, io_latency, top_sql, wait_events) VALUES
('2025-11-15T09:39:00', 22.00, 1.50,
 'SQL_ID=sql_13; CPU_TIME=15ms; ELAPSED=30ms; PLAN=INDEX RANGE SCAN on small_table; ROWS=900;',
 'Top waits: db file scattered read: 12ms; SQL*Net message from client: 20ms;');

INSERT INTO snapshots (snap_time, cpu_usage, io_latency, top_sql, wait_events) VALUES
('2025-11-15T09:42:00', 18.75, 1.10,
 'SQL_ID=sql_14; CPU_TIME=8ms; ELAPSED=18ms; PLAN=INDEX RANGE SCAN on small_table; ROWS=450;',
 'Top waits: db file scattered read: 7ms; SQL*Net message from client: 12ms;');

INSERT INTO snapshots (snap_time, cpu_usage, io_latency, top_sql, wait_events) VALUES
('2025-11-15T09:45:00', 16.20, 1.95,
 'SQL_ID=sql_15; CPU_TIME=12ms; ELAPSED=22ms; PLAN=INDEX RANGE SCAN on small_table; ROWS=1100;',
 'Top waits: db file scattered read: 14ms; SQL*Net message from client: 10ms;');

INSERT INTO snapshots (snap_time, cpu_usage, io_latency, top_sql, wait_events) VALUES
('2025-11-15T09:48:00', 20.40, 2.10,
 'SQL_ID=sql_16; CPU_TIME=18ms; ELAPSED=36ms; PLAN=INDEX RANGE SCAN on small_table; ROWS=1600;',
 'Top waits: db file scattered read: 20ms; SQL*Net message from client: 15ms;');

INSERT INTO snapshots (snap_time, cpu_usage, io_latency, top_sql, wait_events) VALUES
('2025-11-15T09:51:00', 24.00, 1.85,
 'SQL_ID=sql_17; CPU_TIME=10ms; ELAPSED=20ms; PLAN=INDEX RANGE SCAN on small_table; ROWS=700;',
 'Top waits: db file scattered read: 9ms; SQL*Net message from client: 5ms;');

INSERT INTO snapshots (snap_time, cpu_usage, io_latency, top_sql, wait_events) VALUES
('2025-11-15T09:54:00', 19.88, 1.40,
 'SQL_ID=sql_18; CPU_TIME=12ms; ELAPSED=25ms; PLAN=INDEX RANGE SCAN on small_table; ROWS=880;',
 'Top waits: db file scattered read: 11ms; SQL*Net message from client: 8ms;');

COMMIT;
```

### Import

```bash
sqlite3 awr.db < simulate_data.sql
```

---

## 3) Quick checks / requêtes utiles

Après création, vérifie avec :

```bash
# nombre de snapshots
sqlite3 awr.db "SELECT COUNT(*) FROM snapshots;"

# lister les snapshots 1..20
sqlite3 awr.db "SELECT snap_id, snap_time, cpu_usage, io_latency, substr(top_sql,1,120), substr(wait_events,1,120) FROM snapshots ORDER BY snap_id;"

# vérifier problem window (snap_id 7..12)
sqlite3 awr.db "SELECT snap_id, snap_time, cpu_usage, io_latency, top_sql, wait_events FROM snapshots WHERE snap_id BETWEEN 7 AND 12 ORDER BY snap_id;"
```

---

## 4) Notes & recommandations

* Les timestamps dans le script Python sont fixés au 15 nov 2025 à 09:03/06/... pour reproductibilité ; adapte `base_time` si tu veux d'autres dates.
* Le *problem window* est `snap_id` 7..12 (inclus) — tu peux modifier `(7,12)` dans le script Python.
* Les colonnes `top_sql` et `wait_events` contiennent des blocs texte imitant ce que contient un AWR pour faciliter le parsing / chunking.
* Si tu veux stocker des sections séparées (TOP_SQL, WAIT_EVENTS, IO_PROFILE) plutôt que concaténés, je peux te fournir une variante de schéma et d’ingestion.

---

Si tu veux, j’exécute la génération (te fournir le contenu du fichier créé) ou je t’ajoute le script pour **convertir ces snapshots en blocs** comme dans ton premier design (section_name + text_blob) — dis simplement « oui convertis en sections » et je fournis ça tout de suite.
