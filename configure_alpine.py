import os
import sys
import time
from netmiko import ConnectHandler
from gns3fy import Gns3Connector, Project

# --- KONFIGŪRACIJA ---
GNS3_IP = "192.168.56.102"
GNS3_URL = f"http://{GNS3_IP}:80"
PROJECT_NAME = "a"

IP_PLAN = {
    "AlpineLinux-1": ("11.0.0.2",  "11.0.0.1"),
    "AlpineLinux-2": ("10.0.0.11", "10.0.0.1"),
    "AlpineLinux-3": ("10.0.0.12", "10.0.0.1"),
    "AlpineLinux-8": ("10.1.0.10", "10.1.0.1"),
    "AlpineLinux-9": ("10.1.0.11", "10.1.0.1"),
    "AlpineLinux-10": ("10.2.0.10", "10.2.0.1")
}

def main():
    sys.stdout.reconfigure(line_buffering=True)
    
    try:
        # 1. Pirmiausia gauname projekto duomenis per HTTP (tai veikia stabiliai)
        print(f"[INFO] Jungiamasi prie GNS3 API...")
        server = Gns3Connector(url=GNS3_URL)
        project = Project(name=PROJECT_NAME, connector=server)
        project.get()
        project.get_nodes()

        # 2. SSH Prisijungimas su padidintais TIMEOUT
        vm_params = {
            'device_type': 'generic_termserver_telnet',
            'host': GNS3_IP,
            'username': 'gns3',
            'password': 'gns3',
            'port': 22,
            'fast_cli': False, # Neleidžiame skubėti
            'timeout': 30,     # Prailginame laukimą
        }

        print(f"[INFO] Atidariamas SSH ryšys su GNS3 VM ({GNS3_IP})...")
        ssh = ConnectHandler(**vm_params)
        
        # Suteikiame GNS3 VM laiko parodyti meniu
        time.sleep(5)
        
        print("[DEBUG] Siunčiamas '7' (Shell)...")
        ssh.write_channel("7\n")
        time.sleep(5) # Svarbi pauzė po Shell įėjimo
        
        # Išvalome buferį
        ssh.read_channel()

        for node in project.nodes:
            if node.node_type == "docker" and node.name in IP_PLAN:
                ip, gw = IP_PLAN[node.name]
                print(f"\n[PROCESS] Mazgas: {node.name}")

                # Naudojame tiesioginį write_channel, kad išvengtume 10053 klaidos laukiant prompto
                find_id_cmd = f"docker ps -q --filter 'label=com.gns3.node.id={node.node_id}'\n"
                ssh.write_channel(find_id_cmd)
                time.sleep(2)
                
                output = ssh.read_channel().splitlines()
                container_id = None
                for line in reversed(output):
                    clean = line.strip()
                    if len(clean) >= 12 and clean.isalnum():
                        container_id = clean
                        break

                if container_id:
                    print(f"  -> Rasta ID: {container_id}. Konfigūruojama...")
                    cmds = [
                        f"docker exec {container_id} ip addr flush dev eth0\n",
                        f"docker exec {container_id} ip addr add {ip}/24 dev eth0\n",
                        f"docker exec {container_id} ip link set eth0 up\n",
                        f"docker exec {container_id} ip route add default via {gw}\n"
                    ]
                    for c in cmds:
                        ssh.write_channel(c)
                        time.sleep(1)
                    print(f"  -> [OK] IP {ip} nustatytas.")
                else:
                    print(f"  -> [!] Konteineris nerastas.")

        ssh.disconnect()
        print("\n[FINISH] Viskas baigta.")

    except Exception as e:
        print(f"\n[CRITICAL ERROR] {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
