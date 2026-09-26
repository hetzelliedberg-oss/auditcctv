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

FONT_PATH = "C:/Windows/Fonts/tahoma.ttf"
THAI_FONT = None
if os.path.exists(FONT_PATH):
    try:
        THAI_FONT = ImageFont.truetype(FONT_PATH, 19)
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
        ts_now = time.strftime("%Y-%m-%d %H:%M:%S")

        left_text = f"📹 {camera_name} [DID: {did}]"
        if person_count > 0:
            if role == "STAFF":
                status_text = f"🧑‍💼 พนักงานประจำจุด ({person_count} คน) | LIVE {ts_now}"
                status_color = (100, 200, 255)
            else:
                status_text = f"🚨 ลูกค้าเข้าชม: {person_count} คน | LIVE {ts_now}"
                status_color = (255, 60, 60)
        else:
            status_text = f"● LIVE  {ts_now}"
            status_color = (255, 255, 255)

        if THAI_FONT:
            draw.text((12, 11), left_text, font=THAI_FONT, fill=(0, 255, 180))
            draw.text((w - 330, 11), status_text, font=THAI_FONT, fill=status_color)
            return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        else:
            cv2.putText(frame, f"CAM: {did}", (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 180), 2)
            cv2.putText(frame, status_text, (w - 330, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.55, status_color, 2)
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
                            # Use conf=0.48 to eliminate office chair & coat false positives
                            results = self.model(raw_frame, imgsz=480, conf=0.48, verbose=False)
                            boxes = results[0].boxes
                            persons = [b for b in boxes if int(b.cls) == 0]
                            raw_count = len(persons)
                            recent_boxes = persons
                            
                            # Append to history and calculate robust majority/median count
                            self.count_history.append(raw_count)
                            if len(self.count_history) >= 3:
                                smoothed_person_count = int(np.median(list(self.count_history)))
                            else:
                                smoothed_person_count = raw_count
                        except Exception as e:
                            logger.error(f"Inference error: {e}")
                            smoothed_person_count = 0
                            recent_boxes = []

                    # Staff Filter
                    detected_role = "CUSTOMER"
                    if smoothed_person_count > 0 and self.staff_filter_enabled:
                        h, w = raw_frame.shape[:2]
                        for b in recent_boxes:
                            xyxy = b.xyxy[0].cpu().numpy()
                            cx = (xyxy[0] + xyxy[2]) / (2.0 * w)
                            cy = (xyxy[1] + xyxy[3]) / (2.0 * h)
                            # Bottom-right counter desk zone
                            if cx > 0.72 and cy > 0.52:
                                detected_role = "STAFF"

                    self.current_role = detected_role
                    display_frame = add_thai_watermark(raw_frame.copy(), self.camera_name, self.did, smoothed_person_count, detected_role)

                    # Update camera frame files for Dashboard
                    if now - last_frame_save_time >= 0.7:
                        last_frame_save_time = now
                        cam_frame_path = f"data/live_cam_{self.did}.jpg"
                        cv2.imwrite(cam_frame_path, display_frame)
                        if self.is_primary or self.did == "263288748":
                            cv2.imwrite("data/live_camera_frame.jpg", display_frame)

                    # === CONTINUOUS EVENT & SESSION STATE MACHINE ===
                    if smoothed_person_count > 0:
                        self.last_person_seen_time = now

                        if self.active_session is None:
                            # 🚀 PERSON DETECTED!
                            start_dt = datetime.now()
                            party_code = f"PTY-{start_dt.strftime('%y%m%d%H%M%S')}"
                            snap_path = os.path.join(SNAPSHOT_DIR, f"{party_code}_{self.did}_entry.jpg")
                            clip_path = os.path.join(CLIPS_DIR, f"{party_code}_{self.did}_clip.mp4")

                            # 1. Instant Entrance Snapshot
                            cv2.imwrite(snap_path, display_frame)

                            # 2. Start or Merge Session across cameras
                            self.active_session = session_mgr.start_or_resume_session(
                                camera_name=self.camera_name,
                                camera_did=self.did,
                                snapshot_path=snap_path,
                                clip_path=clip_path,
                                people_count=smoothed_person_count,
                                role=detected_role,
                                grace_seconds=45,
                                cross_camera=True # Cross-camera fusion prevents 2 cameras counting 2 people!
                            )

                            if self.active_session.get("is_resumed"):
                                logger.info(f"🔄 [FUSED SESSION] Linked visit on {self.camera_name} to {self.active_session['party_code']}")
                            else:
                                logger.info(f"🚨 [NEW VISIT] {detected_role} entered {self.camera_name} ({self.active_session['party_code']})")

                            self.session_start_time = now
                            self.last_interval_snap_time = now

                            # Initialize PyAV H.264 Video Writer
                            h, w = raw_frame.shape[:2]
                            self.video_writer = H264VideoWriter(clip_path, w, h, fps=15)

                        # Write frame to video
                        if self.video_writer is not None:
                            self.video_writer.write_frame(display_frame)

                        # 3. Interval Snapshots (Capture multiple angles every 4 seconds)
                        if now - self.last_interval_snap_time >= 4.0:
                            self.last_interval_snap_time = now
                            elapsed_sec = int(now - self.session_start_time)
                            extra_snap_name = f"{self.active_session['party_code']}_{self.did}_{elapsed_sec}s.jpg"
                            extra_snap_path = os.path.join(SNAPSHOT_DIR, extra_snap_name)
                            cv2.imwrite(extra_snap_path, display_frame)
                            session_mgr.add_snapshot_to_session(self.active_session["id"], extra_snap_path)

                        session_mgr.touch_session(self.active_session["id"])

                    elif self.active_session is not None:
                        # Person temporarily absent
                        if self.video_writer is not None:
                            self.video_writer.write_frame(display_frame)

                        # Buffer check: Has person been gone for > 8.0 seconds continuously?
                        if now - self.last_person_seen_time > 8.0:
                            # Capture Exit Snapshot
                            exit_snap_path = os.path.join(SNAPSHOT_DIR, f"{self.active_session['party_code']}_{self.did}_exit.jpg")
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
                            logger.info(f"🏁 [EVENT BUFFER FINISHED] {self.camera_name} session {party_code} closed. Dwell: {total_dwell_sec}s")

                            # Send Telegram alert for customers
                            if self.active_session.get("role") != "STAFF":
                                send_telegram_alert({
                                    "party_code": party_code,
                                    "people_count": self.active_session["people_count"],
                                    "description": f"ลูกค้าเข้าชมพื้นที่ {self.active_session.get('camera_name', self.camera_name)} (จับกางเกง: 0 ตัว - เดินชม)",
                                    "pants_touched": 0,
                                    "entered_fitting_room": False,
                                    "start_time": self.active_session["start_time"],
                                    "end_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    "duration_minutes": round(total_dwell_sec / 60.0, 2)
                                }, photo_path=self.active_session["snapshot_path"], video_path=self.active_session["clip_path"], is_exit_summary=True)

                            self.active_session = None
                            self.count_history.clear()

                    time.sleep(0.04)

                cap.release()
                if self.video_writer is not None:
                    self.video_writer.close()
                    self.video_writer = None

            except Exception as e:
                logger.error(f"Worker exception for {self.camera_name}: {e}")
                time.sleep(5)

class MultiCameraSupervisor:
    def __init__(self):
        self.workers = {}

    def run(self):
        logger.info("Starting MultiCameraSupervisor with Auto-Device Discovery...")
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
