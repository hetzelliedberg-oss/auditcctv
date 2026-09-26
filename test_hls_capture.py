import time
import requests
import cv2
import json
from query_devices_encrypted import execute_api_call

did = "263288748"
print("Requesting fresh HLS stream from Xiaomi Cloud...")
res = execute_api_call("sg", "/miotspec/action", {
    "data": json.dumps({
        "params": {
            "did": did,
            "siid": 4,
            "aiid": 1,
            "in": [1]
        }
    })
})

if res and res.get("code") == 0:
    hls_url = res["result"]["out"][0]
    print(f"Got HLS URL: {hls_url}")
    print("Waiting 5 seconds for transcoder pipeline to warm up...")
    time.sleep(5)
    
    for attempt in range(6):
        try:
            r = requests.get(hls_url, timeout=5)
            print(f"Attempt {attempt+1}: Status {r.status_code}")
            if r.status_code == 200:
                print("🎉 M3U8 STREAM READY!")
                print(r.text)
                
                # Test OpenCV reading frame from this HLS stream
                cap = cv2.VideoCapture(hls_url)
                ret, frame = cap.read()
                if ret:
                    cv2.imwrite("data/live_camera_frame.jpg", frame)
                    print("🚀 SUCCESSFULLY CAPTURED LIVE FRAME from camera to data/live_camera_frame.jpg!")
                cap.release()
                break
        except Exception as e:
            print("Request error:", e)
        time.sleep(2)
