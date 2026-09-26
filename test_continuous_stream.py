import time
import cv2
import requests
from camera_auto_stream import get_camera_stream_url

did = "263288748"
print(f"Requesting stream for DID {did}...")
hls_url = get_camera_stream_url(did)
print(f"HLS Stream URL: {hls_url}")

# Wait for stream pipeline
time.sleep(3)

print("Opening VideoCapture on HLS stream...")
cap = cv2.VideoCapture(hls_url)
print("isOpened:", cap.isOpened())

for i in range(10):
    ret, frame = cap.read()
    if ret:
        print(f"Frame {i+1} read successfully! shape: {frame.shape}")
        cv2.imwrite("data/stream_test_frame.jpg", frame)
    else:
        print(f"Frame {i+1} failed to read.")
    time.sleep(0.5)

cap.release()
print("Test completed.")
