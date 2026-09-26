import requests
import json
import hashlib

session = requests.Session()
r1 = session.get("https://account.xiaomi.com/pass/serviceLogin?sid=xiaomiio&_json=true")
data1 = json.loads(r1.text.replace("&&&START&&&", ""))
sign = data1.get("_sign")

url = "https://account.xiaomi.com/pass/serviceLoginAuth2"
post_data = {
    'sid': "xiaomiio",
    'hash': hashlib.md5("P*awin123123".encode()).hexdigest().upper(),
    'callback': "https://sts.api.io.mi.com/sts",
    'qs': '%3Fsid%3Dxiaomiio%26_json%3Dtrue',
    'user': "+66830737979",
    '_json': 'true',
    '_sign': sign
}
r2 = session.post(url, data=post_data)
d2 = json.loads(r2.text.replace("&&&START&&&", ""))
notif_url = d2.get("notificationUrl")
print("Notification URL:", notif_url)
