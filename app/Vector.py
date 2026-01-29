import oracledb

conn = oracledb.connect(user="user", password="pwd", dsn="dsn")
cursor = conn.cursor()

# vec = list[float] de ton embedding
arr = conn.arrayvar(oracledb.DB_TYPE_BINARY_FLOAT, vec)

cursor.execute("""
    BEGIN
        INSERT INTO rag_chunks (content, embedding)
        VALUES (:1, :2);
    END;
""", [content, arr])

conn.commit()
