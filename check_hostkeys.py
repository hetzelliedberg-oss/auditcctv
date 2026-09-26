import os
import sqlite3

user_data = os.path.expanduser(r"~\AppData\Local\Google\Chrome\User Data")
profiles = [d for d in os.listdir(user_data) if 'Profile' in d or d == 'Default']

for p in profiles:
    cookie_db = os.path.join(user_data, p, "Network", "Cookies")
    if not os.path.exists(cookie_db):
        continue
    try:
        conn = sqlite3.connect(cookie_db)
        cursor = conn.cursor()
        cursor.execute("SELECT host_key FROM cookies WHERE host_key LIKE '%mi%'")
        rows = cursor.fetchall()
        if rows:
            print(f"Profile {p}: {set([r[0] for r in rows])}")
        conn.close()
    except Exception as e:
        pass
