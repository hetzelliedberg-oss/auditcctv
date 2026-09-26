import socket
import json
import time
from miio import Device

ip = "192.168.1.120"
token = "646b7078693339556256484e54633836"

print(f"Connecting to {ip} with token {token}...")
try:
    dev = Device(ip, token)
    info = dev.info()
    print("MIIO Info SUCCESS:")
    print(info)
except Exception as e:
    print(f"MIIO Info Error: {e}")

# Try sending standard chuangmi commands (e.g., miIO.info, get_prop, etc.)
try:
    res = dev.send("miIO.info")
    print("miIO.info response:", res)
except Exception as e:
    print("send miIO.info error:", e)
