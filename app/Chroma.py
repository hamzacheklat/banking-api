# vector_store.py
import os
import chromadb
from chromadb.config import Settings
import config

# Utilise un chemin absolu pour éviter problèmes de cwd
PERSIST_DIR = os.path.abspath(config.CHROMA_DB_DIR)

print("Chroma persist dir:", PERSIST_DIR)

chroma_client = chromadb.Client(
    Settings(
        persist_directory=PERSIST_DIR,
        # for newer versions, specify implementation to ensure parquet+duckdb
        chroma_db_impl="duckdb+parquet",
        anonymized_telemetry=False
    )
)

def get_collection():
    return chroma_client.get_or_create_collection(
        name="docs",
        metadata={"description": "Documents Confluence IV2"},
        embedding_function=None
    )
