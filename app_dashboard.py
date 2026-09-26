import os
import sys
import time
import json
import sqlite3
import pandas as pd
from datetime import datetime
import streamlit as st
import streamlit.components.v1 as components

from camera_auto_stream import capture_live_frame, get_camera_stream_url, execute_auto_workflow_for_camera
from session_manager import session_mgr, DB_PATH
from device_sync import get_cameras, get_all_devices, refresh_device_list_from_cloud

st.set_page_config(
    page_title="ระบบวิเคราะห์กล้องวงจรปิด AI & Live Fact Engine",
    page_icon="🎥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Auto-start Multi-Camera AI Supervisor in background thread on server startup
@st.cache_resource
def ensure_cctv_daemon_running():
    import threading
    from live_stream_daemon import MultiCameraSupervisor
    supervisor = MultiCameraSupervisor()
    t = threading.Thread(target=supervisor.run, daemon=True)
    t.start()
    return supervisor

try:
    ensure_cctv_daemon_running()
except Exception:
    pass

# Custom Styling
st.markdown("""
<style>
    .metric-card {
        background: #1e222d;
        padding: 16px;
        border-radius: 10px;
        border-left: 5px solid #2e7bf6;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 12px;
    }
    .status-online {
        color: #00ff66;
        font-weight: bold;
    }
    .status-offline {
        color: #888888;
    }
    .live-badge {
        background-color: #e50914;
        color: white;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 700;
        font-size: 0.8rem;
        display: inline-block;
        margin-bottom: 8px;
    }
    .camera-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 8px;
    }
</style>
""", unsafe_allow_html=True)

# Fetch Fact Data from SQLite
def load_data(role_filter=None):
    conn = sqlite3.connect(DB_PATH)
    if role_filter:
        df = pd.read_sql_query("SELECT * FROM sessions WHERE role = ? ORDER BY id DESC", conn, params=(role_filter,))
    else:
        df = pd.read_sql_query("SELECT * FROM sessions ORDER BY id DESC", conn)
    conn.close()
    return df

# Get Cameras
CAMERAS = get_cameras(force_refresh=False)
ALL_DEVICES = get_all_devices(force_refresh=False)

# Sidebar
with st.sidebar:
    st.image("https://img.icons8.com/color/96/cctv.png", width=64)
    st.title("ระบบวิเคราะห์กล้อง AI")
    st.markdown("**บัญชี Xiaomi Cloud:** `6274970591`")
    
    online_count = len([c for c in CAMERAS if c.get("isOnline")])
    st.markdown(f"""<span class="status-online">🟢 ออนไลน์ {online_count} ตัว</span> (จากทั้งหมด {len(CAMERAS)} กล้อง)""", unsafe_allow_html=True)
    
    if st.button("🔄 รีเฟรชสถานะกล้องสดจาก Xiaomi Cloud", use_container_width=True):
        with st.spinner("กำลังเชื่อมต่อ Cloud เพื่อตรวจเช็คสถานะกล้องทุกตัว..."):
            refresh_device_list_from_cloud()
            st.rerun()

    st.divider()

    st.subheader("⚡ ระบบ AI Computer Vision")
    st.success("🤖 YOLOv8 Person Detector + PyAV H.264")
    st.markdown("""
    - **Session Continuity:** รวมคนเดิมเดินไปมาใน 45 วิเป็น 1 เจ้า
    - **Strict Fact:** ไม่มั่วจับกางเกง (0 คือ 0)
    - **Instant Snapshot:** แคปเจอร์ทันทีที่ก้าวเข้าเฟรม
    """)

    st.divider()
    st.subheader("🧑‍💼 ระบบกรองพนักงาน (Staff Filter)")
    filter_staff = st.toggle("เปิดใช้งานโหมดกรองพนักงานประจำ", value=True)
    st.caption("พนักงานที่ยืนประจำจุดจะถูกคัดแยก ไม่นำมานับรวมเป็นยอดคนเข้าร้าน (Customer Traffic)")

    st.divider()
    st.subheader("💾 พื้นที่จัดเก็บ & Auto-Rewrite (FIFO)")
    storage = session_mgr.get_storage_stats()
    st.markdown(f"""
    - **ขนาดวิดีโอคลิป:** `{storage['clips_mb']} MB`
    - **ขนาดภาพถ่าย:** `{storage['snaps_mb']} MB`
    - **ขนาดฐานข้อมูล Fact:** `{storage['db_mb']} MB`
    - **พื้นที่รวมที่ใช้ไป:** `{storage['total_mb']} MB` ({storage['total_gb']} GB)
    """)
    st.markdown("🔄 **โหมดหมุนเวียน (Auto-Rewrite Loop):** `🟢 เปิดใช้งาน` (วนทับไฟล์เก่าเมื่อใกล้เต็ม ข้อมูลตัวเลขไม่หาย)")

    st.divider()
    st.subheader("🗂️ ศูนย์จัดการและสำรองข้อมูล")
    if st.button("💾 สำรองฐานข้อมูล (Backup DB)", use_container_width=True):
        bk_path = session_mgr.backup_database()
        st.success(f"สำรองข้อมูลเรียบร้อย: {os.path.basename(bk_path)}")

    with st.expander("🗑️ ตัวเลือกลบข้อมูลแบบเจาะจง"):
        reset_mode = st.radio("เลือกลบตามเงื่อนไข:", ["📷 ตามกล้อง", "📅 ตามวันที่", "🏷️ ตามรหัสเจ้า (PTY)", "⚠️ ลบทั้งหมด"])
        
        if reset_mode == "📷 ตามกล้อง":
            c_names = [c.get("name") for c in CAMERAS]
            selected_cam_del = st.selectbox("เลือกกล้องที่ต้องการลบประวัติ:", c_names)
            if st.button(f"ยืนยันลบประวัติของกล้อง '{selected_cam_del}'", type="secondary"):
                session_mgr.delete_sessions_by_camera(selected_cam_del)
                st.success(f"ลบประวัติของ {selected_cam_del} เรียบร้อย!")
                time.sleep(1)
                st.rerun()

        elif reset_mode == "📅 ตามวันที่":
            today_str = datetime.now().strftime("%Y-%m-%d")
            del_date = st.text_input("ระบุวันที่ต้องการลบ (YYYY-MM-DD):", value=today_str)
            if st.button(f"ยืนยันลบข้อมูลวันที่ {del_date}", type="secondary"):
                session_mgr.delete_sessions_by_date(del_date)
                st.success(f"ลบข้อมูลวันที่ {del_date} เรียบร้อย!")
                time.sleep(1)
                st.rerun()

        elif reset_mode == "🏷️ ตามรหัสเจ้า (PTY)":
            df_cur = load_data()
            if not df_cur.empty:
                ptys = df_cur["party_code"].tolist()
                del_pty = st.selectbox("เลือกรหัสเจ้าที่ต้องการลบ:", ptys)
                if st.button(f"ลบรหัสเจ้า {del_pty}", type="secondary"):
                    session_mgr.delete_session_by_party(del_pty)
                    st.success(f"ลบเจ้า {del_pty} เรียบร้อย!")
                    time.sleep(1)
                    st.rerun()
            else:
                st.info("ไม่มีรายการเจ้าในระบบ")

        elif reset_mode == "⚠️ ลบทั้งหมด":
            confirm_all = st.checkbox("ฉันเข้าใจว่าข้อมูลทั้งหมดจะถูกลบ (ระบบจะแบ็คอัพสำรองไว้อัตโนมัติ 1 ชุดก่อนลบเสมอ)")
            if confirm_all and st.button("🚨 ยืนยันล้างข้อมูลทั้งหมด (Clear All Data)", type="primary"):
                session_mgr.delete_all_sessions(auto_backup=True)
                st.success("ล้างข้อมูลทั้งหมดเรียบร้อย (มีไฟล์สำรองใน data/backups/ ปลอดภัย 100%)")
                time.sleep(1)
                st.rerun()

# Header
st.title("🎥 ระบบ Live Stream & Fact Engine วิเคราะห์กล้องวงจรปิดอัตโนมัติ")
st.caption("ระบบเชื่อมตรงกล้อง Xiaomi ผ่าน Cloud: มอนิเตอร์สดทุกกล้อง • ตรวจจับคนจริง • กรองพนักงาน • ไม่นับซ้ำ • บันทึก Fact ชัดเจน")

# === ROW 1: REAL CONNECTED CAMERAS STATUS ===
st.subheader("📡 กล้องทั้งหมดในระบบ (ตรวจพบสดจากบัญชีของคุณ)")

cam_cols = st.columns(min(len(CAMERAS), 4))
for i, cam in enumerate(CAMERAS[:4]):
    with cam_cols[i % 4]:
        is_on = cam.get("isOnline", False)
        status_badge = '<span class="status-online">🟢 ออนไลน์</span>' if is_on else '<span class="status-offline">⚪ ออฟไลน์</span>'
        st.markdown(f"""
        <div class="camera-card">
            <h4>📹 {cam.get('name')}</h4>
            <p style="margin: 4px 0;"><b>DID:</b> <code>{cam.get('did')}</code></p>
            <p style="margin: 4px 0;"><b>IP:</b> <code>{cam.get('localip', 'Cloud')}</code></p>
            <p style="margin: 4px 0;"><b>สถานะ:</b> {status_badge}</p>
        </div>
        """, unsafe_allow_html=True)

if len(CAMERAS) > 4:
    with st.expander(f"🔍 ดูกล้องและอุปกรณ์อื่นทั้งหมดในบัญชี ({len(ALL_DEVICES)} อุปกรณ์)"):
        dev_table = pd.DataFrame([{
            "DID": d.get("did"),
            "ชื่ออุปกรณ์": d.get("name"),
            "รุ่น (Model)": d.get("model"),
            "สถานะ": "🟢 ออนไลน์" if d.get("isOnline") else "⚪ ออฟไลน์",
            "IP Address": d.get("localip", "N/A")
        } for d in ALL_DEVICES])
        st.dataframe(dev_table, use_container_width=True)

st.divider()

# === ROW 2: LIVE STREAM & AUTO WORKFLOW CONTROLLER ===
st.subheader("🔴 มอนิเตอร์กล้องสด Real-Time & ระบบ Auto Workflow")

col_ctrl, col_live = st.columns([1, 1])

# Camera Selection
cam_options = {f"{c.get('name')} ({'🟢 ออนไลน์' if c.get('isOnline') else '⚪ ออฟไลน์'}) [DID: {c.get('did')}]": c for c in CAMERAS}
default_idx = 0
for idx, c in enumerate(CAMERAS):
    if c.get("isOnline"):
        default_idx = idx
        break

with col_ctrl:
    selected_label = st.selectbox("เลือกกล้องที่ต้องการดูสด/วิเคราะห์:", list(cam_options.keys()), index=default_idx)
    selected_device = cam_options[selected_label]
    did = selected_device.get("did")
    cam_name = selected_device.get("name")
    is_online = selected_device.get("isOnline", False)

    st.markdown(f"""
    - **ชื่อกล้อง:** `{cam_name}`
    - **Device ID (DID):** `{did}`
    - **สถานะการเชื่อมต่อ:** {'🟢 ออนไลน์ พร้อมดึงสัญญาณสด' if is_online else '⚪ ออฟไลน์ (เปิดกล้องที่ร้านแล้วจะออนไลน์ทันที)'}
    """)

    btn_auto = st.button("⚡ สั่ง Auto Workflow ตรวจจับภาพสด + วิเคราะห์ AI + สร้าง Fact Data ทันที", type="primary", use_container_width=True)
    btn_snap = st.button("📸 ดึงภาพสด (Capture Live Snapshot พร้อมลายน้ำ)", use_container_width=True)
    btn_hls = st.button("▶️ โหลดสตรีมวิดีโอสด HLS Real-Time", use_container_width=True)

    if btn_auto:
        with st.spinner(f"📡 กำลังดึงภาพสดจากกล้อง '{cam_name}' และรัน YOLO Computer Vision..."):
            res, err = execute_auto_workflow_for_camera(did, cam_name)
            if res:
                if res.get("status") == "EMPTY" or res.get("people_count", 0) == 0:
                    st.info(f"ℹ️ {res.get('message')}")
                else:
                    st.success(f"🎉 ตรวจพบบุคคลจริง! รหัส `{res.get('party_code')}` | นับได้ `{res.get('people_count')}` คน จากกล้อง `{cam_name}`")
                time.sleep(1)
                st.rerun()
            else:
                st.error(f"❌ เกิดข้อผิดพลาด: {err}")

    if btn_snap:
        with st.spinner(f"📸 กำลังสั่งแคปเจอร์ภาพสดพร้อมลายน้ำกล้อง..."):
            snap_path = capture_live_frame(did, camera_name=cam_name)
            if snap_path and os.path.exists(snap_path):
                st.success(f"✅ บันทึกภาพสดสำเร็จ! ({os.path.getsize(snap_path)} bytes)")
                time.sleep(1)
                st.rerun()
            else:
                st.warning("⚠️ ไม่สามารถดึงภาพสดได้ กล้องอาจกำลังเตรียมสัญญาณ กรุณาลองใหม่อีกครั้ง")

with col_live:
    live_mode = st.radio("รูปแบบการรับชมสด:", ["📸 ภาพสด Real-Time (รายวินาที)", "👥 มอนิเตอร์สดทุกกล้องที่ออนไลน์ (Grid View)", "▶️ วิดีโอสตรีมสด (HLS Player)"], horizontal=True)

    if live_mode == "▶️ วิดีโอสตรีมสด (HLS Player)" or btn_hls:
        st.markdown(f'<span class="live-badge">● LIVE HLS STREAM: {cam_name}</span>', unsafe_allow_html=True)
        hls_stream_url = get_camera_stream_url(did)
        if hls_stream_url:
            components.html(f"""
            <div style="background:#000; border-radius:12px; overflow:hidden; position:relative; box-shadow:0 4px 12px rgba(0,0,0,0.3);">
                <div style="position:absolute; top:12px; left:16px; z-index:10; background:rgba(0,0,0,0.65); padding:6px 12px; border-radius:6px; color:#00ffb4; font-family:sans-serif; font-size:13px; font-weight:bold;">
                    📹 {cam_name} [DID: {did}]
                </div>
                <div style="position:absolute; top:12px; right:16px; z-index:10; background:rgba(220,38,38,0.85); padding:6px 12px; border-radius:6px; color:#fff; font-family:sans-serif; font-size:12px; font-weight:bold;">
                    ● LIVE
                </div>
                <video id="hlsVideo" controls autoplay muted playsinline style="width:100%; height:320px; display:block; object-fit:contain; background:#000;"></video>
            </div>
            <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
            <script>
                var video = document.getElementById('hlsVideo');
                var videoSrc = '{hls_stream_url}';
                if (Hls.isSupported()) {{
                    var hls = new Hls({{
                        liveSyncDurationCount: 2,
                        maxLiveSyncPlaybackRate: 1.5,
                        enableWorker: true
                    }});
                    hls.loadSource(videoSrc);
                    hls.attachMedia(video);
                    hls.on(Hls.Events.MANIFEST_PARSED, function() {{
                        video.play();
                    }});
                }} else if (video.canPlayType('application/vnd.apple.mpegurl')) {{
                    video.src = videoSrc;
                    video.addEventListener('loadedmetadata', function() {{
                        video.play();
                    }});
                }}
            </script>
            """, height=340)
        else:
            st.warning("⚠️ สัญญาณสตรีม HLS จาก Cloud กำลังเตรียมพร้อม กดปุ่ม '▶️ โหลดสตรีมวิดีโอสด HLS' เพื่อเรียกสัญญาณใหม่")
            
    elif live_mode == "👥 มอนิเตอร์สดทุกกล้องที่ออนไลน์ (Grid View)":
        st.markdown(f'<span class="live-badge">● DUAL CAMERA LIVE GRID</span>', unsafe_allow_html=True)
        
        @st.fragment(run_every="1s")
        def render_dual_grid():
            online_c = [c for c in CAMERAS if c.get("isOnline")]
            if not online_c:
                st.info("ไม่มีกล้องออนไลน์ขณะนี้")
                return
            g_cols = st.columns(len(online_c))
            for i, c in enumerate(online_c):
                with g_cols[i]:
                    c_did = c["did"]
                    c_name = c["name"]
                    c_file = f"data/live_cam_{c_did}.jpg"
                    if not os.path.exists(c_file):
                        c_file = "data/live_camera_frame.jpg"
                    if os.path.exists(c_file):
                        mod_time = datetime.fromtimestamp(os.path.getmtime(c_file)).strftime("%H:%M:%S")
                        st.image(c_file, caption=f"📹 {c_name} ({mod_time})", use_container_width=True)
                    else:
                        st.info(f"📹 {c_name} (กำลังเตรียมสัญญาณ...)")

        render_dual_grid()

    else:
        st.markdown(f'<span class="live-badge">● LIVE REAL-TIME FEED: {cam_name}</span>', unsafe_allow_html=True)
        
        @st.fragment(run_every="1s")
        def render_live_monitor(target_cam, target_did):
            cam_path = f"data/live_cam_{target_did}.jpg"
            if not os.path.exists(cam_path):
                cam_path = "data/live_camera_frame.jpg"
                
            if os.path.exists(cam_path):
                mod_time = datetime.fromtimestamp(os.path.getmtime(cam_path)).strftime("%Y-%m-%d %H:%M:%S")
                st.image(cam_path, caption=f"ภาพสด Real-Time (อัปเดตอัตโนมัติรายวินาที: {mod_time})", use_container_width=True)
            else:
                st.info(f"กำลังดึงสัญญาณสดจาก {target_cam}...")

        render_live_monitor(cam_name, did)

st.divider()

# === ROW 3: FACT DATA SUMMARY & KPIS ===
@st.fragment(run_every="2s")
def render_fact_section(filter_staff_active):
    # If filter staff active, KPIs only count CUSTOMER
    role_kpi = "CUSTOMER" if filter_staff_active else None
    df_kpi = load_data(role_kpi)
    df_all = load_data(None)

    total_people = int(df_kpi["people_count"].sum()) if not df_kpi.empty else 0
    total_parties = len(df_kpi)
    avg_duration = round(df_kpi["duration_minutes"].mean(), 1) if not df_kpi.empty else 0.0
    total_pants = int(df_kpi["pants_touched"].sum()) if not df_kpi.empty else 0
    fitting_entries = int(df_kpi["entered_fitting_room"].sum()) if not df_kpi.empty else 0

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.metric(label="👥 ยอดลูกค้าจริง (หัว)", value=f"{total_people} คน")
    with k2:
        st.metric(label="🏷️ จำนวนกลุ่มลูกค้า (เจ้า)", value=f"{total_parties} เจ้า")
    with k3:
        st.metric(label="⏳ เวลาเฉลี่ยในร้าน", value=f"{avg_duration} นาที")
    with k4:
        st.metric(label="👖 กางเกงที่ถูกจับจริง", value=f"{total_pants} ตัว")
    with k5:
        conv = round((fitting_entries / total_parties * 100), 1) if total_parties > 0 else 0
        st.metric(label="🚪 เข้าห้องลองจริง", value=f"{fitting_entries} เจ้า ({conv}%)")

    st.divider()

    # === TABS ===
    tab1, tab2, tab3 = st.tabs(["📋 Fact Data ตารางสรุปข้อมูลจริง (Pure Fact 100%)", "📸 แกลเลอรีภาพ Snapshot & วิดีโอบันทึกเหตุการณ์", "📈 กราฟสถิติพฤติกรรมลูกค้า"])

    with tab1:
        view_filter = st.radio("มุมมองข้อมูล:", ["👥 ลูกค้าจริงเท่านั้น", "🧑‍💼 พนักงานประจำ", "📋 ข้อมูลทั้งหมด"], horizontal=True)
        if view_filter == "👥 ลูกค้าจริงเท่านั้น":
            table_source = load_data("CUSTOMER")
        elif view_filter == "🧑‍💼 พนักงานประจำ":
            table_source = load_data("STAFF")
        else:
            table_source = df_all

        st.subheader("ตารางบันทึกข้อมูลลูกค้าแต่ละเจ้า (Fact Data ถาวรใน SQLite)")
        if table_source.empty:
            st.info("ℹ️ ปัจจุบันยังไม่มีข้อมูลบันทึกในหมวดนี้ (Fact Data จะถูกสร้างเฉพาะเมื่อตรวจพบบุคคลจริงในกล้องเท่านั้น)")
        else:
            display_cols = ["camera_name", "party_code", "role", "start_time", "end_time", "duration_minutes", "people_count", "description", "pants_touched", "entered_fitting_room", "status"]
            available_cols = [c for c in display_cols if c in table_source.columns]
            table_df = table_source[available_cols].copy()
            
            col_rename = {
                "camera_name": "กล้องที่ตรวจพบ",
                "party_code": "รหัสเจ้า",
                "role": "ประเภท",
                "start_time": "เวลาเข้า",
                "end_time": "เวลาออก",
                "duration_minutes": "ระยะเวลา (นาที)",
                "people_count": "จำนวนคน",
                "description": "พฤติกรรม/ลักษณะ",
                "pants_touched": "จับกางเกง (ตัว)",
                "entered_fitting_room": "เข้าห้องลอง",
                "status": "สถานะ"
            }
            table_df.rename(columns=col_rename, inplace=True)
            if "ประเภท" in table_df.columns:
                table_df["ประเภท"] = table_df["ประเภท"].apply(lambda x: "🧑‍💼 พนักงาน" if x == "STAFF" else "👥 ลูกค้า")
            if "เข้าห้องลอง" in table_df.columns:
                table_df["เข้าห้องลอง"] = table_df["เข้าห้องลอง"].apply(lambda x: "✅ ได้ลอง" if x == 1 else "❌ ไม่ได้ลอง")
            if "สถานะ" in table_df.columns:
                table_df["สถานะ"] = table_df["สถานะ"].apply(lambda x: "🟢 กำลังอยู่ในเฟรม" if x == "ACTIVE" else "⚪ สิ้นสุดการตรวจ")

            st.dataframe(table_df, use_container_width=True, height=350)

            csv = table_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 ดาวน์โหลดข้อมูลเป็น Excel / CSV",
                data=csv,
                file_name=f"store_analytics_facts_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

    with tab2:
        st.subheader("หลักฐานภาพถ่าย Snapshot & วิดีโอคลิปบันทึกเหตุการณ์ (H.264 Playable)")
        if df_all.empty:
            st.info("ยังไม่มีข้อมูลหลักฐาน (เมื่อตรวจพบบุคคลจริง ภาพและคลิปจะแสดงที่นี่)")
        else:
            cols = st.columns(3)
            for i, (idx, row) in enumerate(df_all.iterrows()):
                with cols[i % 3]:
                    cam_label = row.get("camera_name", "กล้องวงจรปิด")
                    role_badge = "🧑‍💼 พนักงาน" if row.get("role") == "STAFF" else "👥 ลูกค้า"
                    st.markdown(f"**กล้อง:** `{cam_label}` | **รหัส:** `{row['party_code']}` ({role_badge})")
                    st.write(f"👥 มา {row['people_count']} คน | 👖 จับกางเกง {row['pants_touched']} ตัว")
                    st.caption(f"⏱️ เวลา: {row['start_time']} (อยู่ {row['duration_minutes']} นาที)")
                    
                    # Snapshots Gallery
                    snaps_list = []
                    if "all_snapshots" in row and row["all_snapshots"]:
                        try:
                            snaps_list = json.loads(row["all_snapshots"])
                        except Exception:
                            pass
                    if not snaps_list and row["snapshot_path"]:
                        snaps_list = [row["snapshot_path"]]
                        
                    valid_snaps = [s for s in snaps_list if os.path.exists(s)]
                    if valid_snaps:
                        if len(valid_snaps) == 1:
                            st.image(valid_snaps[0], use_container_width=True)
                        else:
                            st.image(valid_snaps[:4], caption=[os.path.basename(s).split("_")[-1].replace(".jpg", "") for s in valid_snaps[:4]], use_container_width=True)
                        
                    # Video Clips (supports single or multi-camera clips)
                    clips_list = []
                    if "all_clips" in row and row["all_clips"]:
                        try:
                            clips_list = json.loads(row["all_clips"])
                        except Exception:
                            pass
                    if not clips_list and row["clip_path"]:
                        clips_list = [row["clip_path"]]
                        
                    for c_path in clips_list:
                        if os.path.exists(c_path):
                            st.markdown(f"**🎬 วิดีโอบันทึกเหตุการณ์ ({os.path.basename(c_path)}):**")
                            st.video(c_path)
                    st.divider()

    with tab3:
        st.subheader("สถิติภาพรวมพฤติกรรมลูกค้า")
        if not df_kpi.empty:
            g1, g2 = st.columns(2)
            with g1:
                st.write("📊 สถิติจำนวนคนที่มาต่อกลุ่ม (เจ้า)")
                st.bar_chart(df_kpi["people_count"].value_counts())
            with g2:
                st.write("👖 สถิติจำนวนกางเกงที่ถูกหยิบจับต่อกลุ่ม")
                st.bar_chart(df_kpi["pants_touched"].value_counts())

render_fact_section(filter_staff)
