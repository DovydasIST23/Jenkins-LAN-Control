import os
import sys
import time
from netmiko import ConnectHandler
from gns3fy import Gns3Connector, Project

# --- KONFIGŪRACIJA ---
GNS3_IP = "192.168.56.102"
GNS3_URL = f"http://{GNS3_IP}:80"
PROJECT_NAME = "a"

IP_PLAN = {
    "AlpineLinux-1": ("11.0.0.2",  "11.0.0.1"),
    "AlpineLinux-2": ("10.0.0.11", "10.0.0.1"),
    "AlpineLinux-3": ("10.0.0.12", "10.0.0.1"),
    "AlpineLinux-8": ("10.1.0.10", "10.1.0.1"),
    "AlpineLinux-9": ("10.1.0.11", "10.1.0.1"),
    "AlpineLinux-10": ("10.2.0.10", "10.2.0.1")
}

def configure_docker_nodes(project):
    print("\n[DEBUG] === Docker (Alpine) konfigūracija pagal vardus ===")
    vm_params = {
        'device_type': 'linux',
        'host': GNS3_IP,
        'username': 'gns3',
        'password': 'gns3',
    }
    try:
        conn = ConnectHandler(**vm_params)
        conn.write_channel("7\r") # Išeiname į shell
        time.sleep(1)

        # Gauname visų veikiančių konteinerių sąrašą (ID ir Name)
        print("[INFO] Gaunamas Docker konteinerių sąrašas...")
        ps_output = conn.send_command('docker ps --format "{{.ID}}|{{.Names}}"')
        containers = ps_output.strip().split('\n')

        for node_name, (ip, gw) in IP_PLAN.items():
            # Ieškome konteinerio, kurio pavadinime yra mazgo vardas
            # GNS3 pavadinimai dažnai būna ilgi, pvz: "vnc-1-7da462ba-1b12..."
            # Todėl ieškome dalinio sutapimo
            target_id = None
            for line in containers:
                if '|' in line:
                    c_id, c_name = line.split('|')
                    # Dažnai GNS3 pavadinime būna mazgo ID, todėl ieškome per project objektą
                    node_obj = next((n for n in project.nodes if n.name == node_name), None)
                    if node_obj and node_obj.node_id in c_name:
                        target_id = c_id
                        break
            
            if target_id:
                print(f"[OK] Rasta: {node_name} -> ID: {target_id}. Konfigūruojama...")
                conn.send_command(f'docker exec {target_id} ip addr flush dev eth0')
                conn.send_command(f'docker exec {target_id} ip addr add {ip}/24 dev eth0')
                conn.send_command(f'docker exec {target_id} ip link set eth0 up')
                conn.send_command(f'docker exec {target_id} ip route add default via {gw}')
            else:
                print(f"[!] Mazgas {node_name} Docker sąraše nerastas.")

        conn.disconnect()
    except Exception as e:
        print(f"[ERR] Docker dalis: {e}")

def configure_mikrotik(project):
    # Paliekame tą pačią logiką, bet pridėjome apsaugą nuo iPXE
    print("\n[DEBUG] === MikroTik konfigūracija ===")
    mt_node = next((n for n in project.nodes if "mikrotik" in n.name.lower()), None)
    if not mt_node: return

    try:
        conn = ConnectHandler(device_type='generic_telnet', host=GNS3_IP, port=mt_node.console)
        conn.write_channel("\r\r")
        time.sleep(1)
        
        output = conn.read_channel()
        if "No bootable device" in output or "iPXE" in output:
            print("[CRITICAL] MikroTik nepasileido (No bootable device). Praleidžiama.")
            return

        commands = ["/ip address add address=11.0.0.1/24 interface=ether1",
                    "/ip address add address=10.0.0.1/24 interface=ether2"]
        for cmd in commands:
            conn.write_channel(cmd + "\r")
            time.sleep(1.5)
        conn.disconnect()
        print("[SUCCESS] MikroTik komandos nusiųstos.")
    except Exception as e:
        print(f"[ERR] MikroTik dalis: {e}")

if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    server = Gns3Connector(url=GNS3_URL)
    project = Project(name=PROJECT_NAME, connector=server)
    project.get()
    project.get_nodes()
    
    configure_docker_nodes(project)
    configure_mikrotik(project)
