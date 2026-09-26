import socket
import concurrent.futures
import time

def check_ip(ip):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0.6)
    hello = bytes.fromhex("21310020ffffffffffffffffffffffffffffffffffffffffffffffffffffffff")
    try:
        s.sendto(hello, (ip, 54321))
        data, addr = s.recvfrom(1024)
        if len(data) >= 32:
            did_hex = data[8:12].hex()
            did_dec = int.from_bytes(data[8:12], 'big')
            s.close()
            return {"ip": ip, "did_hex": did_hex, "did_dec": did_dec, "raw": data.hex()}
    except:
        pass
    s.close()
    return None

def scan_all():
    print("Scanning entire subnet 192.168.1.1 - 254 for all 3 Xiaomi cameras...")
    base_ip = "192.168.1."
    all_ips = [f"{base_ip}{i}" for i in range(1, 255)]
    
    found = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        results = executor.map(check_ip, all_ips)
        for r in results:
            if r:
                found.append(r)
                print(f"[FOUND] IP: {r['ip']} | DID (Dec): {r['did_dec']} | DID (Hex): {r['did_hex']}")

    print(f"\nTotal Xiaomi devices found: {len(found)}")
    return found

if __name__ == "__main__":
    scan_all()
