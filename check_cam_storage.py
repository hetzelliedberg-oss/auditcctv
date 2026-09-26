from inspect_cam_props import call_miio

print("=== Checking Camera Properties & Status ===")
props_to_check = [
    "power",
    "motion_record",
    "night_mode",
    "light",
    "flip",
    "sdcard_status",
    "sdcard_freesize",
    "sdcard_totalsize",
    "nas_state",
    "time_watermark",
    "full_color",
    "wdr"
]

for p in props_to_check:
    res = call_miio("get_prop", [p])
    print(f"Prop '{p}' -> {res.get('result') if 'result' in res else res}")

# Check if we can turn on motion_record if it is off
# In chuangmi camera, set_motion_record or set_alarm
print("\n=== Testing motion settings ===")
res_m = call_miio("get_prop", ["motion_record"])
print("Current motion_record:", res_m)
