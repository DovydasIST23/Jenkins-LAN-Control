import os
import sys
import time
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
                
                # Komandos Alpine konfigūravimui
                commands = [
                    f"ip addr flush dev eth0",
                    f"ip addr add {ip}/24 dev eth0",
                    f"ip link set eth0 up",
                    f"ip route add default via {gw}"
                ]
                
                for cmd in commands:
                    try:
                        # Naudojame gns3fy integruotą metodą komandų vykdymui
                        # Tai automatiškai parinks teisingą API kelią
                        response = node.run_custom_command(cmd)
                        print(f"  -> [OK] {cmd}")
                    except Exception as exec_err:
                        # Jei run_custom_command nepavyksta, bandom per docker_command
                        try:
                            node.connector.post(
                                f"/projects/{project.project_id}/nodes/{node.node_id}/docker/exec",
                                data={"command": cmd}
                            )
                            print(f"  -> [OK] (Alt path) {cmd}")
                        except:
                            print(f"  -> [!] Nepavyko įvykdyti '{cmd}': {exec_err}")
                    
                    time.sleep(0.5)

        print("\n[SUCCESS] Konfigūravimas per API baigtas.")

    except Exception as e:
        print(f"\n[ERROR] Kritinė klaida: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
