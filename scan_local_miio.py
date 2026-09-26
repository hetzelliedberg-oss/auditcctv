import socket
import binascii
import time

def scan_local_xiaomi():
    print("Scanning local Wi-Fi network (Lopburi) for Xiaomi cameras/devices...")
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.settimeout(3.0)

    # Xiaomi discovery packet (Hello handshake)
    hello_packet = bytes.fromhex("21310020ffffffffffffffffffffffffffffffffffffffffffffffffffffffff")
    
    # Send broadcast to port 54321
    s.sendto(hello_packet, ("<broadcast>", 54321))
    
    start = time.time()
    devices = []
    while time.time() - start < 4.0:
        try:
            data, addr = s.recvfrom(1024)
            if len(data) >= 32:
                header = data[:4]
                length = int.from_bytes(data[2:4], 'big')
                did = data[8:12].hex()
                ts = int.from_bytes(data[12:16], 'big')
                checksum = data[16:32].hex()
                devices.append({
                    "ip": addr[0],
                    "port": addr[1],
                    "did": did,
                    "checksum": checksum,
                    "raw": data.hex()
                })
                print(f"[FOUND] Xiaomi device on local network! IP: {addr[0]}, Device ID (hex): {did}")
        except socket.timeout:
            break
        except Exception as e:
            print(f"Error: {e}")
            break
            
    s.close()
    print(f"Local scan completed. Found {len(devices)} Xiaomi device(s).")
    return devices

if __name__ == "__main__":
    scan_local_xiaomi()
