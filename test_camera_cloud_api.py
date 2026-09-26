import json
import requests
from query_devices_encrypted import execute_api_call

# Let's test endpoints for getting device info and camera events
dids = [
    "263288748", # ห้องหลังบ้าน (User's own camera in Lopburi)
    "262682234", # หน้าบ้าน 1
    "262681994", # ออฟฟิศ
    "394098206", # ในห้องนอน หน้าคอม
    "264111350"  # ในห้อง (แชร์จาก 6408821679)
]

print("=== 1. Testing /home/device_list ===")
res1 = execute_api_call("sg", "/home/device_list", {
    "data": json.dumps({"getVirtualModel": False, "getHuamiDevices": 0})
})
print("Endpoint /home/device_list result:")
if res1:
    print("Code:", res1.get("code"))
    list_devs = res1.get("result", {}).get("list", [])
    print(f"Devices found in /home/device_list: {len(list_devs)}")
    for d in list_devs:
        print(f"  - DID: {d.get('did')}, Name: {d.get('name')}, Model: {d.get('model')}, Online: {d.get('isOnline')}")
else:
    print("Failed or None")

print("\n=== 2. Testing /v2/device/batch_dev_detail ===")
res2 = execute_api_call("sg", "/device/batchdevicedatas", {
    "data": json.dumps([{"did": did, "props": ["prop.power", "prop.motion", "prop.alarm"]} for did in dids])
})
print("Result /device/batchdevicedatas:", res2)

print("\n=== 3. Testing Camera Alarm / Motion Event List ===")
# Xiaomi Camera alarm endpoints:
# /v2/device/get_alarm_list
# /camera/getevent
# /common/app/get/v2/eventlist
# /v2/device/get_event
for endpoint in [
    "/v2/device/get_alarm_list",
    "/v2/device/get_event",
    "/camera/getevent",
    "/common/app/get/v2/eventlist",
    "/v2/camera/get_event_list",
    "/v2/homeroom/get_room_history_event",
    "/v2/camera/get_alarm_record"
]:
    try:
        res = execute_api_call("sg", endpoint, {
            "data": json.dumps({
                "did": "263288748",
                "limit": 10,
                "timestamp": 0
            })
        })
        print(f"Endpoint {endpoint} -> code: {res.get('code') if res else 'None'}, message: {res.get('message') if res else ''}")
        if res and res.get("code") == 0:
            print("SUCCESS! Result:", json.dumps(res.get("result"), ensure_ascii=False)[:300])
    except Exception as e:
        print(f"Endpoint {endpoint} error: {e}")
