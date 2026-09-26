import os
import sqlite3
import shutil

user_data = os.path.expanduser(r"~\AppData\Local\Google\Chrome\User Data")
profiles = [d for d in os.listdir(user_data) if 'Profile' in d or d == 'Default']

for p in profiles:
    hist_file = os.path.join(user_data, p, "History")
    if os.path.exists(hist_file):
        try:
            shutil.copy2(hist_file, "temp_hist.db")
            conn = sqlite3.connect("temp_hist.db")
            c = conn.cursor()
            c.execute("SELECT url, title FROM urls WHERE url LIKE '%xiaomi.com%' ORDER BY last_visit_time DESC LIMIT 1")
            row = c.fetchone()
            if row:
                print(f"🎯 FOUND IT! Profile: {p}")
                print(f"   URL: {row[0]}")
            conn.close()
            os.remove("temp_hist.db")
        except Exception as e:
            pass
