import os
import time

user_data = os.path.expanduser(r"~\AppData\Local\Google\Chrome\User Data")
profiles = [d for d in os.listdir(user_data) if 'Profile' in d or d == 'Default']

now = time.time()
recent_profiles = []
for p in profiles:
    cookie_path = os.path.join(user_data, p, "Network", "Cookies")
    if os.path.exists(cookie_path):
        mtime = os.path.getmtime(cookie_path)
        diff = now - mtime
        if diff < 1800: # modified in last 30 mins
            recent_profiles.append((p, diff, cookie_path))

recent_profiles.sort(key=lambda x: x[1])
print("Recent active profiles (modified in last 30m):")
for p, diff, path in recent_profiles:
    print(f"  {p}: modified {int(diff)}s ago ({path})")
