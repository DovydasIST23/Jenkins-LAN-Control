import os
import sys
import time
from netmiko import ConnectHandler
from gns3fy import Gns3Connector, Project

GNS3_IP = "192.168.56.102"
GNS3_URL = f"http://{GNS3_IP}:80"
PROJECT_NAME = "a"

# IP Planas eilės tvarka
IP_LIST = [
    ("11.0.0.2", "11.0.0.1"),   # Pirmas rastas Alpine
    ("10.0.0.11", "10.0.0.1"),  # Antras
    ("10.0.0.12", "10.0.0.1"),  # Trečias
    ("10.1.0.10", "10.1.0.1"),  # Ketvirtas
    ("10.1.0.11", "10.1.0.1")   # Penktas
]

def main():
    sys.stdout.reconfigure(line_buffering=True)
    try:
        ssh = ConnectHandler(
            device_type='terminal_server',
            host=GNS3_IP,
            username='gns3',
            password='gns3',
            port=22
        )
        
        print("--- Valomas terminalas ir jungiamasi prie Docker ---")
        # Išeiname į Shell (agresyviai)
        for _ in range(2): ssh.write_channel("\r"); time.sleep(1)
        ssh.write_channel("7\r"); time.sleep(2)
        ssh.write_channel("stty rows 100 cols 200\r"); time.sleep(1)
        ssh.read_channel() # Išvalome šiukšles

        # Gauname visų veikiančių Alpine konteinerių ID
        print("[INFO] Gaunami Alpine konteinerių ID...")
        ssh.write_channel("docker ps --filter 'ancestor=alpine:latest' -q\r")
        time.sleep(2)
        
        output = ssh.read_channel()
        # Išrenkame tik grynus 12 simbolių ID
        ids = [line.strip() for line in output.splitlines() if len(line.strip()) == 12 and line.strip().isalnum()]
        
        if not ids:
            print(f"[!] Nerasta jokių Alpine ID. Atsakymas: {output[:50]}")
            return

        print(f"[OK] Rasta konteinerių: {len(ids)}")

        for i, container_id in enumerate(ids):
            if i >= len(IP_LIST): break
            
            ip, gw = IP_LIST[i]
            print(f"  -> Konfigūruojamas konteineris {container_id} su IP {ip}")
            
            # Siunčiame komandas aklai
            ssh.write_channel(f"docker exec {container_id} ip addr flush dev eth0\r")
            ssh.write_channel(f"docker exec {container_id} ip addr add {ip}/24 dev eth0\r")
            ssh.write_channel(f"docker exec {container_id} ip link set eth0 up\r")
            ssh.write_channel(f"docker exec {container_id} ip route add default via {gw}\r")
            time.sleep(1)

        ssh.disconnect()
        print("\n[SUCCESS] Alpine konfigūracija baigta.")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
