import json
from query_devices_encrypted import execute_api_call
from inspect_cam_props import call_miio

did = "263288748" # Online camera

print("=== 1. Testing Cloud MIoT Action /miotspec/action ===")
# Try Alexa stream (siid 3, aiid 1)
for video_attr in [1, 0, 2]:
    print(f"\nCalling Cloud Action siid:3, aiid:1 with in:[{video_attr}]...")
    res = execute_api_call("sg", "/miotspec/action", {
        "data": json.dumps({
            "did": did,
            "siid": 3,
            "aiid": 1,
            "in": [video_attr]
        })
    })
    print("Cloud Alexa stream result:", res)
    if res and res.get("code") == 0:
        break

# Try Google Home stream (siid 4, aiid 1)
print(f"\nCalling Cloud Action siid:4, aiid:1 (Google Home HLS stream)...")
res_google = execute_api_call("sg", "/miotspec/action", {
    "data": json.dumps({
        "did": did,
        "siid": 4,
        "aiid": 1,
        "in": [1]
    })
})
print("Cloud Google stream result:", res_google)

print("\n=== 2. Testing Local MIIO Action ===")
res_local = call_miio("action", {
    "did": did,
    "siid": 3,
    "aiid": 1,
    "in": [1]
})
print("Local Alexa action result:", res_local)

res_local_g = call_miio("action", {
    "did": did,
    "siid": 4,
    "aiid": 1,
    "in": [1]
})
print("Local Google action result:", res_local_g)
