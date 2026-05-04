import os
import sys
import time
import requests
from gns3fy import Gns3Connector, Project

# Nustatymai
GNS3_IP = "192.168.56.102"
GNS3_URL = f"http://{GNS3_IP}:80"
PROJECT_NAME = "a"

# IP Planas
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
        print(f"[INFO] Jungiamasi prie GNS3 API: {GNS3_URL}")
        server = Gns3Connector(url=GNS3_URL)
        project = Project(name=PROJECT_NAME, connector=server)
        project.get()
        project.get_nodes()

        for node in project.nodes:
            if node.node_type == "docker" and node.name in IP_PLAN:
                ip, gw = IP_PLAN[node.name]
                print(f"\n[PROCESS] Mazgas: {node.name}")
                
                # Naudojame tiesioginį GNS3 API kvietimą komandoms vykdyti konteineryje
                # Tai apeina bet kokius SSH meniu ar terminalo simbolius
                exec_url = f"{GNS3_URL}/v2/projects/{project.project_id}/nodes/{node.node_id}/docker/exec"
                
                cmds = [
                    f"ip addr flush dev eth0",
                    f"ip addr add {ip}/24 dev eth0",
                    f"ip link set eth0 up",
                    f"ip route add default via {gw}"
                ]
                
                for cmd in cmds:
                    # Siunčiame komandą per HTTP POST
                    payload = {"command": cmd}
                    response = requests.post(exec_url, json=payload)
                    if response.status_code == 200 or response.status_code == 201:
                        print(f"  -> [OK] {cmd}")
                    else:
                        print(f"  -> [!] Klaida vykdant '{cmd}': {response.text}")
                    time.sleep(0.5)

        print("\n[SUCCESS] Visų Docker mazgų konfigūracija baigta per API.")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
