import sys
import time
from gns3fy import Gns3Connector, Project

# Nustatymai
GNS3_IP = "192.168.56.102"
GNS3_URL = f"http://{GNS3_IP}:80"
PROJECT_NAME = "a"

# IP Planas: { "Mazgo pavadinimas": ("IP adresas", "Vartai") }
IP_PLAN = {
    "AlpineLinux-1": ("11.0.0.2",  "11.0.0.1"),
    "AlpineLinux-2": ("10.0.0.11", "10.0.0.1"),
    "AlpineLinux-3": ("10.0.0.12", "10.0.0.1"),
    "AlpineLinux-4": ("10.1.0.10", "10.1.0.1"),
    "AlpineLinux-5": ("10.1.0.11", "10.1.0.1")
}

def main():
    # Užtikriname, kad Jenkins konsolė rodytų tekstą realiu laiku
    sys.stdout.reconfigure(line_buffering=True)
    
    error_count = 0
    
    try:
        print(f"[INFO] Jungiamasi prie GNS3 API: {GNS3_URL}")
        server = Gns3Connector(url=GNS3_URL)
        project = Project(name=PROJECT_NAME, connector=server)
        project.get()
        project.get_nodes()

        for node in project.nodes:
            if node.node_type == "docker" and node.name in IP_PLAN:
                # Patikriname, ar mazgas paleistas
                if node.status != "started":
                    print(f"[WARN] Mazgas {node.name} yra išjungtas (status: {node.status}). Praleidžiama.")
                    continue

                ip, gw = IP_PLAN[node.name]
                print(f"\n[PROCESS] Konfigūruojamas mazgas: {node.name}")
                
                # Alpine Linux tinklo komandos
                commands = [
                    f"ip addr flush dev eth0",
                    f"ip addr add {ip}/24 dev eth0",
                    f"ip link set eth0 up",
                    f"ip route add default via {gw}"
                ]
                
                for cmd in commands:
                    try:
                        # GNS3 API Docker vykdymo kelias
                        # Naudojame server.post, nes tai patikimiausias būdas Docker komandoms
                        exec_url = f"/projects/{project.project_id}/nodes/{node.node_id}/docker/exec"
                        
                        # API tikisi JSON objekto su raktu "command"
                        server.post(exec_url, data={"command": cmd})
                        print(f"  -> [OK] {cmd}")
                    except Exception as exec_err:
                        print(f"  -> [!] KLAIDA vykdant '{cmd}': {exec_err}")
                        error_count += 1
                    
                    time.sleep(0.3)

        if error_count > 0:
            print(f"\n[FAILED] Konfigūravimas baigtas su {error_count} klaidomis.")
            sys.exit(1)
        else:
            print("\n[SUCCESS] Visa konfigūracija sėkmingai pritaikyta.")

    except Exception as e:
        print(f"\n[ERROR] Kritinė klaida: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
