import requests
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

session = requests.Session()
url = "https://account.xiaomi.com/longPolling/loginUrl?_qrsize=240&qs=%3Fsid%3Dxiaomiio%26_json%3Dtrue&sid=xiaomiio&_json=true"
r = session.get(url)
print("QR Code Login API response:")
print(r.text)
