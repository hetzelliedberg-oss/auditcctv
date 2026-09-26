import json
from query_devices_encrypted import execute_api_call

# Fetch own and shared devices
print("Fetching device lists from Xiaomi Cloud...")
all_devs = []

# 1. Standard device list
res = execute_api_call("sg", "/home/device_list", {
    "data": json.dumps({"getVirtualModel": False, "getHuamiDevices": 0})
})
if res and res.get("code") == 0:
    devs = res.get("result", {}).get("list", [])
    print(f"Found {len(devs)} devices in own account.")
    all_devs.extend(devs)

# 2. Check shared devices
res_share = execute_api_call("sg", "/v2/home/home_device_list", {
    "data": json.dumps({
        "home_owner": 6408821679,
        "home_id": "43001035837",
        "limit": 200,
        "get_split_device": True,
        "support_smart_home": True
    })
})
if res_share and res_share.get("code") == 0:
    s_devs = res_share.get("result", {}).get("device_list", [])
    print(f"Found {len(s_devs)} shared devices from 6408821679.")
    all_devs.extend(s_devs)

# Deduplicate by DID
unique_devs = {}
for d in all_devs:
    unique_devs[d["did"]] = d

device_list = list(unique_devs.values())

with open("data/all_real_devices.json", "w", encoding="utf-8") as f:
    json.dump(device_list, f, indent=2, ensure_ascii=False)

print(f"\nSaved {len(device_list)} real devices to data/all_real_devices.json:")
for d in device_list:
    status = "🟢 ONLINE" if d.get("isOnline") else "⚪ offline"
    print(f"  {status} | DID: {d.get('did')} | Name: {d.get('name')} | IP: {d.get('localip', 'N/A')} | Token: {d.get('token', '')[:8]}... | Model: {d.get('model')}")
