import os
import sys
import time
from netmiko import ConnectHandler
from gns3fy import Gns3Connector, Project

GNS3_IP = "192.168.56.102"
GNS3_URL = f"http://{GNS3_IP}:80"
PROJECT_NAME = "a"

IP_PLAN = {
    "AlpineLinux-1": ("11.0.0.2",  "11.0.0.1"),
    "AlpineLinux-2": ("10.0.0.11", "10.0.0.1"),
    "AlpineLinux-3": ("10.0.0.12", "10.0.0.1"),
    "AlpineLinux-4": ("10.1.0.10", "10.1.0.1"),
    "AlpineLinux-5": ("10.1.0.11", "10.1.0.1")
}

def main():
    sys.stdout.reconfigure(line_buffering=True)
    try:
        server = Gns3Connector(url=GNS3_URL)
        project = Project(name=PROJECT_NAME, connector=server)
        project.get()
        project.get_nodes()

        ssh = ConnectHandler(
            device_type='terminal_server',
            host=GNS3_IP,
            username='gns3',
            password='gns3',
            port=22
        )
        
        print("--- Valomas GNS3 terminalas ---")
        # Išeiname iš meniu (Enter kelis kartus ir 7)
        for _ in range(2): ssh.write_channel("\r"); time.sleep(1)
        ssh.write_channel("7\r"); time.sleep(3)
        
        # Svarbu: Priverstinai išvalome terminalo šiukšles
        ssh.write_channel("stty cols 200 && reset\r")
        time.sleep(4)
        ssh.read_channel() # Išmetame šiukšles

        for node in project.nodes:
            if node.node_type == "docker" and node.name in IP_PLAN:
                ip, gw = IP_PLAN[node.name]
                print(f"\n[PROCESS] Mazgas: {node.name}")

                # Siunčiame užklausą ir gauname tik grynus ID
                ssh.write_channel(f"docker ps -q --filter \"label=com.gns3.node.id={node.node_id}\"\r")
                time.sleep(2)
                
                output = ssh.read_channel()
                container_id = None
                
                # Ieškome 12 simbolių kodo tarp visų eilučių
                for line in output.splitlines():
                    clean = line.strip()
                    if len(clean) == 12 and clean.isalnum():
                        container_id = clean
                        break

                if container_id:
                    print(f"  -> Rasta ID: {container_id}. Konfigūruojama...")
                    ssh.write_channel(f"docker exec {container_id} ip addr flush dev eth0\r")
                    ssh.write_channel(f"docker exec {container_id} ip addr add {ip}/24 dev eth0\r")
                    ssh.write_channel(f"docker exec {container_id} ip link set eth0 up\r")
                    ssh.write_channel(f"docker exec {container_id} ip route add default via {gw}\r")
                    time.sleep(1)
                else:
                    print(f"  -> [!] ID nerastas. Debug logas: {output.replace(chr(27), '[ESC]')[:60]}")

        ssh.disconnect()
        print("\n[SUCCESS] Konfigūracija baigta.")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
