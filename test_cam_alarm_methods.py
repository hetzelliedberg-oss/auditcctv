from enable_motion_record import call_miio

test_methods = [
    ("set_alarm", ["on"]),
    ("set_arm", ["on"]),
    ("set_nas_enable", [1]),
    ("get_prop", ["alarm_status", "alarm_motion", "alarm_push", "alarm_time", "alarm_sound"])
]

for m, p in test_methods:
    print(f"Calling {m}({p}) -> {call_miio(m, p)}")
