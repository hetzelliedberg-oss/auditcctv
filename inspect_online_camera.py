import json
from query_devices_encrypted import execute_api_call

res = execute_api_call("sg", "/home/device_list", {
    "data": json.dumps({"getVirtualModel": False, "getHuamiDevices": 0})
})

if res and res.get("code") == 0:
    devs = res.get("result", {}).get("list", [])
    for d in devs:
        if d.get("did") == "263288748":
            print("=== Full details for หลังบ้าน 1 (Online Camera) ===")
            print(json.dumps(d, indent=2, ensure_ascii=False))
            break
