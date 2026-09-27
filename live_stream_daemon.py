"""
Multi-Camera Real-Time AI Stream Daemon & Cross-Camera Fact Engine
- Auto-syncs all online Xiaomi cameras from Cloud (หลังบ้าน 1, กล้อง 2, and Video camera2 when online)
- Temporal Majority Smoothing: Eliminates single-frame ghost/false positive person spikes (e.g. office chairs)
- Cross-Camera Spatial-Temporal Fusion: Merges visits across multiple cameras into 1 customer party
- Multi-Snapshot Gallery: Captures entry, interval (every 4-5s), and exit shots
- Native H.264 MP4 event recording via PyAV
- Retail Staff Filtering: Excludes stationery staff behind counters
- Strict Fact recording (0 pants touched, 0 fitting room unless verified)
"""
import os
import sys
import time
import threading
import logging
import json
from datetime import datetime
from collections import deque
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from ultralytics import YOLO

from camera_auto_stream import get_camera_stream_url
from session_manager import session_mgr
from video_recorder import H264VideoWriter
from device_sync import get_online_cameras
from telegram_alert import send_telegram_alert
from time_utils import now_bkk, bkk_str, bkk_time_str
from staff_matcher import staff_matcher

sys.stdout.reconfigure(encoding='utf-8')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("stream_daemon")

SNAPSHOT_DIR = "data/snapshots"
CLIPS_DIR = "data/clips"
os.makedirs(SNAPSHOT_DIR, exist_ok=True)
os.makedirs(CLIPS_DIR, exist_ok=True)

LOCAL_FONT = os.path.join(os.path.dirname(__file__), "data", "fonts", "tahoma.ttf")
FONT_PATHS = [LOCAL_FONT, "C:/Windows/Fonts/tahoma.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
THAI_FONT = None
for fp in FONT_PATHS:
    if os.path.exists(fp):
        try:
            THAI_FONT = ImageFont.truetype(fp, 18)
            break
        except Exception:
            pass

def add_thai_watermark(frame, camera_name: str, did: str, person_count: int = 0, role: str = "CUSTOMER"):
    try:
        h, w = frame.shape[:2]
        banner_h = 46
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, banner_h), (12, 12, 12), -1)
        cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

        pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_img)
        ts_now = bkk_str()

        left_text = f"📹 {camera_name} [DID: {did}]"
        if role == "STAFF":
            status_text = f"🧑‍💼 น้องพนักงาน (ประจำเคาน์เตอร์) | ไม่มีลูกค้า | LIVE {ts_now}"
            status_color = (100, 200, 255)
        elif role == "CUSTOMER" and person_count > 0:
            status_text = f"🚨 ลูกค้าเข้าชม: {person_count} คน | LIVE {ts_now}"
            status_color = (255, 60, 60)
        else:
            status_text = f"● LIVE (ร้านว่าง) {ts_now}"
            status_color = (255, 255, 255)

        if THAI_FONT:
            draw.text((12, 11), left_text, font=THAI_FONT, fill=(0, 255, 180))
            draw.text((w - 420, 11), status_text, font=THAI_FONT, fill=status_color)
            return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        else:
            cv2.putText(frame, f"CAM: {did}", (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 180), 2)
            ascii_text = "STAFF COUNTER" if role == "STAFF" else (f"CUSTOMERS: {person_count}" if role == "CUSTOMER" else "EMPTY")
            cv2.putText(frame, f"{ascii_text} | {ts_now}", (w - 380, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.55, status_color, 2)
            return frame
    except Exception:
        return frame

class CameraWorker(threading.Thread):
    def __init__(self, did: str, camera_name: str, is_primary: bool = False):
        super().__init__(daemon=True)
        self.did = did
        self.camera_name = camera_name
        self.is_primary = is_primary
        self.stop_requested = False
        self.model = YOLO("yolov8n.pt")
        
        # Temporal smoothing window to eliminate single-frame glitches
        self.count_history = deque(maxlen=7)
        self.staff_filter_enabled = True
        
        # Session state
        self.active_session = None
        self.video_writer = None
        self.last_person_seen_time = 0
        self.session_start_time = 0
        self.last_interval_snap_time = 0
        self.snapped_milestones = set()
        self.current_role = "CUSTOMER"

    def stop(self):
        self.stop_requested = True

    def run(self):
        logger.info(f"🚀 Started CameraWorker for '{self.camera_name}' (DID: {self.did})")
        while not self.stop_requested:
            try:
                stream_url = get_camera_stream_url(self.did)
                if not stream_url:
                    logger.warning(f"Could not get stream URL for {self.camera_name}. Retrying in 10s...")
                    time.sleep(10)
                    continue

                cap = cv2.VideoCapture(stream_url)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                ret, _ = cap.read()
                if not ret:
                    time.sleep(3)
                    cap.release()
                    continue

                logger.info(f"🟢 Connected to live stream for '{self.camera_name}'!")
                
                last_frame_save_time = 0
                last_yolo_time = 0
                smoothed_person_count = 0
                recent_boxes = []

                while not self.stop_requested:
                    ret, raw_frame = cap.read()
                    if not ret or raw_frame is None:
                        logger.warning(f"Frame drop on {self.camera_name}. Reconnecting...")
                        break

                    now = time.time()

                    # High-frequency YOLO Person Detection (~7 FPS)
                    if now - last_yolo_time >= 0.14:
                        last_yolo_time = now
                        try:
                            results = self.model(raw_frame, imgsz=480, conf=0.42, verbose=False)
                            boxes = results[0].boxes
                            persons = [b for b in boxes if int(b.cls) == 0]
                            
                            h, w = raw_frame.shape[:2]
                            filtered_boxes = []
                            for b in persons:
                                xyxy = b.xyxy[0].cpu().numpy().astype(int)
                                cx = (xyxy[0] + xyxy[2]) / (2.0 * w)
                                cy = (xyxy[1] + xyxy[3]) / (2.0 * h)
                                
                                # Store front camera (262682799): ignore top mall corridor & mannequins
                                if self.did == "262682799" and cy < 0.38:
                                    continue
                                filtered_boxes.append((b, cx, cy, xyxy))
                                
                            staff_boxes = []
                            customer_boxes = []
                            
                            for b, cx, cy, xyxy in filtered_boxes:
                                is_staff = False
                                if self.staff_filter_enabled:
                                    x1, y1 = max(0, xyxy[0]), max(0, xyxy[1])
                                    x2, y2 = min(w, xyxy[2]), min(h, xyxy[3])
                                    crop = raw_frame[y1:y2, x1:x2]
                                    
                                    # 1. Visual matching against staff profiles (red uniform / white polo)
                                    match_res = staff_matcher.match_person_crop(crop, cx, cy)
                                    if match_res["is_staff"]:
                                        is_staff = True
                                    # 2. Store Front (262682799): Front cashier counter zone
                                    elif self.did == "262682799" and cx <= 0.52 and cy >= 0.45:
                                        is_staff = True
                                    # 3. Other cameras fallback desk zones
                                    elif self.did != "262682799" and ((cx > 0.70 and cy > 0.45) or (cx < 0.28 and cy > 0.40)):
                                        is_staff = True
                                        
                                if is_staff:
                                    staff_boxes.append((b, cx, cy))
                                else:
                                    customer_boxes.append((b, cx, cy))
                                    
                            raw_customer_count = len(customer_boxes)
                            staff_present = len(staff_boxes) > 0
                            
                            self.count_history.append(raw_customer_count)
                            if len(self.count_history) >= 3:
                                smoothed_customer_count = int(np.median(list(self.count_history)))
                            else:
                                smoothed_customer_count = raw_customer_count
                                
                        except Exception as e:
                            logger.error(f"Inference error: {e}")
                            smoothed_customer_count = 0
                            staff_present = False
                            customer_boxes = []

                    detected_role = "CUSTOMER" if smoothed_customer_count > 0 else ("STAFF" if staff_present else "EMPTY")
                    self.current_role = detected_role
                    display_frame = add_thai_watermark(raw_frame.copy(), self.camera_name, self.did, smoothed_customer_count, detected_role)

                    # Update camera frame files for Dashboard
                    if now - last_frame_save_time >= 0.7:
                        last_frame_save_time = now
                        cam_frame_path = f"data/live_cam_{self.did}.jpg"
                        cv2.imwrite(cam_frame_path, display_frame)
                        if self.is_primary or self.did == "263288748":
                            cv2.imwrite("data/live_camera_frame.jpg", display_frame)

                    # === REAL CUSTOMER SESSION STATE MACHINE ===
                    # If only staff is in frame -> ZERO sessions, ZERO snapshots, ZERO video clips!
                    if smoothed_customer_count > 0:
                        self.last_person_seen_time = now

                        if self.active_session is None:
                            # 🚀 REAL CUSTOMER DETECTED!
                            start_dt = now_bkk()
                            party_code = f"PTY-{start_dt.strftime('%y%m%d%H%M%S')}"
                            snap_path = os.path.join(SNAPSHOT_DIR, f"{party_code}_{self.did}_entry.jpg").replace("\\", "/")
                            clip_path = os.path.join(CLIPS_DIR, f"{party_code}_{self.did}_clip.mp4").replace("\\", "/")

                            # 1. Instant Entrance Snapshot (Exactly 1 photo)
                            cv2.imwrite(snap_path, display_frame)

                            # 2. Start or Merge Session across cameras
                            self.active_session = session_mgr.start_or_resume_session(
                                camera_name=self.camera_name,
                                camera_did=self.did,
                                snapshot_path=snap_path,
                                clip_path=clip_path,
                                people_count=smoothed_customer_count,
                                role="CUSTOMER",
                                grace_seconds=45,
                                cross_camera=True
                            )

                            self.session_start_time = now
                            self.snapped_milestones = set()
                            logger.info(f"🚨 [REAL CUSTOMER VISIT] Customer entered {self.camera_name} ({self.active_session['party_code']}) - Count: {smoothed_customer_count}")

                            # Initialize PyAV H.264 Video Writer
                            h, w = raw_frame.shape[:2]
                            self.video_writer = H264VideoWriter(clip_path, w, h, fps=15)

                        # Write frame to video
                        if self.video_writer is not None:
                            self.video_writer.write_frame(display_frame)

                        # 3. Controlled Milestone Snapshots (Only at 5s, 15s, 30s, 60s - Max 4 photos! NO INFINITE SNAPSHOTS!)
                        elapsed_sec = int(now - self.session_start_time)
                        milestones = [5, 15, 30, 60]
                        for m in milestones:
                            if elapsed_sec >= m and m not in self.snapped_milestones:
                                self.snapped_milestones.add(m)
                                extra_snap_name = f"{self.active_session['party_code']}_{self.did}_{m}s.jpg"
                                extra_snap_path = os.path.join(SNAPSHOT_DIR, extra_snap_name).replace("\\", "/")
                                cv2.imwrite(extra_snap_path, display_frame)
                                session_mgr.add_snapshot_to_session(self.active_session["id"], extra_snap_path)
                                logger.info(f"📸 Captured milestone snapshot at {m}s for {self.active_session['party_code']}")

                        # 4. Fitting Room Detection (Curtain zone bottom-right cx >= 0.65, cy >= 0.40)
                        if self.active_session is not None:
                            for b, cx, cy in customer_boxes:
                                if cx >= 0.65 and cy >= 0.40 and not self.active_session.get("entered_fitting_room"):
                                    self.active_session["entered_fitting_room"] = True
                                    session_mgr.mark_fitting_room_entry(self.active_session["id"])
                                    logger.info(f"🚪 [FITTING ROOM] Customer {self.active_session['party_code']} entered fitting room (cx={cx:.2f}, cy={cy:.2f})!")
                                    break

                        session_mgr.touch_session(self.active_session["id"])

                    elif self.active_session is not None:
                        # Customer temporarily absent
                        if self.video_writer is not None:
                            self.video_writer.write_frame(display_frame)

                        # Buffer check: 600s if in fitting room, 8.0s for normal exit
                        absence_threshold = 600.0 if self.active_session.get("entered_fitting_room") else 8.0
                        if now - self.last_person_seen_time > absence_threshold:
                            # Capture Exit Snapshot
                            exit_snap_path = os.path.join(SNAPSHOT_DIR, f"{self.active_session['party_code']}_{self.did}_exit.jpg").replace("\\", "/")
                            cv2.imwrite(exit_snap_path, display_frame)
                            session_mgr.add_snapshot_to_session(self.active_session["id"], exit_snap_path)

                            # Close video clip
                            if self.video_writer is not None:
                                self.video_writer.close()
                                self.video_writer = None

                            total_dwell_sec = round(now - self.session_start_time, 1)
                            sess_id = self.active_session["id"]
                            party_code = self.active_session["party_code"]
                            
                            session_mgr.close_session(sess_id, total_dwell_sec)
                            logger.info(f"🏁 [CUSTOMER VISIT COMPLETED] {self.camera_name} session {party_code} closed. Dwell: {total_dwell_sec}s")

                            # Send Telegram alert for customers
                            is_fitting = self.active_session.get("entered_fitting_room", False)
                            desc = "ลูกค้าเข้าลองกางเกงในห้องลอง (ผ้าม่านขวาล่าง)" if is_fitting else f"ลูกค้าเข้าชมพื้นที่ {self.active_session.get('camera_name', self.camera_name)} (เดินชม)"
                            send_telegram_alert({
                                "party_code": party_code,
                                "people_count": self.active_session["people_count"],
                                "description": desc,
                                "pants_touched": 1 if is_fitting else 0,
                                "entered_fitting_room": is_fitting,
                                "start_time": self.active_session["start_time"],
                                "end_time": bkk_str(),
                                "duration_minutes": round(total_dwell_sec / 60.0, 2)
                            }, photo_path=self.active_session["snapshot_path"], video_path=self.active_session["clip_path"], is_exit_summary=True)

                            self.active_session = None
                            self.snapped_milestones.clear()
                            self.count_history.clear()

                    time.sleep(0.04)

                cap.release()
                if self.video_writer is not None:
                    self.video_writer.close()
                    self.video_writer = None

            except Exception as e:
                logger.error(f"Worker exception for {self.camera_name}: {e}")
                time.sleep(5)

def start_self_keep_alive_bot(target_url: str = "https://auditcctv.streamlit.app/_stcore/health"):
    """Internal 24/7 Auto-Bot Trigger that pings Streamlit Cloud to prevent hibernation."""
    def pinger():
        logger.info(f"🤖 [Auto-Bot Trigger] Activated! Pinging {target_url} every 4 minutes 24/7...")
        import requests
        while True:
            time.sleep(240) # Every 4 minutes
            try:
                res = requests.get(target_url, timeout=8)
                logger.info(f"🤖 [Auto-Bot Ping] {target_url} -> Status: {res.status_code}")
            except Exception as e:
                logger.debug(f"🤖 [Auto-Bot Ping Error]: {e}")
    t = threading.Thread(target=pinger, daemon=True)
    t.start()

class MultiCameraSupervisor:
    def __init__(self):
        self.workers = {}
        self.bot_started = False

    def run(self):
        logger.info("Starting MultiCameraSupervisor with Auto-Device Discovery...")
        if not self.bot_started:
            start_self_keep_alive_bot()
            self.bot_started = True

        while True:
            try:
                online_cams = get_online_cameras(force_refresh=True)
                active_dids = {c["did"]: c for c in online_cams}

                # Start workers for any newly online cameras (including Video camera2 when turned on)
                for did, cam in active_dids.items():
                    if did not in self.workers or not self.workers[did].is_alive():
                        is_primary = (len(self.workers) == 0 or did == "263288748")
                        worker = CameraWorker(did, cam.get("name", f"Camera {did}"), is_primary=is_primary)
                        worker.start()
                        self.workers[did] = worker
                        logger.info(f"🌟 Launched worker for camera: {cam.get('name')} (DID: {did})")

                # Stop workers for cameras that went offline
                for did in list(self.workers.keys()):
                    if did not in active_dids:
                        logger.info(f"Camera DID {did} went offline. Stopping worker...")
                        self.workers[did].stop()
                        del self.workers[did]

            except Exception as e:
                logger.error(f"Supervisor loop error: {e}")

            time.sleep(15)

if __name__ == "__main__":
    space_host = os.environ.get("SPACE_HOST")
    if space_host:
        try:
            from hf_cloud_sync import start_keep_alive_pinger
            start_keep_alive_pinger(f"https://{space_host}")
        except Exception:
            pass

    supervisor = MultiCameraSupervisor()
    supervisor.run()
