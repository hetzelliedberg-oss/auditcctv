import requests
import json
import hashlib
import sys

sys.stdout.reconfigure(encoding='utf-8')

session = requests.Session()
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
print("Keys in d2:", list(d2.keys()))
for k, v in d2.items():
    if k != "context":
        print(f"  {k}: {v}")
