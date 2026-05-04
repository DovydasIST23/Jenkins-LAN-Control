import os
import sys
import time
from netmiko import ConnectHandler
from gns3fy import Gns3Connector, Project

# Nustatymai
GNS3_IP = "192.168.56.102"
GNS3_URL = f"http://{GNS3_IP}:80"
PROJECT_NAME = "a"

IP_PLAN = {
    "AlpineLinux-1": ("11.0.0.2",  "11.0.0.1"),
    "AlpineLinux-2": ("10.0.0.11", "10.0.0.1")
}

def main():
    sys.stdout.reconfigure(line_buffering=True)
    
    try:
        print(f"[1] Jungiamasi prie API: {GNS3_URL}")
        server = Gns3Connector(url=GNS3_URL)
        project = Project(name=PROJECT_NAME, connector=server)
        project.get()
        project.get_nodes()

        # SVARBU: Naudojame 'terminal_server' tipą per 22 portą.
        # Tai priverčia Netmiko prisijungti prie SSH, bet nesitikėti jokio prompto.
        vm_params = {
            'device_type': 'terminal_server',
            'host': GNS3_IP,
            'username': 'gns3',
            'password': 'gns3',
            'port': 22,
            'global_delay_factor': 2,
        }

        print(f"[2] Atidariamas SSH ryšys (Port 22, no-prompt mode)...")
        ssh = ConnectHandler(**vm_params)
        
        # Duodame VM laiko parodyti meniu
        time.sleep(2)
        
        print("[3] Siunčiamas '7' (Shell)...")
        ssh.write_channel("7\n")
        time.sleep(3)
        
        # Pasižiūrime ką gavome
        output = ssh.read_channel()
        print(f"--- TERMINALO ATSAKYMAS ---\n{output}\n--------------------------")

        for node in project.nodes:
            if node.node_type == "docker" and node.name in IP_PLAN:
                ip, gw = IP_PLAN[node.name]
                print(f"\n[NODE] {node.name} konfigūracija...")

                # Siunčiame komandą gauti ID
                ssh.write_channel(f"docker ps -q --filter 'label=com.gns3.node.id={node.node_id}'\n")
                time.sleep(2)
                
                res = ssh.read_channel()
                container_id = None
                for line in res.splitlines():
                    clean = line.strip()
                    # ID turi būti 12 simbolių ilgio (pvz. a1b2c3d4e5f6)
                    if len(clean) >= 12 and clean.isalnum():
                        container_id = clean
                        break

                if container_id:
                    print(f"  -> Rasta ID: {container_id}. Siunčiamas IP {ip}")
                    ssh.write_channel(f"docker exec {container_id} ip addr flush dev eth0\n")
                    ssh.write_channel(f"docker exec {container_id} ip addr add {ip}/24 dev eth0\n")
                    ssh.write_channel(f"docker exec {container_id} ip link set eth0 up\n")
                    ssh.write_channel(f"docker exec {container_id} ip route add default via {gw}\n")
                    time.sleep(1)
                else:
                    print(f"  -> [!] Konteinerio ID nerastas atsakyme.")

        ssh.disconnect()
        print("\n[SUCCESS] Pipeline baigtas.")

    except Exception as e:
        print(f"\n[FATAL ERROR] {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
