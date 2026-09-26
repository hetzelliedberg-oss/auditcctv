"""
Selenium Xiaomi Cloud Authenticator
Opens Chrome on user's desktop, logs in, and waits for user authentication.
"""
import time
import json
import os
import sys

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

def run():
    print("=" * 60)
    print("🚀 เปิดหน้าต่าง Chrome เพื่อเข้าสู่ระบบ Xiaomi...")
    print("=" * 60)

    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        # Navigate to Xiaomi Account login
        driver.get("https://account.xiaomi.com/pass/serviceLogin?sid=xiaomiio&_json=false")
        time.sleep(3)

        print("👉 กำลังใส่เบอร์และรหัสผ่าน...")
        try:
            user_input = driver.find_element(By.NAME, "account")
            user_input.clear()
            user_input.send_keys("+66830737979")
            time.sleep(1)

            pwd_input = driver.find_element(By.NAME, "password")
            pwd_input.clear()
            pwd_input.send_keys("P*awin123123")
            time.sleep(1)

            submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            submit_btn.click()
            print("✅ กดปุ่มล็อกอินเรียบร้อย")
        except Exception as e:
            print(f"ℹ️ ฟอร์มล็อกอิน: {e}")

        print("\n⏳ กำลังรอการยืนยัน... (หากมีให้เลื่อนจิ๊กซอว์ หรือกรอก OTP ในหน้าต่าง Chrome ที่เปิดขึ้นมา ให้กดได้เลยครับ)")
        
        # Wait up to 3 minutes for user to solve captcha/OTP if any
        authenticated = False
        for i in range(90):
            time.sleep(2)
            current_url = driver.current_url
            cookies = driver.get_cookies()
            cookie_dict = {c["name"]: c["value"] for c in cookies}
            
            # Check if userId and serviceToken or cUserId are present
            if "userId" in cookie_dict and ("serviceToken" in cookie_dict or "passToken" in cookie_dict):
                print("\n🎉 ล็อกอินสำเร็จ 100%! ดึง Token สำเร็จแล้ว!")
                print(f"User ID: {cookie_dict.get('userId')}")
                authenticated = True
                
                # Now navigate to Miot device list using this session
                driver.get("https://api.io.mi.com/app/v2/home/home_device_list")
                time.sleep(2)
                page_source = driver.page_source
                
                token_file = os.path.join(os.path.dirname(__file__), "data", "xiaomi_session.json")
                with open(token_file, "w", encoding="utf-8") as f:
                    json.dump(cookie_dict, f, indent=2)
                print(f"💾 บันทึก Token เรียบร้อยที่: {token_file}")
                break
            else:
                if i % 5 == 0:
                    print(f"[{i*2}s] สถานะ: กำลังรอที่ URL: {current_url[:60]}...")

        if not authenticated:
            print("⚠️ หมดเวลาการรอ (3 นาที)")

    finally:
        time.sleep(2)
        driver.quit()

if __name__ == "__main__":
    run()
