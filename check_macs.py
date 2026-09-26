import subprocess
import re

macs = {
    "192.168.1.108": "50-ec-50-30-cd-02",
    "192.168.1.120": "50-ec-50-30-bc-85",
    "192.168.1.102": "50-0f-f5-81-5d-c0",
    "192.168.1.119": "50-0f-f5-81-5d-c0",
    "192.168.1.135": "50-0f-f5-81-5d-c0",
    "192.168.1.10":  "84-7a-b6-4a-b8-dd",
    "192.168.1.101": "c8-12-0b-e7-6c-36",
    "192.168.1.109": "00-0c-43-a5-eb-34",
    "192.168.1.111": "68-27-37-87-a6-bf",
    "192.168.1.112": "1c-bf-ce-d6-d8-e0",
    "192.168.1.116": "a0-d0-5b-94-4d-a3",
    "192.168.1.126": "84-7a-b6-4a-b8-dd",
}

print("Checking Xiaomi MACs:")
for ip, mac in macs.items():
    prefix = mac[:8].replace("-", ":").upper()
    if prefix == "50:EC:50":
        print(f"  [XIAOMI DEVICE] IP: {ip} | MAC: {mac}")
