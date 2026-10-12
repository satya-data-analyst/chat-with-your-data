"""
Chat with your data  --  a text-to-SQL assistant built with Streamlit.
Ask a question in plain English; the app writes SQL, runs it, and answers.

Run locally:   streamlit run app.py
"""

import os
import sqlite3

import pandas as pd
import streamlit as st
from openai import OpenAI

# ----------------------------------------------------------------------
# 1. Page setup
# ----------------------------------------------------------------------
st.set_page_config(page_title="Chat with your data", page_icon="\U0001F4AC")
st.title("Chat with your data")
st.caption("Ask questions in plain English. The app writes SQL, runs it, and answers.")

DB_PATH = "data/mydata.db"          # your SQLite database file
MODEL = "openai/gpt-oss-120b"       # a free Groq model (check console.groq.com/docs/models)

# ----------------------------------------------------------------------
# 2. API key  (works locally via .env, and online via Streamlit secrets)
# ----------------------------------------------------------------------
def get_api_key():
    try:
        return st.secrets["GROQ_API_KEY"]
    except Exception:
        return os.environ.get("GROQ_API_KEY", "")

api_key = get_api_key()
if not api_key:
    st.error("No API key found. See the guide for how to set GROQ_API_KEY.")
    st.stop()

client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=api_key)


# ----------------------------------------------------------------------
# 3. Database helpers
# ----------------------------------------------------------------------
@st.cache_resource
def get_connection():
    # check_same_thread=False lets Streamlit reuse the connection
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def get_schema(conn):
    """Read table/column names plus a few real sample values, so the model
    knows the actual shape of the data (e.g. the date format)."""
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cur.fetchall()]
    lines = []
    for t in tables:
        cur.execute(f"PRAGMA table_info({t});")
        lines.append(f"Table {t}:")
        for c in cur.fetchall():
            name, ctype = c[1], c[2]
            cur.execute(
                f'SELECT DISTINCT "{name}" FROM {t} '
                f'WHERE "{name}" IS NOT NULL LIMIT 3;'
            )
            samples = [str(r[0]) for r in cur.fetchall()]
            eg = f"   e.g. {', '.join(samples)}" if samples else ""
            lines.append(f"  - {name} ({ctype}){eg}")
    return "\n".join(lines)


def ask_llm(prompt, temperature=0):
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
    )
    return resp.choices[0].message.content.strip()


# ----------------------------------------------------------------------
# 4. The core steps
# ----------------------------------------------------------------------
def answer_or_sql(question, schema):
    """Decide whether this is a data question (return SQL) or chit-chat
    (return a short friendly reply prefixed with CHITCHAT:)."""
    prompt = f"""You are a friendly data assistant for a SQLite database.
You are NOT ChatGPT or any other assistant; never claim to be one.

Here is the database schema:
{schema}

Decide what the user's message is:

- If it is a greeting, thanks, small talk, or anything that is NOT a
  question about the data, reply with exactly this format:
  CHITCHAT: <a short, friendly one-line reply>
- If it IS a question about the data, reply with ONLY a SQLite SELECT
  query that answers it. No explanation, no markdown, no semicolon.

User message: {question}"""
    return ask_llm(prompt)


def clean_sql(text):
    sql = text.replace("```sql", "").replace("```", "").strip()
    return sql.rstrip(";")


def explain_result(question, sql, df):
    preview = df.head(20).to_string(index=False)
    prompt = f"""The user asked: "{question}"
You ran this SQL: {sql}
The result table was:
{preview}

Write a short, clear answer to the user's question in 1-3 sentences,
using ONLY the numbers shown in the result table. Do not repeat values,
do not invent numbers. Be friendly and concise."""
    return ask_llm(prompt, temperature=0.2)


def is_safe(sql):
    """Only allow read-only SELECT queries."""
    s = sql.strip().lower()
    return s.startswith("select") or s.startswith("with")


def run_query_with_retry(conn, question, sql, schema):
    """Run the SQL. If it errors, ask the model to fix it, then try once more."""
    try:
        return pd.read_sql_query(sql, conn), sql
    except Exception as e:
        fix_prompt = f"""The following SQLite query failed.

Schema:
{schema}

Question: {question}
SQL: {sql}
Error: {e}

Rewrite the query to fix the error.
Return ONLY the corrected SQL, no explanation, no markdown, no semicolon."""
        fixed = clean_sql(ask_llm(fix_prompt))
        if not is_safe(fixed):
            raise
        return pd.read_sql_query(fixed, conn), fixed


# ----------------------------------------------------------------------
# 5. Chat UI
# ----------------------------------------------------------------------
conn = get_connection()
schema = get_schema(conn)

if "messages" not in st.session_state:
    st.session_state.messages = []

# replay past messages
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m.get("sql"):
            with st.expander("See the SQL"):
                st.code(m["sql"], language="sql")
        if m.get("data") is not None:
            st.dataframe(m["data"])

question = st.chat_input("e.g. What were the top 5 products by revenue?")

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                raw = answer_or_sql(question, schema)

                # small talk -> just reply, no SQL, no table
                if raw.strip().upper().startswith("CHITCHAT:"):
                    reply = raw.split(":", 1)[1].strip()
                    reply = reply or "Hi! Ask me anything about the data."
                    st.markdown(reply)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": reply}
                    )
                else:
                    sql = clean_sql(raw)

                    if not is_safe(sql):
                        answer = "Sorry, I can only run read-only SELECT queries."
                        st.markdown(answer)
                        st.session_state.messages.append(
                            {"role": "assistant", "content": answer}
                        )
                    else:
                        df, sql = run_query_with_retry(conn, question, sql, schema)
                        answer = explain_result(question, sql, df)

                        st.markdown(answer)
                        with st.expander("See the SQL"):
                            st.code(sql, language="sql")
                        st.dataframe(df)

                        st.session_state.messages.append(
                            {
                                "role": "assistant",
                                "content": answer,
                                "sql": sql,
                                "data": df,
                            }
                        )
            except Exception as e:
                msg = f"I could not answer that one. Error: {e}"
                st.markdown(msg)
                st.session_state.messages.append(
                    {"role": "assistant", "content": msg}
                )
