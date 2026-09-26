import socket

ip = "192.168.1.120"
ports = [21, 22, 23, 80, 443, 554, 1935, 54321, 8080, 8554]

print(f"Scanning open ports on Xiaomi device {ip}...")
open_ports = []
for p in ports:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1.0)
    res = s.connect_ex((ip, p))
    if res == 0:
        open_ports.append(p)
        print(f"  [OPEN] Port {p}")
    s.close()

print(f"Open ports on {ip}: {open_ports}")
