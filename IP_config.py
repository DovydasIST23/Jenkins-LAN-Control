import os
import sys
import time
from netmiko import ConnectHandler
from gns3fy import Gns3Connector, Project

# Nustatymai
GNS3_IP = "192.168.56.102"
GNS3_URL = f"http://{GNS3_IP}:80"
PROJECT_NAME = "a"

# Susiejame GNS3 mazgo pavadinimą su planuojamu IP
IP_PLAN = {
    "AlpineLinux-1": ("11.0.0.2",  "11.0.0.1"),
    "AlpineLinux-2": ("10.0.0.11", "10.0.0.1"),
    "AlpineLinux-3": ("10.0.0.12", "10.0.0.1"),
    "AlpineLinux-8": ("10.1.0.10", "10.1.0.1"),
    "AlpineLinux-9": ("10.1.0.11", "10.1.0.1"),
    "AlpineLinux-10": ("10.2.0.10", "10.2.0.1")
}

def configure_docker_nodes(project):
    print("\n[DEBUG] === Docker (Alpine) konfigūracija ===")
    vm_params = {
        'device_type': 'linux',
        'host': GNS3_IP,
        'username': 'gns3',
        'password': 'gns3',
    }
    try:
        ssh_conn = ConnectHandler(**vm_params)
        
        # Priverstinai išeiname į shell, jei esame meniu
        ssh_conn.write_channel("7\r")
        time.sleep(1)

        for node in project.nodes:
            if node.node_type == "docker" and node.name in IP_PLAN:
                ip, gw = IP_PLAN[node.name]
                print(f"[PROCESS] Konfigūruojamas {node.name}...")

                # PAKEISTA: ieškome konteinerio ID pagal GNS3 mazgo ID tiesiogiai per docker ps
                container_cmd = f"docker ps -q --filter 'label=com.gns3.node.id={node.node_id}'"
                container_id = ssh_conn.send_command(container_cmd).strip()

                if not container_id:
                    # Alternatyva: jei label neveikia, bandom rasti pagal pavadinimą (iš jūsų nuotraukos)
                    # GNS3 Docker pavadinimai paprastai turi projekto ir mazgo ID dalis
                    print(f"  [!] Per label nerasta, bandoma surasti bet kokį veikiantį konteinerį...")
                    container_id = ssh_conn.send_command(f"docker ps -q -l").strip() # Paskutinis paleistas

                if container_id:
                    print(f"  -> Rasta ID: {container_id}. Siunčiamos komandos...")
                    ssh_conn.send_command(f'docker exec {container_id} ip addr flush dev eth0')
                    ssh_conn.send_command(f'docker exec {container_id} ip addr add {ip}/24 dev eth0')
                    ssh_conn.send_command(f'docker exec {container_id} ip link set eth0 up')
                    ssh_conn.send_command(f'docker exec {container_id} ip route add default via {gw}')
                    print(f"  -> [OK] {node.name} IP nustatytas: {ip}")
                else:
                    print(f"  -> [!] ERROR: Konteineris mazgui {node.name} nerastas.")
        
        ssh_conn.disconnect()
    except Exception as e:
        print(f"[ERR] Docker dalis: {e}")

def configure_mikrotik(project):
    print("\n[DEBUG] === MikroTik konfigūracija ===")
    mt_node = next((n for n in project.nodes if "mikrotik" in n.name.lower()), None)
    if not mt_node: return

    mt_params = {
        'device_type': 'generic_telnet',
        'host': GNS3_IP,
        'port': mt_node.console,
    }
    try:
        conn = ConnectHandler(**mt_params)
        conn.write_channel("\r\r")
        time.sleep(1)
        
        # Tikriname ar ne iPXE (jūsų nuotraukos problema)
        output = conn.read_channel()
        if "iPXE" in output:
            print("  [!] Įrenginys vis dar iPXE režime! Bandoma išeiti...")
            conn.write_channel("exit\r")
            time.sleep(3)

        commands = [
            "/ip address add address=11.0.0.1/24 interface=ether1",
            "/ip address add address=10.0.0.1/24 interface=ether2",
            "/ip address add address=10.1.0.1/24 interface=ether3",
            "/ip address add address=10.2.0.1/24 interface=ether4"
        ]
        for cmd in commands:
            conn.write_channel(cmd + "\r")
            time.sleep(1.5)
        print("[SUCCESS] MikroTik baigtas.")
        conn.disconnect()
    except Exception as e:
        print(f"[ERR] MikroTik dalis: {e}")

if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    connector = Gns3Connector(url=GNS3_URL)
    project = Project(name=PROJECT_NAME, connector=connector)
    project.get()
    project.get_nodes()
    configure_docker_nodes(project)
    configure_mikrotik(project)
