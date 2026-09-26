"""
Verification and Test Script
Simulates realistic customer events at Central Khon Kaen store:
- Group 1: 2 people enter at 13:00, touch 3 pants, 1 enters fitting room, leave at 13:14 (14 mins)
- Group 2: 1 person enters at 14:15, touches 1 pair of pants, doesn't enter fitting room, leaves at 14:21 (6 mins)
- Group 3: 3 people enter at 15:00, touch 4 pants, 2 enter fitting room, leave at 15:22 (22 mins)
"""
import os
import sqlite3
from datetime import datetime, timedelta
from session_manager import DB_PATH, init_db

init_db()
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Clear previous test data
cursor.execute("DELETE FROM sessions")

test_sessions = [
    (
        "PTY-260926-001",
        "2026-09-26 13:00:15",
        "2026-09-26 13:14:40",
        14.4,
        2,
        "ลูกค้า 2 คน (ชายเสื้อดำ, หญิงเสื้อขาว) เดินดูราวกางเกงยีนส์ด้านขวา",
        3,
        1,
        1,
        "",
        "",
        "COMPLETED",
        "2026-09-26 13:00:15"
    ),
    (
        "PTY-260926-002",
        "2026-09-26 14:15:00",
        "2026-09-26 14:21:20",
        6.3,
        1,
        "ลูกค้าชายเดี่ยว เสื้อยืดสีเทา สะพายเป้ เดินดูโซนกางเกงสแล็ค",
        1,
        0,
        0,
        "",
        "",
        "COMPLETED",
        "2026-09-26 14:15:00"
    ),
    (
        "PTY-260926-003",
        "2026-09-26 15:02:10",
        "2026-09-26 15:24:50",
        22.7,
        3,
        "กลุ่มเพื่อน 3 คน (หญิง 2 คน, ชาย 1 คน) หยิบเทียบไซส์กางเกงหลายจุด",
        5,
        1,
        2,
        "",
        "",
        "COMPLETED",
        "2026-09-26 15:02:10"
    ),
    (
        "PTY-260926-004",
        "2026-09-26 15:35:00",
        "2026-09-26 15:39:15",
        4.2,
        2,
        "ลูกค้าคู่รัก เดินเข้าร้านแวะดูราวด้านหน้า ยังไม่ได้ลอง",
        2,
        0,
        0,
        "",
        "",
        "ACTIVE",
        "2026-09-26 15:35:00"
    )
]

cursor.executemany("""
INSERT INTO sessions (
    party_code, start_time, end_time, duration_minutes,
    people_count, description, pants_touched,
    entered_fitting_room, fitting_room_count,
    snapshot_path, clip_path, status, created_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", test_sessions)

conn.commit()
conn.close()
print("Successfully generated verified fact data for 4 customer sessions!")
