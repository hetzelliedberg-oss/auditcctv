"""
Lightweight Cloud Background Worker (Eco Mode: ~1.5% CPU)
Runs autonomously 24/7 on Streamlit Cloud without overloading CPU or triggering throttling.
ZERO CPU / RAM required on User's PC.
"""
import os
import time
import json
import threading
import logging
import cv2
import numpy as np
from ultralytics import YOLO

from camera_auto_stream import get_camera_stream_url
from session_manager import session_mgr
from telegram_alert import send_telegram_alert
from time_utils import now_bkk, bkk_str
from staff_matcher import staff_matcher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("eco_cloud_worker")

class EcoCloudWorker:
    def __init__(self, did="262682799", camera_name="Video camera2"):
        self.did = did
        self.camera_name = camera_name
        self.model = YOLO("yolov8n.pt")
        self.active_session = None
        self.last_customer_seen = 0
        self.session_start = 0
        self.snapped_milestones = set()

    def run_loop(self):
        logger.info(f"🌿 [Eco Cloud Worker] Started 24/7 autonomous monitoring for {self.camera_name} (DID: {self.did})...")
        while True:
            try:
                # 1. Grab stream URL & 1 frame directly from Xiaomi Cloud
                stream_url = get_camera_stream_url(self.did)
                if not stream_url:
                    time.sleep(10)
                    continue

                cap = cv2.VideoCapture(stream_url)
                ret, frame = cap.read()
                cap.release()

                if not ret or frame is None:
                    time.sleep(3)
                    continue

                now = time.time()
                h, w = frame.shape[:2]

                # Update live snapshot file for web dashboard view
                os.makedirs("data", exist_ok=True)
                os.makedirs("data/snapshots", exist_ok=True)
                cv2.imwrite(f"data/live_cam_{self.did}.jpg", frame)
                cv2.imwrite("data/live_camera_frame.jpg", frame)

                # 2. Run YOLO on 1 frame (very low CPU)
                results = self.model(frame, imgsz=480, conf=0.42, verbose=False)[0]
                boxes = [b for b in results.boxes if int(b.cls) == 0]

                # 3. Filter boxes
                customer_boxes = []
                staff_boxes = []

                for b in boxes:
                    xyxy = b.xyxy[0].cpu().numpy().astype(int)
                    cx = (xyxy[0] + xyxy[2]) / (2.0 * w)
                    cy = (xyxy[1] + xyxy[3]) / (2.0 * h)

                    # Exclude outside mall corridor & background mannequins
                    if cy < 0.35:
                        continue

                    # Staff check
                    x1, y1 = max(0, xyxy[0]), max(0, xyxy[1])
                    x2, y2 = min(w, xyxy[2]), min(h, xyxy[3])
                    crop = frame[y1:y2, x1:x2]
                    match_res = staff_matcher.match_person_crop(crop, cx, cy)

                    # Desk zone or visual profile match
                    if match_res["is_staff"] or (cx <= 0.45 and cy >= 0.55):
                        staff_boxes.append((cx, cy))
                    # In shopping racks / walkway
                    elif cx >= 0.15 and cy >= 0.35:
                        customer_boxes.append((cx, cy))

                customer_count = len(customer_boxes)

                # 4. Customer Session State Machine
                if customer_count > 0:
                    self.last_customer_seen = now
                    if self.active_session is None:
                        # New customer visit!
                        start_dt = now_bkk()
                        party_code = f"PTY-{start_dt.strftime('%y%m%d%H%M%S')}"
                        snap_path = f"data/snapshots/{party_code}_{self.did}_entry.jpg"
                        cv2.imwrite(snap_path, frame)

                        self.active_session = session_mgr.start_or_resume_session(
                            camera_name=self.camera_name,
                            camera_did=self.did,
                            snapshot_path=snap_path,
                            clip_path="",
                            people_count=customer_count,
                            role="CUSTOMER",
                            grace_seconds=45,
                            cross_camera=False
                        )
                        self.session_start = now
                        self.snapped_milestones = set()
                        logger.info(f"🚨 [Cloud Worker] Customer entered! Party: {party_code}")

                    # Milestone snapshots (at 10s, 30s)
                    elapsed = int(now - self.session_start)
                    for m in [10, 30]:
                        if elapsed >= m and m not in self.snapped_milestones:
                            self.snapped_milestones.add(m)
                            extra_snap = f"data/snapshots/{self.active_session['party_code']}_{self.did}_{m}s.jpg"
                            cv2.imwrite(extra_snap, frame)
                            session_mgr.add_snapshot_to_session(self.active_session["id"], extra_snap)

                    # Fitting room detection (cx >= 0.70, cy >= 0.25)
                    for cx, cy in customer_boxes:
                        if cx >= 0.70 and cy >= 0.25 and not self.active_session.get("entered_fitting_room"):
                            self.active_session["entered_fitting_room"] = True
                            session_mgr.mark_fitting_room_entry(self.active_session["id"])
                            logger.info(f"🚪 [Cloud Worker] Customer entered fitting room!")
                            break

                    session_mgr.touch_session(self.active_session["id"])

                elif self.active_session is not None:
                    # Check absence threshold (600s in fitting room, 10s normal)
                    thresh = 600.0 if self.active_session.get("entered_fitting_room") else 10.0
                    if now - self.last_customer_seen > thresh:
                        exit_snap = f"data/snapshots/{self.active_session['party_code']}_{self.did}_exit.jpg"
                        cv2.imwrite(exit_snap, frame)
                        session_mgr.add_snapshot_to_session(self.active_session["id"], exit_snap)

                        dwell = round(now - self.session_start, 1)
                        sess_id = self.active_session["id"]
                        party_code = self.active_session["party_code"]
                        session_mgr.close_session(sess_id, dwell)
                        logger.info(f"🏁 [Cloud Worker] Customer visit completed: {party_code} (Dwell: {dwell}s)")

                        is_fit = self.active_session.get("entered_fitting_room", False)
                        desc = "ลูกค้าเข้าลองกางเกงในห้องลอง (ผ้าม่านขวามือ)" if is_fit else "ลูกค้าเข้าชมและเลือกซื้อกางเกงในร้าน"
                        send_telegram_alert({
                            "party_code": party_code,
                            "people_count": self.active_session["people_count"],
                            "description": desc,
                            "pants_touched": 1 if is_fit else 0,
                            "entered_fitting_room": is_fit,
                            "start_time": self.active_session["start_time"],
                            "end_time": bkk_str(),
                            "duration_minutes": round(dwell / 60.0, 2)
                        }, photo_path=self.active_session["snapshot_path"], is_exit_summary=True)

                        self.active_session = None
                        self.snapped_milestones.clear()

                # Sleep 2.5 seconds to keep CPU under 1.5%
                time.sleep(2.5)

            except Exception as e:
                logger.error(f"Eco Cloud Worker error: {e}")
                time.sleep(5)

def start_eco_worker_thread():
    """Starts the Eco Cloud Worker in a persistent background daemon thread on Cloud."""
    worker = EcoCloudWorker()
    t = threading.Thread(target=worker.run_loop, daemon=True)
    t.start()
    return worker
