import requests
import hashlib
import json

session = requests.Session()
# step 1
r1 = session.get("https://account.xiaomi.com/pass/serviceLogin?sid=xiaomiio&_json=true")
data1 = json.loads(r1.text.replace("&&&START&&&", ""))
sign = data1.get("_sign")

# step 2
url = "https://account.xiaomi.com/pass/serviceLoginAuth2"
for user in ["+66830737979", "0830737979", "snook004@gmail.com"]:
    post_data = {
        'sid': "xiaomiio",
        'hash': hashlib.md5("P*awin123123".encode()).hexdigest().upper(),
        'callback': "https://sts.api.io.mi.com/sts",
        'qs': '%3Fsid%3Dxiaomiio%26_json%3Dtrue',
        'user': user,
        '_json': 'true',
        '_sign': sign
    }
    r2 = session.post(url, data=post_data)
    d2 = json.loads(r2.text.replace("&&&START&&&", ""))
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    print(f"User: {user} -> Code: {d2.get('code')}, Desc: {d2.get('desc')}, NotificationUrl: {d2.get('notificationUrl')}")
