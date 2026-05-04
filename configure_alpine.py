import os
import sys
import time
from netmiko import ConnectHandler

GNS3_IP = "192.168.56.102"

# IP Planas eilės tvarka (konfigūruosime tiek, kiek rasime)
IP_LIST = [
    ("11.0.0.2", "11.0.0.1"),
    ("10.0.0.11", "10.0.0.1"),
    ("10.0.0.12", "10.0.0.1"),
    ("10.1.0.10", "10.1.0.1"),
    ("10.1.0.11", "10.1.0.1")
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
        
        print("--- BRUTALUS terminalo valymas ---")
        # 1. Priverstinai išeiname iš bet kokių langų ir užmušame meniu procesą
        ssh.write_channel("\r\r")
        time.sleep(1)
        # Ši komanda nužudo GNS3 meniu procesą, kad jis daugiau nepieštų ekrane
        ssh.write_channel("sudo pkill -f gns3vm-menu\r")
        time.sleep(2)
        # Patekome į gryną shell
        ssh.write_channel("reset && stty cols 200 rows 100\r")
        time.sleep(3)
        ssh.read_channel() # Išvalome šiukšles

        # 2. Gauname ID (naudojame ancestor, kad rastume tik Alpine)
        print("[INFO] Užklausiamas Docker sąrašas...")
        ssh.write_channel("docker ps --filter 'ancestor=alpine:latest' -q\r")
        time.sleep(2)
        
        output = ssh.read_channel()
        # Išvalome ANSI kodus iš ID sąrašo (paimame tik 12 simbolių šešioliktainius)
        raw_ids = output.replace('\r', '').split('\n')
        ids = [line.strip() for line in raw_ids if len(line.strip()) == 12 and line.strip().isalnum()]
        
        if not ids:
            print(f"[!] ID nerasta. Terminalo šiukšlės: {repr(output[:100])}")
            return

        print(f"[OK] Rasta Alpine konteinerių: {len(ids)}")

        for i, container_id in enumerate(ids):
            if i >= len(IP_LIST): break
            
            ip, gw = IP_LIST[i]
            print(f"  -> Konfigūruojamas {container_id} -> IP: {ip}")
            
            # Konfigūruojame
            cmds = [
                f"docker exec {container_id} ip addr flush dev eth0\r",
                f"docker exec {container_id} ip addr add {ip}/24 dev eth0\r",
                f"docker exec {container_id} ip link set eth0 up\r",
                f"docker exec {container_id} ip route add default via {gw}\r"
            ]
            for c in cmds:
                ssh.write_channel(c)
                time.sleep(1)

        ssh.disconnect()
        print("\n[SUCCESS] Konfigūracija sėkmingai baigta!")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
