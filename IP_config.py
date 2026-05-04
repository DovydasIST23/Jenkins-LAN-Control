import os
import sys
import time
from netmiko import ConnectHandler
from gns3fy import Gns3Connector, Project

# --- KONFIGŪRACIJA ---
GNS3_IP = "192.168.56.102"
GNS3_URL = os.environ.get("GNS3_SERVER_URL", f"http://{GNS3_IP}:80")
PROJECT_NAME = "a"
GNS3_VM_USER = "gns3"
GNS3_VM_PASS = "gns3"

# IP Planas Alpine konteineriams
IP_PLAN = {
    "AlpineLinux-1": ("11.0.0.2",  "11.0.0.1"),
    "AlpineLinux-2": ("10.0.0.11", "10.0.0.1"),
    "AlpineLinux-3": ("10.0.0.12", "10.0.0.1"),
    "AlpineLinux-8": ("10.1.0.10", "10.1.0.1"),
    "AlpineLinux-9": ("10.1.0.11", "10.1.0.1"),
    "AlpineLinux-10": ("10.2.0.10", "10.2.0.1")
}

def configure_docker_nodes(project):
    print("\n[DEBUG] === Pradedama Docker (Alpine) konfigūracija ===")
    
    vm_params = {
        'device_type': 'linux',
        'host': GNS3_IP,
        'username': GNS3_VM_USER,
        'password': GNS3_VM_PASS,
        # Svarbu: užtikriname, kad patektume tiesiai į shell, o ne į gns3-menu
        'session_preparation_commands': [
            'export TERM=xterm',
            'stty cols 200',
            'unset LANG'
        ]
    }
    
    try:
        print(f"[INFO] Jungiamasi prie GNS3 VM SSH ({GNS3_IP})...")
        ssh_conn = ConnectHandler(**vm_params)
        
        for node in project.nodes:
            if node.node_type == "docker" and node.name in IP_PLAN:
                ip, gw = IP_PLAN[node.name]
                
                # Gauname konteinerio ID
                cmd = f'docker ps --filter "label=com.gns3.node.id={node.node_id}" --format "{{{{.ID}}}}"'
                container_id = ssh_conn.send_command(cmd).strip()
                
                if container_id:
                    print(f"[OK] {node.name} -> Nustatomas IP {ip}")
                    ssh_conn.send_command(f'docker exec {container_id} ip addr flush dev eth0')
                    ssh_conn.send_command(f'docker exec {container_id} ip addr add {ip}/24 dev eth0')
                    ssh_conn.send_command(f'docker exec {container_id} ip link set eth0 up')
                    ssh_conn.send_command(f'docker exec {container_id} ip route add default via {gw}')
                else:
                    print(f"[!] Mazgas {node.name} nerastas veikiančiuose konteineriuose.")
        
        ssh_conn.disconnect()
    except Exception as e:
        print(f"[CRITICAL] Docker klaida: {e}")

def configure_mikrotik(project):
    print("\n[DEBUG] === Pradedama MikroTik konfigūracija ===")
    
    mt_node = next((n for n in project.nodes if "mikrotik" in n.name.lower()), None)
    if not mt_node:
        print("[ERROR] MikroTik mazgas nerastas.")
        return

    print(f"[INFO] MikroTik portas: {mt_node.console}. Jungiamasi...")

    mt_params = {
        'device_type': 'generic_telnet',
        'host': GNS3_IP,
        'port': mt_node.console,
        'timeout': 10,
    }

    try:
        net_conn = ConnectHandler(**mt_params)
        
        # 1. "Pravalome" konsolę, kad būtume švariame prompt'e
        print("  -> Budinama konsole...")
        for _ in range(3):
            net_conn.write_channel("\r")
            time.sleep(1)
        
        commands = [
            "/ip address add address=11.0.0.1/24 interface=ether1",
            "/ip address add address=10.0.0.1/24 interface=ether2",
            "/ip address add address=10.1.0.1/24 interface=ether3",
            "/ip address add address=10.2.0.1/24 interface=ether4"
        ]
        
        # 2. Siunčiame komandas po vieną su ilga pauze
        for cmd in commands:
            print(f"  -> Siunciama: {cmd}")
            net_conn.write_channel(cmd + "\r")
            time.sleep(2) # MikroTik Telnet reikia laiko apdoroti įvestį
            
        print("[SUCCESS] MikroTik konfigūravimas baigtas.")
        net_conn.disconnect()
    except Exception as e:
        print(f"[CRITICAL] MikroTik klaida: {e}")

def main():
    try:
        # Priverčiame spausdinti tekstą iškart (Jenkins debugui)
        sys.stdout.reconfigure(line_buffering=True)
        
        connector = Gns3Connector(url=GNS3_URL)
        project = Project(name=PROJECT_NAME, connector=connector)
        project.get()
        project.get_nodes()

        # Pirmiausia Alpine, tada MikroTik
        configure_docker_nodes(project)
        time.sleep(2)
        configure_mikrotik(project)

        print("\n[FINISH] Automatizacija baigta.")

    except Exception as e:
        print(f"\n[ERROR] Klaida pagrindiniame cikle: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
