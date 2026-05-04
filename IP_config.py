import os
import sys
import time
from netmiko import ConnectHandler
from gns3fy import Gns3Connector, Project

# --- KONFIGŪRACIJA ---
GNS3_IP = "192.168.56.102"
GNS3_URL = os.environ.get("GNS3_SERVER_URL", f"http://{GNS3_IP}:80")
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
    print("\n[DEBUG] === 1 ETAPAS: Docker (Alpine) konfigūracija ===")
    vm_params = {
        'device_type': 'generic_termserver_telnet', # Ignoruojame SSH promptus
        'host': GNS3_IP,
        'username': 'gns3',
        'password': 'gns3',
        'port': 22,
    }
    try:
        conn = ConnectHandler(**vm_params)
        print("[INFO] Jungiamasi prie VM... Bandoma išeiti iš meniu.")
        
        # Priverstinai išeiname iš GNS3 meniu į Shell (siunčiame 7 ir Enter)
        conn.write_channel("7\r")
        time.sleep(2)
        
        # Pravalome viską, ką gavome
        conn.read_channel()

        for node_name, (ip, gw) in IP_PLAN.items():
            node_obj = next((n for n in project.nodes if n.name == node_name), None)
            if not node_obj:
                continue

            print(f"[PROCESS] Mazgas: {node_name}")
            
            # Gauname ID per Shell
            cmd = f"docker ps -q --filter 'label=com.gns3.node.id={node_obj.node_id}'\r"
            conn.write_channel(cmd)
            time.sleep(1)
            
            output = conn.read_channel().splitlines()
            # ID paprastai būna paskutinėje arba priešpaskutinėje eilutėje
            container_id = None
            for line in reversed(output):
                clean_line = line.strip()
                if len(clean_line) >= 12 and clean_line.isalnum():
                    container_id = clean_line
                    break

            if container_id:
                print(f"  -> Rasta ID: {container_id}. Siunčiamos komandos.")
                docker_cmds = [
                    f'docker exec {container_id} ip addr flush dev eth0\r',
                    f'docker exec {container_id} ip addr add {ip}/24 dev eth0\r',
                    f'docker exec {container_id} ip link set eth0 up\r',
                    f'docker exec {container_id} ip route add default via {gw}\r'
                ]
                for d_cmd in docker_cmds:
                    conn.write_channel(d_cmd)
                    time.sleep(0.5)
            else:
                print(f"  -> [!] Konteineris nerastas.")

        conn.disconnect()
    except Exception as e:
        print(f"[ERR] Docker dalis: {e}")

def configure_mikrotik(project):
    print("\n[DEBUG] === 2 ETAPAS: MikroTik konfigūracija ===")
    mt_node = next((n for n in project.nodes if "mikrotik" in n.name.lower()), None)
    if not mt_node: return

    try:
        conn = ConnectHandler(device_type='generic_telnet', host=GNS3_IP, port=mt_node.console)
        conn.write_channel("\r\r")
        time.sleep(1)
        
        output = conn.read_channel()
        if "iPXE" in output or "No bootable" in output:
            print("[CRITICAL] MikroTik vis dar iPXE/Boot loop. Rankiniu būdu sutvarkykite GNS3!")
            return

        commands = ["/ip address add address=11.0.0.1/24 interface=ether1\r",
                    "/ip address add address=10.0.0.1/24 interface=ether2\r"]
        for cmd in commands:
            conn.write_channel(cmd)
            time.sleep(1)
        conn.disconnect()
        print("[SUCCESS] MikroTik baigtas.")
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
