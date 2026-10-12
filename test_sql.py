import sqlite3
import tomllib

import pandas as pd
from openai import OpenAI

with open(".streamlit/secrets.toml", "rb") as f:
    key = tomllib.load(f)["GROQ_API_KEY"]

client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=key)
MODEL = "openai/gpt-oss-120b"

conn = sqlite3.connect("data/mydata.db")


def get_schema(conn):
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [r[0] for r in cur.fetchall()]
    lines = []
    for t in tables:
        cur.execute(f"PRAGMA table_info({t});")
        cols = [f"{c[1]} ({c[2]})" for c in cur.fetchall()]
        lines.append(f"Table {t}: " + ", ".join(cols))
    return "\n".join(lines)


def generate_sql(question, schema):
    prompt = f"""You are a SQLite expert.

Here is the database schema:
{schema}

Write ONE SQLite SELECT query that answers the user's question.
Rules:
- Return ONLY the SQL query.
- No explanations, no markdown, no code fences, no trailing semicolon.

Question: {question}
SQL:"""
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    sql = resp.choices[0].message.content.strip()
    sql = sql.replace("```sql", "").replace("```", "").strip()
    return sql.rstrip(";")


schema = get_schema(conn)
question = "What are the top 5 product names by total sales?"
sql = generate_sql(question, schema)

print("QUESTION:", question)
print("\nSQL:\n", sql)

df = pd.read_sql_query(sql, conn)
print("\nRESULT:\n", df.to_string(index=False))
