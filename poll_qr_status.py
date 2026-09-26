import requests
import json
import time
import sys
import base64
import hashlib
import hmac
from Crypto.Cipher import ARC4

sys.stdout.reconfigure(encoding='utf-8')

def poll_and_fetch():
    with open("data/qr_login_info.json", "r", encoding="utf-8") as f:
        info = json.load(f)

    lp_url = info["lp_url"]
    print("Waiting for user to scan QR code with Mi Home app...")
    
    session = requests.Session()
    # Poll for up to 3 minutes
    for i in range(90):
        try:
            r = session.get(lp_url, timeout=5)
            text = r.text.replace("&&&START&&&", "")
            d = json.loads(text)
            code = d.get("code")
            desc = d.get("desc")
            
            # code 0: confirmed login!
            if code == 0:
                print("\n🎉 SUCCESS! QR Code confirmed by Mi Home app!")
                location = d.get("location")
                user_id = d.get("userId")
                ssecurity = d.get("ssecurity")
                
                # Fetch serviceToken from location
                r_sts = session.get(location)
                cookies = session.cookies.get_dict()
                service_token = cookies.get("serviceToken")
                
                credentials = {
                    "userId": str(user_id),
                    "ssecurity": ssecurity,
                    "serviceToken": service_token,
                    "cookies": cookies
                }
                
                with open("data/authenticated_credentials.json", "w", encoding="utf-8") as f:
                    json.dump(credentials, f, indent=2)
                print(f"Saved authenticated credentials to data/authenticated_credentials.json!")
                
                # Fetch devices!
                fetch_all_devices(credentials)
                return True
            elif code == 70014: # Expired
                print("QR code expired. Please generate a new one.")
                return False
            else:
                if i % 5 == 0:
                    print(f"[{i*2}s] Waiting for scan... Status: {desc} (code {code})")
        except Exception as e:
            pass
        time.sleep(2)
        
    print("Timed out.")
    return False

def fetch_all_devices(creds):
    print("\nFetching devices across regions (sg, cn, th)...")
    user_id = creds["userId"]
    ssecurity = creds["ssecurity"]
    service_token = creds["serviceToken"]
    
    for country in ["sg", "cn", "i2", "de", "us"]:
        url = f"https://{country + '.' if country != 'cn' else ''}api.io.mi.com/app/v2/home/home_device_list"
        headers = {
            "User-Agent": "Android-7.1.1-1.0.0-ONEPLUS A3010-136-APP-com.xiaomi.smarthome APPV/7.0.0",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        cookies = {
            "userId": str(user_id),
            "serviceToken": str(service_token),
            "yetAnotherServiceToken": str(service_token)
        }
        
        # Simple plain payload
        data = {
            "data": json.dumps({
                "get_split_device": True,
                "support_smart_home": True
            })
        }
        try:
            r = requests.post(url, headers=headers, cookies=cookies, data=data, timeout=5)
            res = r.json()
            if res.get("code") == 0:
                devices = res.get("result", {}).get("list", [])
                print(f"👉 Found {len(devices)} devices in region {country}:")
                for dev in devices:
                    print(f"   Name: {dev.get('name')} | Model: {dev.get('model')} | DID: {dev.get('did')} | Online: {dev.get('isOnline')}")
                if devices:
                    with open(f"data/devices_{country}.json", "w", encoding="utf-8") as f:
                        json.dump(devices, f, indent=2)
        except Exception as e:
            print(f"Error querying region {country}: {e}")

if __name__ == "__main__":
    poll_and_fetch()
