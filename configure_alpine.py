import sys
import time
import requests  # Naudosime tiesioginėms užklausoms
from gns3fy import Gns3Connector, Project

# Nustatymai
GNS3_IP = "192.168.56.102"
GNS3_BASE_URL = f"http://{GNS3_IP}:80/v2"  # Pridedame /v2 versiją
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
    error_count = 0
    
    try:
        print(f"[INFO] Jungiamasi prie GNS3 API per: {GNS3_BASE_URL}")
        server = Gns3Connector(url=f"http://{GNS3_IP}:80")
        project = Project(name=PROJECT_NAME, connector=server)
        project.get()
        project.get_nodes()

        for node in project.nodes:
            if node.node_type == "docker" and node.name in IP_PLAN:
                if node.status != "started":
                    print(f"[WARN] Mazgas {node.name} neįjungtas. Praleidžiama.")
                    continue

                ip, gw = IP_PLAN[node.name]
                print(f"\n[PROCESS] Konfigūruojamas mazgas: {node.name}")
                
                commands = [
                    f"ip addr flush dev eth0",
                    f"ip addr add {ip}/24 dev eth0",
                    f"ip link set eth0 up",
                    f"ip route add default via {gw}"
                ]
                
                # API adresas Docker komandų vykdymui
                exec_url = f"{GNS3_BASE_URL}/projects/{project.project_id}/nodes/{node.node_id}/docker/exec"
                
                for cmd in commands:
                    try:
                        # Naudojame tiesioginį requests.post
                        response = requests.post(exec_url, json={"command": cmd})
                        
                        if response.status_code in [200, 201, 204]:
                            print(f"  -> [OK] {cmd}")
                        else:
                            print(f"  -> [!] API klaida ({response.status_code}): {response.text}")
                            error_count += 1
                    except Exception as e:
                        print(f"  -> [!] KLAIDA siunčiant užklausą: {e}")
                        error_count += 1
                    
                    time.sleep(0.3)

        if error_count > 0:
            print(f"\n[FAILED] Konfigūravimas baigtas su {error_count} klaidomis.")
            sys.exit(1)
        else:
            print("\n[SUCCESS] Viskas atlikta sėkmingai.")

    except Exception as e:
        print(f"\n[ERROR] Kritinė klaida: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
