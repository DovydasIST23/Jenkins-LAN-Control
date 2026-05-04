import os
import time
import sys
from netmiko import ConnectHandler
from gns3fy import Gns3Connector, Project

# Nustatymai
GNS3_URL = os.environ.get("GNS3_SERVER_URL", "http://192.168.56.102:80")
PROJECT_NAME = "a"
GNS3_VM_IP = "192.168.56.102"
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
    print("\n--- Konfigūruojami Docker (Alpine) mazgai ---")
    
    # Jungiamės prie GNS3 VM (Linux host)
    vm_params = {
        'device_type': 'linux',
        'host': GNS3_VM_IP,
        'username': GNS3_VM_USER,
        'password': GNS3_VM_PASS,
    }
    
    try:
        ssh_conn = ConnectHandler(**vm_params)
        
        for node in project.nodes:
            if node.node_type == "docker" and node.name in IP_PLAN:
                ip, gw = IP_PLAN[node.name]
                
                # Surandame Docker Container ID pagal GNS3 Node ID
                cmd = f'docker ps --filter "label=com.gns3.node.id={node.node_id}" --format "{{{{.ID}}}}"'
                container_id = ssh_conn.send_command(cmd).strip()
                
                if container_id:
                    print(f"[OK] {node.name} -> Nustatomas IP {ip}")
                    # Vykdome tinklo nustatymo komandas konteinerio viduje
                    cfg_cmds = [
                        f'docker exec {container_id} ip addr flush dev eth0',
                        f'docker exec {container_id} ip addr add {ip}/24 dev eth0',
                        f'docker exec {container_id} ip link set eth0 up',
                        f'docker exec {container_id} ip route add default via {gw}'
                    ]
                    for cfg in cfg_cmds:
                        ssh_conn.send_command(cfg)
                else:
                    print(f"[!] Mazgas {node.name} nerastas veikiančiuose konteineriuose.")
        
        ssh_conn.disconnect()
    except Exception as e:
        print(f"[ERROR] Docker konfigūracijos klaida: {e}")

def configure_mikrotik(project):
    """Konfigūruoja MikroTik per Telnet konsolę (GNS3 portą)"""
    print("\n--- Konfigūruojamas MikroTik ---")
    
    # Randame MikroTik mazgą ir jo konsolės portą
    mt_node = next((n for n in project.nodes if "mikrotik" in n.name.lower()), None)
    
    if not mt_node:
        print("[ERROR] MikroTik mazgas projekte nerastas.")
        return

    # Jungiamės prie MikroTik per Telnet (GNS3 Console Port)
    mt_params = {
        'device_type': 'mikrotik_routeros',
        'host': GNS3_VM_IP,
        'port': mt_node.console, # Naudojame GNS3 priskirtą portą (pvz. 5001)
        'username': 'admin',
        'password': '', 
    }

    try:
        # Prieš jungiantis per Netmiko Telnet, gali prireikti sekundės palaukti
        net_conn = ConnectHandler(**mt_params)
        
        commands = [
            "/ip address add address=11.0.0.1/24 interface=ether1",
            "/ip address add address=10.0.0.1/24 interface=ether2",
            "/ip address add address=10.1.0.1/24 interface=ether3",
            "/ip address add address=10.2.0.1/24 interface=ether4"
        ]
        
        # MikroTik'e siunčiame komandas
        output = net_conn.send_config_set(commands)
        print(output)
        net_conn.disconnect()
        print("[SUCCESS] MikroTik sukonfigūruotas.")
        
    except Exception as e:
        print(f"[ERROR] MikroTik konfigūracijos klaida: {e}")

def main():
    try:
        connector = Gns3Connector(url=GNS3_URL)
        project = Project(name=PROJECT_NAME, connector=connector)
        project.get()
        project.get_nodes()

        # 1. Konfigūruojame Alpine konteinerius
        configure_docker_nodes(project)
        
        # 2. Konfigūruojame MikroTik
        configure_mikrotik(project)

    except Exception as e:
        print(f"[CRITICAL] Klaida: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
