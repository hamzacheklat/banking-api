from sqlalchemy import create_engine
from urllib.parse import quote_plus

odbc_str = (
    "DSN=DBREPOV2;"
    "UID=SVC2ASYDATABASED;"
    "PWD=3aGfH3Lb2+3aGvHUH573Sagd08Ne4;"
)

params = quote_plus(odbc_str)

engine = create_engine(
    f"sybase+pyodbc:///?odbc_connect={params}"
)

conn = engine.connect()
print("OK")
