import sqlite3

conn = sqlite3.connect("data/mydata.db")
cur = conn.cursor()

print("Total rows:", cur.execute("SELECT COUNT(*) FROM superstore").fetchone()[0])
print()
print("First 10 order_date values:")
for r in cur.execute("SELECT order_date FROM superstore LIMIT 10"):
    print("   ", repr(r[0]))
print()
print("Rows containing a slash:",
      cur.execute("SELECT COUNT(*) FROM superstore WHERE order_date LIKE '%/%'").fetchone()[0])
print("Rows WITHOUT a slash:",
      cur.execute("SELECT COUNT(*) FROM superstore WHERE order_date NOT LIKE '%/%'").fetchone()[0])
print()
print("Sample of rows without a slash:")
for r in cur.execute(
        "SELECT DISTINCT order_date FROM superstore WHERE order_date NOT LIKE '%/%' LIMIT 10"):
    print("   ", repr(r[0]))
