import os
import sys
import time
from netmiko import ConnectHandler
from gns3fy import Gns3Connector, Project

# --- KONFIGŪRACIJA ---
GNS3_IP = "192.168.56.102"
GNS3_URL = f"http://{GNS3_IP}:80"
PROJECT_NAME = "a"

# IP Planas: Mazgo vardas GNS3 -> (IP adresas, Gateway)
IP_PLAN = {
    "AlpineLinux-1": ("11.0.0.2",  "11.0.0.1"),
    "AlpineLinux-2": ("10.0.0.11", "10.0.0.1"),
    "AlpineLinux-3": ("10.0.0.12", "10.0.0.1"),
    "AlpineLinux-8": ("10.1.0.10", "10.1.0.1"),
    "AlpineLinux-9": ("10.1.0.11", "10.1.0.1"),
    "AlpineLinux-10": ("10.2.0.10", "10.2.0.1")
}

def main():
    # Užtikriname, kad logai matytųsi Jenkins lange iškart
    sys.stdout.reconfigure(line_buffering=True)
    
    try:
        print(f"[INFO] Jungiamasi prie GNS3 projekto: {PROJECT_NAME}")
        server = Gns3Connector(url=GNS3_URL)
        project = Project(name=PROJECT_NAME, connector=server)
        project.get()
        project.get_nodes()

        # Prisijungimo prie GNS3 VM parametrai
        # Naudojame 'generic_termserver_telnet', kad išvengtume SSH prompt klaidų
        vm_params = {
            'device_type': 'generic_termserver_telnet',
            'host': GNS3_IP,
            'username': 'gns3',
            'password': 'gns3',
            'port': 22,
        }

        print(f"[INFO] Jungiamasi prie GNS3 VM SSH ({GNS3_IP})...")
        ssh = ConnectHandler(**vm_params)
        
        # 1. Priverstinai išeiname iš GNS3 meniu į Shell (dažniausiai parinktis Nr. 7)
        print("[DEBUG] Bandoma išeiti iš GNS3 meniu į Shell...")
        ssh.write_channel("7\r")
        time.sleep(2)
        ssh.read_channel() # Išvalome buferį

        for node in project.nodes:
            if node.node_type == "docker" and node.name in IP_PLAN:
                ip, gw = IP_PLAN[node.name]
                print(f"\n[PROCESS] Konfigūruojamas mazgas: {node.name}")

                # Surandame Docker ID pagal GNS3 Node ID
                cmd_get_id = f"docker ps -q --filter 'label=com.gns3.node.id={node.node_id}'\r"
                ssh.write_channel(cmd_get_id)
                time.sleep(1)
                
                output = ssh.read_channel().splitlines()
                container_id = None
                for line in reversed(output):
                    clean_line = line.strip()
                    if len(clean_line) >= 12 and clean_line.isalnum():
                        container_id = clean_line
                        break

                if container_id:
                    print(f"  -> Rasta Docker ID: {container_id}")
                    # Siunčiame tinklo konfigūracijos komandas
                    cfg_cmds = [
                        f"docker exec {container_id} ip addr flush dev eth0\r",
                        f"docker exec {container_id} ip addr add {ip}/24 dev eth0\r",
                        f"docker exec {container_id} ip link set eth0 up\r",
                        f"docker exec {container_id} ip route add default via {gw}\r"
                    ]
                    for cfg in cfg_cmds:
                        ssh.write_channel(cfg)
                        time.sleep(0.5)
                    print(f"  -> [OK] IP {ip} nustatytas sėkmingai.")
                else:
                    print(f"  -> [!] ERROR: Konteineris mazgui {node.name} nerastas.")

        ssh.disconnect()
        print("\n[FINISH] Alpine mazgų konfigūravimas baigtas.")

    except Exception as e:
        print(f"\n[CRITICAL ERROR] {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
