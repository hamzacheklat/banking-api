import re
import pdfplumber
import tiktoken
import oracledb
from openai import OpenAI

### CONFIG ###

PDF_PATH = "oracle_tuning.pdf"
MAX_TOKENS = 1200
EMBED_MODEL = "text-embedding-3-large"

client = OpenAI()

### TOKENIZER ###

tokenizer = tiktoken.encoding_for_model("gpt-4")

def token_count(text):
    return len(tokenizer.encode(text))

### PDF EXTRACTION ###

def extract_text(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"
    return text

### RECIPE SPLITTING ###

def split_recipes(text):
    pattern = r"(Recipe\s+\d+[-–].*?)(?=Recipe\s+\d+[-–]|\Z)"
    recipes = re.findall(pattern, text, re.S)
    return recipes

### CHUNKING ###

def smart_chunk(recipe):
    sections = re.split(
        r"(Problem|Solution|How It Works)",
        recipe
    )

    chunks = []
    current = ""

    for part in sections:
        if token_count(current + part) > MAX_TOKENS:
            chunks.append(current)
            current = part
        else:
            current += part

    if current:
        chunks.append(current)

    return chunks

### EMBEDDING ###

def embed(text):
    resp = client.embeddings.create(
        model=EMBED_MODEL,
        input=text
    )
    return resp.data[0].embedding

### ORACLE SETUP ###

def init_oracle():
    conn = oracledb.connect(
        user="user",
        password="password",
        dsn="localhost:1521/XEPDB1"
    )

    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rag_chunks (
            id NUMBER GENERATED ALWAYS AS IDENTITY,
            content CLOB,
            embedding VECTOR(3072)
        )
    """)

    conn.commit()
    return conn

### INSERT ###

def insert_chunk(conn, content, vector):
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO rag_chunks (content, embedding)
        VALUES (:1, :2)
    """, [content, vector])

    conn.commit()

### MAIN ###

def main():
    text = extract_text(PDF_PATH)
    recipes = split_recipes(text)

    conn = init_oracle()

    for r in recipes:
        chunks = smart_chunk(r)

        for c in chunks:
            if token_count(c) < 50:
                continue

            vec = embed(c)
            insert_chunk(conn, c, vec)

            print("Inserted chunk:", token_count(c), "tokens")

if __name__ == "__main__":
    main()


def token_count(text):
    return len(text) / 4

