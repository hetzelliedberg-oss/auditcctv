import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "data", "store_sessions.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("DELETE FROM sessions")
conn.commit()
conn.close()
print("All mock data cleared! Database is completely clean and ready for real data.")
