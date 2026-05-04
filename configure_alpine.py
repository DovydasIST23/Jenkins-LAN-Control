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
    # Užtikriname, kad Jenkins matytų print() iškart
    sys.stdout.reconfigure(line_buffering=True)
    
    try:
        print(f"[1] Jungiamasi prie API: {GNS3_URL}")
        server = Gns3Connector(url=GNS3_URL)
        project = Project(name=PROJECT_NAME, connector=server)
        project.get()
        project.get_nodes()
        print(f"[OK] Projektas '{PROJECT_NAME}' rastas.")

        # NAUDOJAME 'linux' (SSH), nes jungiamės prie 22 porto
        vm_params = {
            'device_type': 'linux',
            'host': GNS3_IP,
            'username': 'gns3',
            'password': 'gns3',
            'port': 22,
            'global_delay_factor': 2,
        }

        print(f"[2] Atidariamas SSH ryšys (Port 22)...")
        ssh = ConnectHandler(**vm_params)
        
        # GNS3 VM prisijungus rodo meniu. Mums reikia išeiti į Shell (7).
        print("[3] Prisijungta. Siunčiamas '7' (Shell)...")
        time.sleep(2)
        ssh.write_channel("7\n")
        time.sleep(3)
        
        # Išvalome buferį ir pažiūrime, ar patekome į shell
        output = ssh.read_channel()
        print(f"--- TERMINALO ATSAKYMAS ---\n{output}\n--------------------------")

        for node in project.nodes:
            if node.node_type == "docker" and node.name in IP_PLAN:
                ip, gw = IP_PLAN[node.name]
                print(f"\n[NODE] {node.name} konfigūracija...")

                # Surandame Docker ID
                find_cmd = f"docker ps -q --filter 'label=com.gns3.node.id={node.node_id}'\n"
                ssh.write_channel(find_cmd)
                time.sleep(2)
                
                res = ssh.read_channel()
                container_id = None
                # Ieškome ID (12 simbolių eilutė)
                for line in res.splitlines():
                    clean = line.strip()
                    if len(clean) >= 12 and clean.isalnum():
                        container_id = clean
                        break

                if container_id:
                    print(f"  -> Rasta ID: {container_id}. Siunčiame IP: {ip}")
                    ssh.write_channel(f"docker exec {container_id} ip addr flush dev eth0\n")
                    ssh.write_channel(f"docker exec {container_id} ip addr add {ip}/24 dev eth0\n")
                    ssh.write_channel(f"docker exec {container_id} ip link set eth0 up\n")
                    ssh.write_channel(f"docker exec {container_id} ip route add default via {gw}\n")
                    time.sleep(1)
                else:
                    print("  -> [!] Konteinerio ID nerastas.")

        ssh.disconnect()
        print("\n[SUCCESS] Alpine konfigūracija baigta.")

    except Exception as e:
        print(f"\n[FATAL ERROR] {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
