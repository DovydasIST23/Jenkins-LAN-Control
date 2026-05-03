import os
import time
import sys
from gns3fy import Gns3Connector, Project

# Išjungiame buferizavimą
sys.stdout.reconfigure(line_buffering=True)

GNS3_URL = os.environ.get("GNS3_SERVER_URL", "http://192.168.56.102:80")
PROJECT_NAME = "a"

def main():
    try:
        print(f"[INFO] Jungiamasi prie GNS3: {GNS3_URL}")
        connector = Gns3Connector(url=GNS3_URL)
        project = Project(name=PROJECT_NAME, connector=connector)
        project.get()
        
        # 1. Paleidžiame mazgus
        if not start_nodes(project):
            print("[WARN] Kai kurie mazgai nepasileido, tęsiame...")

        # 2. Konfigūruojame tinklą (Be apk add!)
        configure_network(project)

        # 3. IŠPLĖSTINIS TESTAVIMAS
        run_network_tests(project)

        print("\n[SUCCESS] AUTOMATIZAVIMAS BAIGTAS")

    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

def configure_network(project):
    print("\n[INFO] Konfigūruojamas tinklas per API...")
    ip_plan = {
        "AlpineLinux-1": ("11.0.0.1", "11.0.0.1"),
        "AlpineLinux-2": ("10.0.0.11", "10.0.0.1"),
        "AlpineLinux-3": ("10.0.0.12", "10.0.0.1"),
        "AlpineLinux-8": ("10.1.0.10", "10.1.0.1")
    }

    for node in project.nodes:
        if node.name in ip_plan:
            ip, gw = ip_plan[node.name]
            # Naudojame tik standartines komandas, kurios jau yra Alpine
            cmd = f"sh -c 'ip addr flush dev eth0; ip addr add {ip}/24 dev eth0; ip link set eth0 up; ip route add default via {gw}'"
            print(f"[CFG] {node.name} -> {ip}")
            node.run_executable(cmd)

def run_network_tests(project):
    print("\n[TEST] Pradedamas išplėstinis tinklo testavimas...")
    
    # Testas: Ar AlpineLinux-2 mato AlpineLinux-3?
    test_connectivity(project, "AlpineLinux-2", "10.0.0.12")
    
    # Testas: Ar AlpineLinux-1 mato savo Gateway?
    test_connectivity(project, "AlpineLinux-1", "11.0.0.1")

def test_connectivity(project, source_node_name, target_ip):
    node = next((n for n in project.nodes if n.name == source_node_name), None)
    if node:
        print(f"[PING] {source_node_name} -> {target_ip}...", end=" ")
        try:
            # Vykdome ping (3 paketai)
            result = node.run_executable(f"ping -c 3 {target_ip}")
            if "0% packet loss" in result:
                print("✅ PASIEKIAMA")
            else:
                print("❌ NĖRA RYŠIO")
        except:
            print("❌ KLAIDA (API)")

def start_nodes(project):
    project.get_nodes()
    for node in project.nodes:
        if node.status != "started":
            node.start()
    
    for _ in range(10):
        project.get_nodes()
        if all(n.status == "started" for n in project.nodes):
            return True
        time.sleep(2)
    return False

if __name__ == "__main__":
    main()
