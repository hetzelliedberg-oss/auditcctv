import sys
from micloud import MiCloud

user = "snook004@gmail.com"
password = "P*awin123123"

print("Attempting login to Xiaomi Cloud...")
mc = MiCloud(user, password)
success = mc.login()
print(f"Login success: {success}")

if success:
    servers = ["sg", "cn", "de", "i2", "us", "ru"]
    for s in servers:
        print(f"\nChecking server: {s}")
        try:
            devices = mc.get_devices(country=s)
            print(f"Found {len(devices)} devices in {s}")
            for d in devices:
                print(f"  Name: {d.get('name')}, Model: {d.get('model')}, DID: {d.get('did')}, Token: {d.get('token')}")
        except Exception as e:
            print(f"  Error on server {s}: {e}")
else:
    print("Login failed. Check credentials or 2FA required.")
