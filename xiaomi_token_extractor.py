"""
Xiaomi Cloud Token & Device Extractor
Connects to Xiaomi Cloud to retrieve the camera's Device ID and P2P connection token.
"""
import sys
import getpass

def extract():
    print("=" * 60)
    print("🔑 Xiaomi Cloud Camera Connection Tool")
    print("=" * 60)
    print("เครื่องมือนี้จะดึง Device ID และ Token ของกล้อง Mi Home 1080p")
    print("เพื่อส่งต่อให้ Cloud Worker สตรีมภาพฟรีได้ตลอด 24 ชม.")
    print("-" * 60)

    user = input("กรุณากรอก Mi Account (Email หรือ เบอร์โทร หรือ Mi ID): ").strip()
    password = getpass.getpass("กรุณากรอกรหัสผ่าน Mi Account: ").strip()
    server = input("เลือก Server (ค่าเริ่มต้น 'sg' สำหรับสิงคโปร์/ไทย): ").strip() or "sg"

    print(f"\nกำลังเชื่อมต่อ Xiaomi Cloud ({server})...")
    try:
        # Check if micloud is installed
        from micloud import MiCloud
        mc = MiCloud(user, password)
        if mc.login():
            print("✅ เข้าสู่ระบบ Xiaomi Cloud สำเร็จ!")
            devices = mc.get_devices(country=server)
            print(f"\nพบอุปกรณ์ทั้งหมด {len(devices)} ชิ้น:")
            for d in devices:
                name = d.get("name", "Unnamed")
                model = d.get("model", "Unknown")
                did = d.get("did", "")
                token = d.get("token", "")
                print(f"👉 ชื่อ: {name} | รุ่น (Model): {model} | Device ID: {did}")
                if "camera" in model or "ipc" in model:
                    print(f"   🎯 กล้องตรวจจับ: Model={model}, DID={did}, Token={token}")
        else:
            print("❌ ล็อกอินไม่สำเร็จ กรุณาตรวจสอบ Username / Password")
    except ImportError:
        print("💡 กำลังติดตั้งไลบรารี micloud...")
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "micloud"])
        print("ติดตั้งเสร็จแล้ว กรุณารันคำสั่งนี้อีกครั้ง")

if __name__ == "__main__":
    extract()
