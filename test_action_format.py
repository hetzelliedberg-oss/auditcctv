import json
from query_devices_encrypted import execute_api_call

did = "263288748"

# 1. Single dict in params
res1 = execute_api_call("sg", "/miotspec/action", {
    "data": json.dumps({
        "params": {
            "did": did,
            "siid": 3,
            "aiid": 1,
            "in": [1]
        }
    })
})
print("Result with params dict:", res1)

# 2. List in params
res2 = execute_api_call("sg", "/miotspec/action", {
    "data": json.dumps({
        "params": [{
            "did": did,
            "siid": 3,
            "aiid": 1,
            "in": [1]
        }]
    })
})
print("Result with params list:", res2)

# 3. Google stream
res3 = execute_api_call("sg", "/miotspec/action", {
    "data": json.dumps({
        "params": {
            "did": did,
            "siid": 4,
            "aiid": 1,
            "in": [1]
        }
    })
})
print("Result Google stream:", res3)
