import os
import sys
import time
import logging
from netmiko import ConnectHandler
from gns3fy import Gns3Connector, Project

# --- DEBUG NUSTATYMAI ---
# Priverčiame Python spausdinti tekstą iškart (be buferio)
sys.stdout.reconfigure(line_buffering=True)

# Nustatymai
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
    """Konfigūruoja Docker konteinerius per GNS3 VM SSH"""
    print("\n[DEBUG] === Pradedama Docker mazgų konfigūracija ===")
    
    vm_params = {
        'device_type': 'linux',
        'host': GNS3_IP,
        'username': GNS3_VM_USER,
        'password': GNS3_VM_PASS,
    }
    
    try:
        print(f"[INFO] Jungiamasi prie GNS3 VM SSH ({GNS3_IP})...")
        ssh_conn = ConnectHandler(**vm_params)
        
        for node in project.nodes:
            if node.node_type == "docker" and node.name in IP_PLAN:
                ip, gw = IP_PLAN[node.name]
                print(f"[PROCESS] Konfigūruojamas {node.name}...")
                
                # Docker ID gavimas
                cmd = f'docker ps --filter "label=com.gns3.node.id={node.node_id}" --format "{{{{.ID}}}}"'
                container_id = ssh_conn.send_command(cmd).strip()
                
                if container_id:
                    print(f"  -> Rasta Docker ID: {container_id}. Siunčiamos tinklo komandos...")
                    cfg_cmds = [
                        f'docker exec {container_id} ip addr flush dev eth0',
                        f'docker exec {container_id} ip addr add {ip}/24 dev eth0',
                        f'docker exec {container_id} ip link set eth0 up',
                        f'docker exec {container_id} ip route add default via {gw}'
                    ]
                    for cfg in cfg_cmds:
                        ssh_conn.send_command(cfg)
                    print(f"  -> [OK] {node.name} sukonfigūruotas su {ip}")
                else:
                    print(f"  -> [!] ERROR: Nepavyko rasti veikiančio konteinerio mazgui {node.name}")
        
        ssh_conn.disconnect()
    except Exception as e:
        print(f"[CRITICAL] Docker konfigūracijos klaida: {e}")

def configure_mikrotik(project):
    """Konfigūruoja MikroTik per GNS3 Console Port (Telnet)"""
    print("\n[DEBUG] === Pradedama MikroTik konfigūracija ===")
    
    mt_node = next((n for n in project.nodes if "mikrotik" in n.name.lower()), None)
    
    if not mt_node:
        print("[ERROR] MikroTik mazgas projekte nerastas.")
        return

    print(f"[INFO] MikroTik mazgas: {mt_node.name}, Statusas: {mt_node.status}, Portas: {mt_node.console}")

    # Jungiamės per Telnet (nes tai standartinis GNS3 konsolės būdas)
    mt_params = {
        'device_type': 'mikrotik_routeros_telnet', # Pakeista į telnet stabilesniam ryšiui
        'host': GNS3_IP,
        'port': mt_node.console,
        'username': 'admin',
        'password': '',
        'global_delay_factor': 2,
    }

    try:
        print(f"[INFO] Atidariamas ryšys su MikroTik per portą {mt_node.console}...")
        net_conn = ConnectHandler(**mt_params)
        
        commands = [
            "/ip address add address=11.0.0.1/24 interface=ether1",
            "/ip address add address=10.0.0.1/24 interface=ether2",
            "/ip address add address=10.1.0.1/24 interface=ether3",
            "/ip address add address=10.2.0.1/24 interface=ether4"
        ]
        
        print("[PROCESS] Siunčiamos komandos į MikroTik...")
        output = net_conn.send_config_set(commands)
        print(f"[OUTPUT]\n{output}")
        
        net_conn.disconnect()
        print("[SUCCESS] MikroTik konfigūravimas baigtas.")
        
    except Exception as e:
        print(f"[CRITICAL] MikroTik konfigūracijos klaida: {e}")

def main():
    try:
        print(f"[START] Jungiamasi prie GNS3 API: {GNS3_URL}")
        connector = Gns3Connector(url=GNS3_URL)
        project = Project(name=PROJECT_NAME, connector=connector)
        project.get()
        project.get_nodes()

        print(f"[OK] Projektas '{PROJECT_NAME}' sėkmingai pasiektas.")

        # 1. Docker konfigūravimas
        configure_docker_nodes(project)
        
        # 2. Trumpa pauzė tarp skirtingų mazgų tipų
        time.sleep(2)
        
        # 3. MikroTik konfigūravimas
        configure_mikrotik(project)
        
        print("\n[FINISH] Visa automatizacija baigta sėkmingai.")

    except Exception as e:
        print(f"\n[CRITICAL ERROR] Pagrindinio proceso klaida: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
