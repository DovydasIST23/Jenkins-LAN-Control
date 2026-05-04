import sys
import time
import requests
from gns3fy import Gns3Connector, Project

# Nustatymai
GNS3_IP = "192.168.56.102"
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
        server_url = f"http://{GNS3_IP}:80"
        print(f"[INFO] Jungiamasi prie GNS3: {server_url}")
        
        server = Gns3Connector(url=server_url)
        project = Project(name=PROJECT_NAME, connector=server)
        project.get()
        project.get_nodes()

        for node in project.nodes:
            if node.node_type == "docker" and node.name in IP_PLAN:
                if node.status != "started":
                    print(f"[WARN] Mazgas {node.name} neįjungtas. Praleidžiama.")
                    continue

                ip, gw = IP_PLAN[node.name]
                print(f"\n[PROCESS] Mazgas: {node.name}")
                
                commands = [
                    f"ip addr flush dev eth0",
                    f"ip addr add {ip}/24 dev eth0",
                    f"ip link set eth0 up",
                    f"ip route add default via {gw}"
                ]
                
                # Svarbu: kai kurios GNS3 versijos naudoja v2, kitos ne. 
                # Išbandome tiesioginį kelią per projekto/node ID
                base_exec_url = f"{server_url}/v2/projects/{project.project_id}/nodes/{node.node_id}/docker/exec"
                
                for cmd in commands:
                    try:
                        # Siunčiame užklausą. 
                        # Jei 404, pabandome alternatyvų URL (be /v2)
                        payload = {"command": cmd}
                        response = requests.post(base_exec_url, json=payload)
                        
                        if response.status_code == 404:
                            # Antras bandymas be /v2 prefixo
                            alt_url = f"{server_url}/projects/{project.project_id}/nodes/{node.node_id}/docker/exec"
                            response = requests.post(alt_url, json=payload)

                        if response.status_code in [200, 201, 204]:
                            print(f"  -> [OK] {cmd}")
                        else:
                            print(f"  -> [!] Klaida {node.name} | URL: {response.url} | Kodas: {response.status_code}")
                            error_count += 1
                    except Exception as e:
                        print(f"  -> [!] Ryšio klaida: {e}")
                        error_count += 1
                    
                    time.sleep(0.2)

        if error_count > 0:
            print(f"\n[FAILED] Baigta su {error_count} klaidomis.")
            sys.exit(1)
        else:
            print("\n[SUCCESS] Konfigūracija pritaikyta sėkmingai.")

    except Exception as e:
        print(f"\n[ERROR] Kritinė klaida: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
