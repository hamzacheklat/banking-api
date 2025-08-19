from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Paramètres de connexion
user_name = "Q"
user_password 
user_schema = "iaml"
db_host = "your_host"
db_port = "1521"
db_service = vice_name"

# URI Oracle
URI = f"oracle://{user_name}:{user_password}@{db_host}:{db_port}/{db_service}"

# Création session
def _db(uri=URI):
    db_engine = create_engine(uri)
    session_factory = sessionmaker(bind=db_engine)
    return session_factory()

# Exécution du SELECT
def select_data():
    session = _db()
    query = text("""
        SELECT *
        FROM product_action_available
        WHERE ROWNUM <= 20
    """)
    result = session.connection().execute(query)

    for row in result:
        print(row)

if __name__ == "__main__":
    select_data()
