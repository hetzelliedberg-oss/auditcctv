import browser_cookie3
import requests
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

print("Fetching cookies from Chrome for xiaomi.com...")
try:
    cj = browser_cookie3.chrome(domain_name="xiaomi.com")
    cookies = {c.name: c.value for c in cj}
    print(f"Found {len(cookies)} cookies for xiaomi.com:")
    for k in cookies:
        print(f"  {k}: {cookies[k][:15]}...")
        
    with open("data/chrome_xiaomi_cookies.json", "w", encoding="utf-8") as f:
        json.dump(cookies, f, indent=2)
    print("Saved cookies to data/chrome_xiaomi_cookies.json")
except Exception as e:
    print(f"Error reading cookies: {e}")
