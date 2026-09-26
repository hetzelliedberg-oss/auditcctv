import os
import glob
import sqlite3

cookie_paths = glob.glob(os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data\**\Network\Cookies"), recursive=True)
for cp in cookie_paths:
    try:
        conn = sqlite3.connect(f"file:{cp}?mode=ro", uri=True)
        c = conn.cursor()
        c.execute("SELECT host_key, name FROM cookies WHERE host_key LIKE '%huggingface%'")
        rows = c.fetchall()
        if rows:
            print(f"Found {len(rows)} HF cookies in {cp}:")
            for r in rows:
                print(" ", r)
        conn.close()
    except Exception as e:
        pass
