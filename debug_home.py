import json
from query_devices_encrypted import execute_api_call

res = execute_api_call("sg", "/v2/homeroom/gethome", {
    "data": json.dumps({"fg": True, "fetch_share": True, "fetch_share_dev": True, "limit": 300, "app_ver": 7})
})

print("Full Home Response SG:")
print(json.dumps(res, indent=2, ensure_ascii=False))
