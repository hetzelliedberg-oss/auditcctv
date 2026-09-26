import json
from query_devices_encrypted import execute_api_call

all_dids = [
    "263288748", # ห้องหลังบ้าน
    "262682234", # หน้าบ้าน 1
    "262681994", # ออฟฟิศ
    "134676647", # ห้องนอน
    "259072949", # ห้องนอน 2
    "264112853", # โลตัสเฮียแบงค์
    "264116706", # โลตัสเฮียแบงค์ 2
    "394098206", # ในห้องนอน หน้าคอม
    "264111350"  # ในห้อง (แชร์)
]

print("Fetching details for all DIDs...")
res = execute_api_call("sg", "/v2/device/batch_dev_detail", {
    "data": json.dumps({"dids": all_dids})
})

device_details = []
if res and res.get("code") == 0:
    dev_dict = res.get("result", {})
    for did, d in dev_dict.items():
        print(f"📹 DID: {did} | Name: {d.get('name')} | Model: {d.get('model')} | Online: {d.get('isOnline')} | IP: {d.get('localip')}")
        device_details.append(d)
else:
    # Try /v2/home/device_list or single info
    print("Trying /v2/device/blt_get_beaconkey or alternative...")

with open("data/user_all_real_cameras.json", "w", encoding="utf-8") as f:
    json.dump(res, f, indent=2, ensure_ascii=False)

print("Saved to data/user_all_real_cameras.json")
