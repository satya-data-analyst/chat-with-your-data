"""
Turn one of your CSV files into a SQLite database the app can read.

Usage:
    python load_data.py path/to/your_file.csv mytable

This creates  data/mydata.db  with a table called 'mytable'.
"""

import os
import sqlite3
import sys

import pandas as pd


def parse_dates(series):
    """Normalise mixed date formats (e.g. '1/1/2011' and '13-01-2011') to ISO."""
    out = pd.Series(pd.NaT, index=series.index)
    for fmt in ("%m/%d/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y", "%m-%d-%Y"):
        parsed = pd.to_datetime(series, format=fmt, errors="coerce")
        out = out.fillna(parsed)
    return out.dt.strftime("%Y-%m-%d")


def main():
    if len(sys.argv) != 3:
        print("Usage: python load_data.py <csv_file> <table_name>")
        sys.exit(1)

    csv_path, table_name = sys.argv[1], sys.argv[2]

    os.makedirs("data", exist_ok=True)

    df = pd.read_csv(csv_path)
    # tidy the column names so SQL is easier to write
    df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace(r"[^0-9a-zA-Z_]", "", regex=True)
    )

    # normalise any date-like column to ISO so SQL date functions work
    for col in df.columns:
        if "date" in col:
            before = df[col].head(2).tolist()
            df[col] = parse_dates(df[col])
            after = df[col].head(2).tolist()
            print(f"Date column '{col}': {before} -> {after}")

    conn = sqlite3.connect("data/mydata.db")
    df.to_sql(table_name, conn, if_exists="replace", index=False)
    conn.close()

    print(f"Loaded {len(df)} rows into table '{table_name}' in data/mydata.db")
    print("Columns:", ", ".join(df.columns))


if __name__ == "__main__":
    main()
