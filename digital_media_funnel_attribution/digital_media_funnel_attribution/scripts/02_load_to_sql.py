"""
02_load_to_sql.py
Loads the CSVs in ./data into a local SQLite database (media_funnel.db).

Run:    python 02_load_to_sql.py
Output: media_funnel.db (in the project root)
"""

import os
import sqlite3

import pandas as pd

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
DB_PATH = os.path.join(BASE_DIR, "media_funnel.db")
DATA_DIR = os.path.join(BASE_DIR, "data")

if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

conn = sqlite3.connect(DB_PATH)

tables = {
    "customers": "customers.csv",
    "channels": "channels.csv",
    "funnel_exposures": "funnel_exposures.csv",
}

for table, filename in tables.items():
    df = pd.read_csv(os.path.join(DATA_DIR, filename))
    df.to_sql(table, conn, if_exists="replace", index=False)
    print(f"Loaded {table:<20} {len(df):>7,} rows")

cur = conn.cursor()
cur.execute("CREATE INDEX IF NOT EXISTS idx_exp_customer ON funnel_exposures(customer_id)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_exp_channel ON funnel_exposures(channel_name)")
conn.commit()
conn.close()

print(f"\nDatabase ready at {DB_PATH}")
