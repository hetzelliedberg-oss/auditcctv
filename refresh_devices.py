import json
from mi_cloud_client import MiCloudClient

client = MiCloudClient()
devs = client.get_device_list()
print(f"Total devices found: {len(devs)}")
cams = [d for d in devs if "camera" in d.get("model", "").lower()]
for c in cams:
    print(f"CAMERA: {c.get('name')} | DID: {c.get('did')} | Online: {c.get('isOnline')} | IP: {c.get('localip')}")

with open("data/all_real_devices.json", "w", encoding="utf-8") as f:
    json.dump(devs, f, ensure_ascii=False, indent=2)
print("Updated data/all_real_devices.json successfully!")
