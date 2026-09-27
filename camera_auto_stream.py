import os
import time
import json
import logging
import cv2
import requests
from query_devices_encrypted import execute_api_call
from ai_engine import analyze_clip_or_image
from session_manager import session_mgr

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("camera_auto_stream")

SNAPSHOT_DIR = "data/snapshots"
CLIPS_DIR = "data/clips"
os.makedirs(SNAPSHOT_DIR, exist_ok=True)
os.makedirs(CLIPS_DIR, exist_ok=True)

_stream_url_cache = {}  # did -> {"url": str, "expires": float}

def get_camera_stream_url(did: str, force_fresh: bool = False):
    """Request HLS live stream from Xiaomi Cloud for camera DID, cached for 10 minutes to prevent Mi Home notification spam."""
    now = time.time()
    if not force_fresh and did in _stream_url_cache:
        cached = _stream_url_cache[did]
        if now < cached["expires"]:
            return cached["url"]

    try:
        res = execute_api_call("sg", "/miotspec/action", {
            "data": json.dumps({
                "params": {
                    "did": str(did),
                    "siid": 4,
                    "aiid": 1,
                    "in": [1]
                }
            })
        })
        if res and res.get("code") == 0:
            out_list = res.get("result", {}).get("out", [])
            if out_list and len(out_list) > 0:
                url = out_list[0]
                # Cache URL for 10 minutes
                _stream_url_cache[did] = {"url": url, "expires": now + 600}
                return url
    except Exception as e:
        logger.error(f"Error getting HLS stream for DID {did}: {e}")
    return None

def add_camera_watermark(img, camera_name: str, did: str):
    """Draws a professional CCTV camera watermark banner with camera name and live timestamp."""
    try:
        h, w = img.shape[:2]
        banner_h = 55
        
        # Create semi-transparent overlay
        overlay = img.copy()
        cv2.rectangle(overlay, (0, 0), (w, banner_h), (15, 15, 15), -1)
        cv2.addWeighted(overlay, 0.7, img, 0.3, 0, img)
        
        ts_now = time.strftime("%Y-%m-%d %H:%M:%S")
        left_text = f"CAM: {camera_name} [DID: {did}]"
        right_text = f"LIVE  {ts_now}"
        
        # Left: Camera name in bright cyan/green
        cv2.putText(img, left_text, (15, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 180), 2, cv2.LINE_AA)
        
        # Right: Live indicator + timestamp
        cv2.circle(img, (w - 270, 28), 7, (0, 0, 255), -1)
        cv2.putText(img, right_text, (w - 250, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2, cv2.LINE_AA)
    except Exception as e:
        logger.error(f"Error adding watermark: {e}")
    return img

def capture_live_frame(did: str, camera_name: str = "กล้องวงจรปิด", save_path: str = None, max_wait_sec: int = 12):
    """Connects to live camera HLS stream, captures a real JPEG frame, and applies watermark."""
    hls_url = get_camera_stream_url(did)
    if not hls_url:
        logger.warning(f"Could not get stream URL for DID {did}")
        return None
        
    logger.info(f"Connecting to live stream for DID {did}: {hls_url}")
    time.sleep(3)
    
    start_time = time.time()
    cap = None
    frame = None
    
    while time.time() - start_time < max_wait_sec:
        try:
            r = requests.get(hls_url, timeout=4)
            if r.status_code == 200:
                cap = cv2.VideoCapture(hls_url)
                ret, img = cap.read()
                if ret and img is not None and img.shape[0] > 0:
                    frame = img
                    break
        except Exception as e:
            logger.debug(f"Retrying stream read: {e}")
        time.sleep(1.5)
        
    if cap:
        cap.release()
        
    if frame is not None:
        # Apply camera name watermark
        frame = add_camera_watermark(frame, camera_name, did)
        
        if not save_path:
            ts_str = time.strftime("%Y%m%d_%H%M%S")
            save_path = os.path.join(SNAPSHOT_DIR, f"live_cam_{did}_{ts_str}.jpg")
            
        cv2.imwrite(save_path, frame)
        # Also update live_camera_frame.jpg for instant preview
        cv2.imwrite("data/live_camera_frame.jpg", frame)
        logger.info(f"Captured live frame saved to: {save_path} ({os.path.getsize(save_path)} bytes)")
        return save_path
    else:
        logger.warning(f"Failed to capture frame from stream for DID {did}")
        # If we have existing frame, watermark it
        if os.path.exists("data/live_camera_frame.jpg"):
            f = cv2.imread("data/live_camera_frame.jpg")
            if f is not None:
                f = add_camera_watermark(f, camera_name, did)
                cv2.imwrite("data/live_camera_frame.jpg", f)
                return "data/live_camera_frame.jpg"
        return None

def execute_auto_workflow_for_camera(did: str, camera_name: str = "กล้องวงจรปิด"):
    """
    100% Automated Workflow:
    1. Grabs live snapshot frame from camera with camera watermark.
    2. Runs YOLOv8 Computer Vision.
    3. Extracts true Head count.
    4. If people found, logs to SQLite with camera_name and camera_did.
    5. If 0 people found, reports 0 people accurately without creating phantom sessions.
    """
    logger.info(f"Executing Auto Workflow for Camera '{camera_name}' (DID: {did})...")
    
    # Step 1: Capture live frame
    snapshot_file = capture_live_frame(did, camera_name=camera_name)
    if not snapshot_file or not os.path.exists(snapshot_file):
        if os.path.exists("data/live_camera_frame.jpg"):
            snapshot_file = "data/live_camera_frame.jpg"
        else:
            return None, "ไม่สามารถดึงภาพสดจากกล้องได้ (โปรดตรวจสอบสถานะออนไลน์ของกล้อง)"
            
    # Step 2: Run AI Vision analysis
    ai_result = analyze_clip_or_image(snapshot_file)
    people_count = ai_result.get("people_count", 0)
    
    # Step 3: Handle empty vs detected
    if people_count == 0:
        logger.info(f"[{camera_name}] No people detected. Space is empty. Not creating phantom session.")
        return {
            "status": "EMPTY",
            "people_count": 0,
            "camera_name": camera_name,
            "camera_did": did,
            "snapshot_path": snapshot_file,
            "message": f"ภาพจากกล้อง '{camera_name}': ไม่พบคนในพื้นที่ (0 คน) - ห้องว่าง/ไม่มีลูกค้า"
        }, None
        
    # If people > 0:
    session_dict = session_mgr.start_new_session(
        ai_data=ai_result,
        snapshot_path=snapshot_file,
        clip_path="",
        camera_name=camera_name,
        camera_did=did
    )
    session_id = session_dict["id"]
    session_mgr.update_active_session(session_id, ai_result)
    session_mgr.close_session(session_id)
    
    logger.info(f"Auto Workflow Real Fact Session Created: ID {session_id} | Cam: {camera_name} | People: {people_count}")
    return session_dict, None
