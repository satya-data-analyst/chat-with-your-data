import pandas as pd

df = pd.read_csv("superstore.csv")
col = [c for c in df.columns if "date" in c.lower()][0]
s = df[col].astype(str)

slash = s[s.str.contains("/")]
print("Slash rows:", len(slash))
print("First numbers in slash dates:", sorted({int(x.split("/")[0]) for x in slash}))

hyphen = s[s.str.contains("-")]
print("Hyphen rows:", len(hyphen))
print("First numbers in hyphen dates:", sorted({int(x.split("-")[0]) for x in hyphen}))
