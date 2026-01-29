import cx_Oracle

# ------------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------------
DSN = "host:1521/ORCLCDB.localdomain"
USER = "rag_user"
PWD = "rag_pwd"

# ------------------------------------------------------------------
# SQL STATEMENTS
# ------------------------------------------------------------------

DROP_TABLE_SQL = """
BEGIN
    EXECUTE IMMEDIATE 'DROP TABLE oracle_rag_docs PURGE';
EXCEPTION
    WHEN OTHERS THEN
        IF SQLCODE != -942 THEN
            RAISE;
        END IF;
END;
"""

CREATE_TABLE_SQL = """
CREATE TABLE oracle_rag_docs (
    id          NUMBER
                GENERATED ALWAYS AS IDENTITY,
    topic       VARCHAR2(50)      NOT NULL,
    sub_topics  VARCHAR2(4000),
    source      VARCHAR2(200)     NOT NULL,
    content     CLOB              NOT NULL,
    embedding   VECTOR(384, FLOAT32),
    created_at  TIMESTAMP DEFAULT SYSTIMESTAMP,

    CONSTRAINT oracle_rag_docs_pk
        PRIMARY KEY (id)
)
"""

CREATE_VECTOR_INDEX_SQL = """
CREATE VECTOR INDEX oracle_rag_vec_idx
ON oracle_rag_docs (embedding)
ORGANIZATION NEIGHBOR PARTITIONS
DISTANCE COSINE
"""

CREATE_TOPIC_INDEX_SQL = """
CREATE INDEX oracle_rag_topic_idx
ON oracle_rag_docs (topic)
"""

CREATE_SOURCE_INDEX_SQL = """
CREATE INDEX oracle_rag_source_idx
ON oracle_rag_docs (source)
"""

# OPTIONAL JSON INDEX (if you store sub_topics as JSON)
JSON_CHECK_SQL = """
ALTER TABLE oracle_rag_docs
ADD CONSTRAINT oracle_rag_sub_topics_json_chk
CHECK (sub_topics IS JSON)
"""

JSON_INDEX_SQL = """
CREATE SEARCH INDEX oracle_rag_sub_topics_json_idx
ON oracle_rag_docs (sub_topics)
FOR JSON
"""

# ------------------------------------------------------------------
# EXECUTION
# ------------------------------------------------------------------

def main(drop_existing: bool = True, enable_json_index: bool = False):
    conn = cx_Oracle.connect(USER, PWD, DSN)
    cur = conn.cursor()

    if drop_existing:
        print("🗑 Dropping existing table (if exists)...")
        cur.execute(DROP_TABLE_SQL)

    print("📦 Creating table oracle_rag_docs...")
    cur.execute(CREATE_TABLE_SQL)

    print("🧠 Creating VECTOR index...")
    cur.execute(CREATE_VECTOR_INDEX_SQL)

    print("📌 Creating topic index...")
    cur.execute(CREATE_TOPIC_INDEX_SQL)

    print("📌 Creating source index...")
    cur.execute(CREATE_SOURCE_INDEX_SQL)

    if enable_json_index:
        print("🧩 Enabling JSON constraint + index on sub_topics...")
        cur.execute(JSON_CHECK_SQL)
        cur.execute(JSON_INDEX_SQL)

    conn.commit()
    cur.close()
    conn.close()

    print("✅ Oracle RAG schema successfully created")


# ------------------------------------------------------------------
# ENTRY POINT
# ------------------------------------------------------------------

if __name__ == "__main__":
    main(
        drop_existing=True,       # set False in prod
        enable_json_index=False   # True if sub_topics stored as JSON
    )
