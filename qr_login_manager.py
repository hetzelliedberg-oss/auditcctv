import requests
import json
import time
import sys

sys.stdout.reconfigure(encoding='utf-8')

session = requests.Session()
url = "https://account.xiaomi.com/longPolling/loginUrl?_qrsize=240&qs=%3Fsid%3Dxiaomiio%26_json%3Dtrue&sid=xiaomiio&_json=true"
r = session.get(url)
d = json.loads(r.text.replace("&&&START&&&", ""))
qr_url = d.get("qr")
lp_url = d.get("lp")

print("=" * 60)
print("QR Code Image URL:", qr_url)
print("Long polling URL:", lp_url)
print("=" * 60)

with open("data/qr_login_info.json", "w", encoding="utf-8") as f:
    json.dump({"qr_url": qr_url, "lp_url": lp_url, "status": "WAITING_SCAN", "timestamp": time.time()}, f, indent=2)
print("Saved QR login info to data/qr_login_info.json")
