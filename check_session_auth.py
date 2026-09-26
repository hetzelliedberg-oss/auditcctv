import requests
import json
import hashlib
import sys

sys.stdout.reconfigure(encoding='utf-8')

session = requests.Session()
# Check if we can complete login now that account identity is confirmed
r1 = session.get("https://account.xiaomi.com/pass/serviceLogin?sid=xiaomiio&_json=true")
d1 = json.loads(r1.text.replace("&&&START&&&", ""))
sign = d1.get("_sign")

post_data = {
    'sid': "xiaomiio",
    'hash': hashlib.md5("P*awin123123".encode()).hexdigest().upper(),
    'callback': "https://sts.api.io.mi.com/sts",
    'qs': '%3Fsid%3Dxiaomiio%26_json%3Dtrue',
    'user': "+66830737979",
    '_json': 'true',
    '_sign': sign
}
r2 = session.post("https://account.xiaomi.com/pass/serviceLoginAuth2", data=post_data)
d2 = json.loads(r2.text.replace("&&&START&&&", ""))
print("Auth2 Status:", d2.get("code"), d2.get("desc"))
print("Keys:", list(d2.keys()))
if "location" in d2 and d2["location"]:
    print("Location found! Logging in...")
    r3 = session.get(d2["location"])
    print("Cookies after STS:", session.cookies.get_dict())
    with open("data/xiaomi_cloud_session.json", "w") as f:
        json.dump(session.cookies.get_dict(), f, indent=2)
    print("SUCCESS! Captured session to data/xiaomi_cloud_session.json")
else:
    print("Notification URL still required:", d2.get("notificationUrl")[:60] if d2.get("notificationUrl") else None)
