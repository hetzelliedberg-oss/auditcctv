import urllib.request
import json

ouis = ["50:0F:F5", "84:7A:B6", "C8:12:0B", "1C:BF:CE", "A0:D0:5B", "00:0C:43", "68:27:37"]
for oui in ouis:
    try:
        url = f"https://api.macvendors.com/{oui}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=2)
        print(f"{oui} -> {resp.read().decode('utf-8')}")
    except Exception as e:
        print(f"{oui} -> {e}")
