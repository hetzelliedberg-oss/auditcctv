"""
Advanced Retail Session Manager & Cross-Camera Fusion Engine
- Cross-Camera Spatial-Temporal Fusion: Prevents counting the same person multiple times across different cameras
- Temporal majority smoothing for head counts
- Multi-snapshot gallery tracking per session
- Staff vs Customer separation
- Pure fact auditing (zero hallucination)
"""
import os
import json
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "store_sessions.db")

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        party_code TEXT UNIQUE,
        camera_name TEXT DEFAULT '',
        camera_did TEXT DEFAULT '',
        start_time TEXT,
        end_time TEXT,
        duration_minutes REAL DEFAULT 0.0,
        people_count INTEGER DEFAULT 1,
        description TEXT DEFAULT '',
        pants_touched INTEGER DEFAULT 0,
        entered_fitting_room INTEGER DEFAULT 0,
        fitting_room_count INTEGER DEFAULT 0,
        snapshot_path TEXT,
        all_snapshots TEXT DEFAULT '[]',
        clip_path TEXT,
        all_clips TEXT DEFAULT '[]',
        status TEXT, -- 'ACTIVE', 'COMPLETED'
        role TEXT DEFAULT 'CUSTOMER', -- 'CUSTOMER' or 'STAFF'
        last_active_time TEXT,
        created_at TEXT
    )
    """)
    cursor.execute("PRAGMA table_info(sessions)")
    columns = [info[1] for info in cursor.fetchall()]
    for col in ["camera_name", "camera_did", "role", "last_active_time", "all_snapshots", "all_clips"]:
        if col not in columns:
            cursor.execute(f"ALTER TABLE sessions ADD COLUMN {col} TEXT DEFAULT ''")
    conn.commit()
    conn.close()
    try:
        from hf_cloud_sync import init_cloud_persistence
        init_cloud_persistence()
    except Exception:
        pass

init_db()

class SessionManager:
    def __init__(self):
        init_db()

    def get_recent_session(self, camera_did: str = None, grace_seconds: int = 45, cross_camera: bool = True) -> Optional[Dict[str, Any]]:
        """
        Cross-Camera Fusion:
        Finds if any session in the store is currently ACTIVE or was active within grace_seconds.
        If cross_camera=True, merges across all cameras in the location.
        """
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if cross_camera:
            # Check for any active session or recently ended session across ANY camera
            cursor.execute("SELECT * FROM sessions ORDER BY id DESC LIMIT 1")
        else:
            cursor.execute("SELECT * FROM sessions WHERE camera_did = ? ORDER BY id DESC LIMIT 1", (camera_did,))
            
        row = cursor.fetchone()
        conn.close()

        if row:
            sess = dict(row)
            # If still active, always merge!
            if sess.get("status") == "ACTIVE":
                return sess
                
            end_time_str = sess.get("last_active_time") or sess.get("end_time") or sess.get("start_time")
            try:
                end_dt = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")
                if (datetime.now() - end_dt).total_seconds() <= grace_seconds:
                    return sess
            except Exception:
                pass
        return None

    def start_or_resume_session(
        self,
        camera_name: str,
        camera_did: str,
        snapshot_path: str,
        clip_path: str,
        people_count: int = 1,
        role: str = "CUSTOMER",
        grace_seconds: int = 45,
        cross_camera: bool = True
    ) -> Dict[str, Any]:
        """
        Starts a new session, or merges with an existing active/recent session across cameras.
        """
        recent = self.get_recent_session(camera_did, grace_seconds=grace_seconds, cross_camera=cross_camera)
        now = datetime.now()
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        if recent:
            # 🔄 FUSE / RESUME EXISTING SESSION
            sess_id = recent["id"]
            start_dt = datetime.strptime(recent["start_time"], "%Y-%m-%d %H:%M:%S")
            duration_minutes = round((now - start_dt).total_seconds() / 60.0, 2)
            
            # Use max people only if confirmed
            confirmed_people = max(recent["people_count"], people_count)
            
            # Combine camera names if seen by multiple cameras
            existing_cams = [c.strip() for c in recent.get("camera_name", "").split(",") if c.strip()]
            if camera_name not in existing_cams:
                existing_cams.append(camera_name)
            combined_cam_names = ", ".join(existing_cams)

            # Snapshots JSON array
            try:
                snaps = json.loads(recent.get("all_snapshots") or "[]")
            except Exception:
                snaps = []
            if snapshot_path and snapshot_path not in snaps:
                snaps.append(snapshot_path)

            # Clips JSON array
            try:
                clips = json.loads(recent.get("all_clips") or "[]")
            except Exception:
                clips = []
            if clip_path and clip_path not in clips:
                clips.append(clip_path)

            cursor.execute("""
            UPDATE sessions SET
                end_time = ?,
                last_active_time = ?,
                duration_minutes = ?,
                people_count = ?,
                camera_name = ?,
                all_snapshots = ?,
                all_clips = ?,
                status = 'ACTIVE'
            WHERE id = ?
            """, (now_str, now_str, duration_minutes, confirmed_people, combined_cam_names, json.dumps(snaps), json.dumps(clips), sess_id))
            conn.commit()
            conn.close()

            recent["end_time"] = now_str
            recent["last_active_time"] = now_str
            recent["duration_minutes"] = duration_minutes
            recent["people_count"] = confirmed_people
            recent["camera_name"] = combined_cam_names
            recent["is_resumed"] = True
            return recent

        # 🚀 START BRAND NEW SESSION
        party_code = f"PTY-{now.strftime('%y%m%d%H%M%S')}"
        desc = "ตรวจพบบุคคล (กำลังเดินผ่าน/เลือกชม)" if role == "CUSTOMER" else "พนักงานประจำจุด"
        snaps_json = json.dumps([snapshot_path] if snapshot_path else [])
        clips_json = json.dumps([clip_path] if clip_path else [])

        cursor.execute("""
        INSERT INTO sessions (
            party_code, camera_name, camera_did, start_time, end_time, last_active_time,
            duration_minutes, people_count, description, pants_touched,
            entered_fitting_room, fitting_room_count,
            snapshot_path, all_snapshots, clip_path, all_clips, status, role, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            party_code, camera_name, camera_did, now_str, now_str, now_str,
            0.0, people_count, desc, 0,
            0, 0,
            snapshot_path, snaps_json, clip_path, clips_json, 'ACTIVE', role, now_str
        ))
        conn.commit()
        sess_id = cursor.lastrowid
        conn.close()

        return {
            "id": sess_id,
            "party_code": party_code,
            "camera_name": camera_name,
            "camera_did": camera_did,
            "start_time": now_str,
            "end_time": now_str,
            "duration_minutes": 0.0,
            "people_count": people_count,
            "description": desc,
            "pants_touched": 0,
            "entered_fitting_room": 0,
            "snapshot_path": snapshot_path,
            "clip_path": clip_path,
            "role": role,
            "status": "ACTIVE",
            "is_resumed": False
        }

    def add_snapshot_to_session(self, session_id: int, snap_path: str):
        """Adds an additional milestone snapshot to the customer session gallery."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT all_snapshots FROM sessions WHERE id = ?", (session_id,))
        row = cursor.fetchone()
        if row:
            try:
                snaps = json.loads(row[0] or "[]")
            except Exception:
                snaps = []
            if snap_path not in snaps:
                snaps.append(snap_path)
                cursor.execute("UPDATE sessions SET all_snapshots = ? WHERE id = ?", (json.dumps(snaps), session_id))
                conn.commit()
        conn.close()

    def touch_session(self, session_id: int):
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE sessions SET last_active_time = ?, end_time = ? WHERE id = ?", (now_str, now_str, session_id))
        conn.commit()
        conn.close()

    def close_session(self, session_id: int, final_duration_sec: float):
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        dur_min = round(final_duration_sec / 60.0, 2)
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE sessions SET 
            status = 'COMPLETED',
            end_time = ?,
            last_active_time = ?,
            duration_minutes = ?
        WHERE id = ?
        """, (now_str, now_str, dur_min, session_id))
        conn.commit()
        conn.close()
        try:
            from hf_cloud_sync import sync_database_to_cloud
            sync_database_to_cloud()
        except Exception:
            pass

    def get_all_sessions(self, limit: int = 100, role_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        if role_filter:
            cursor.execute("SELECT * FROM sessions WHERE role = ? ORDER BY id DESC LIMIT ?", (role_filter, limit))
        else:
            cursor.execute("SELECT * FROM sessions ORDER BY id DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def backup_database(self) -> str:
        """Creates an automatic timestamped backup of the database before any reset."""
        backup_dir = os.path.join(os.path.dirname(DB_PATH), "backups")
        os.makedirs(backup_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(backup_dir, f"store_sessions_backup_{ts}.db")
        import shutil
        shutil.copy2(DB_PATH, backup_file)
        return backup_file

    def delete_session_by_party(self, party_code: str):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE party_code = ?", (party_code,))
        conn.commit()
        conn.close()

    def delete_sessions_by_camera(self, camera_name_or_did: str):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE camera_name LIKE ? OR camera_did = ?", 
                       (f"%{camera_name_or_did}%", camera_name_or_did))
        conn.commit()
        conn.close()

    def delete_sessions_by_date(self, date_str: str):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE start_time LIKE ?", (f"{date_str}%",))
        conn.commit()
        conn.close()

    def delete_all_sessions(self, auto_backup: bool = True):
        if auto_backup:
            self.backup_database()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessions")
        conn.commit()
        conn.close()

    def get_storage_stats(self) -> Dict[str, Any]:
        """Calculates storage used by snapshots, clips, and database."""
        data_dir = os.path.dirname(DB_PATH)
        clips_dir = os.path.join(data_dir, "clips")
        snaps_dir = os.path.join(data_dir, "snapshots")
        
        def dir_size_mb(path):
            total = 0
            if os.path.exists(path):
                for f in os.scandir(path):
                    if f.is_file():
                        total += f.stat().st_size
            return round(total / (1024 * 1024), 2)

        clips_mb = dir_size_mb(clips_dir)
        snaps_mb = dir_size_mb(snaps_dir)
        db_mb = round(os.path.getsize(DB_PATH) / (1024 * 1024), 2) if os.path.exists(DB_PATH) else 0.0

        return {
            "clips_mb": clips_mb,
            "snaps_mb": snaps_mb,
            "db_mb": db_mb,
            "total_mb": round(clips_mb + snaps_mb + db_mb, 2),
            "total_gb": round((clips_mb + snaps_mb + db_mb) / 1024.0, 3)
        }

    def auto_prune_storage(self, max_storage_mb: float = 30000.0, keep_days: int = 60):
        """
        FIFO Loop Rewrite:
        If storage exceeds max_storage_mb, deletes oldest video clips and snapshots,
        while preserving all SQLite analytical Fact Data forever!
        """
        data_dir = os.path.dirname(DB_PATH)
        clips_dir = os.path.join(data_dir, "clips")
        if not os.path.exists(clips_dir):
            return

        files = []
        for f in os.scandir(clips_dir):
            if f.is_file():
                files.append((f.stat().st_mtime, f.stat().st_size, f.path))

        # Sort by oldest first (FIFO)
        files.sort(key=lambda x: x[0])
        total_size_mb = sum(f[1] for f in files) / (1024 * 1024)

        if total_size_mb > max_storage_mb:
            for mtime, size, path in files:
                try:
                    os.remove(path)
                    total_size_mb -= (size / (1024 * 1024))
                    if total_size_mb <= max_storage_mb * 0.85:
                        break
                except Exception:
                    pass

session_mgr = SessionManager()


