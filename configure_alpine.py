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
        print(f" [1] Jungiamasi prie API: {GNS3_URL}")
        server = Gns3Connector(url=GNS3_URL)
        project = Project(name=PROJECT_NAME, connector=server)
        project.get()
        project.get_nodes()

        vm_params = {
            'device_type': 'terminal_server',
            'host': GNS3_IP,
            'username': 'gns3',
            'password': 'gns3',
            'port': 22,
        }

        print(f" [2] Atidariamas SSH ryšys (Port 22)...")
        ssh = ConnectHandler(**vm_params)
        
        print(" [3] „Pralaužiamas“ GNS3 meniu (agresyvus rėžimas)...")
        time.sleep(5)
        
        # Siunčiame 3x Enter, kad uždarytume bet kokius iššokusius langus (Information/Error)
        for i in range(3):
            ssh.write_channel("\r")
            time.sleep(2)
        
        # Siunčiame '7', kad pasirinktume Shell
        print(" [4] Siunčiama komanda '7' (Shell)...")
        ssh.write_channel("7\r")
        time.sleep(5)
        
        # Pravalome ir tikriname būseną
        output = ssh.read_channel()
        if "gns3@" in output.lower() or "ubuntu" in output.lower():
            print(" [OK] Sėkmingai patekome į Shell terminalą.")
        else:
            print(" [!] Įspėjimas: Terminalas neatrodo kaip Shell, bet tęsiame...")

        for node in project.nodes:
            if node.node_type == "docker" and node.name in IP_PLAN:
                ip, gw = IP_PLAN[node.name]
                print(f"\n [PROCESS] Mazgas: {node.name}")

                # Ieškome Docker ID. Siunčiame Enter prieš komandą, kad išvalytume eilutę
                ssh.write_channel("\r")
                time.sleep(1)
                cmd = f"docker ps -q --filter 'label=com.gns3.node.id={node.node_id}'\r"
                ssh.write_channel(cmd)
                time.sleep(3)
                
                res = ssh.read_channel()
                container_id = None
                # Ieškome ID (12 simbolių). Filtruojame tik alfanumerinius.
                for line in res.splitlines():
                    clean = line.strip()
                    if len(clean) >= 12 and clean.isalnum() and "docker" not in clean.lower():
                        container_id = clean
                        break

                if container_id:
                    print(f"  -> Rasta ID: {container_id}. Konfigūruojama...")
                    # Naudojame tiesiogines komandas su didesniais tarpais
                    for c in [
                        f'docker exec {container_id} ip addr flush dev eth0\r',
                        f'docker exec {container_id} ip addr add {ip}/24 dev eth0\r',
                        f'docker exec {container_id} ip link set eth0 up\r',
                        f'docker exec {container_id} ip route add default via {gw}\r'
                    ]:
                        ssh.write_channel(c)
                        time.sleep(1.5)
                    print(f"  -> [OK] IP {ip} nustatytas.")
                else:
                    print(f"  -> [!] Konteinerio ID nerastas. Logas: {res[:50]}...")

        ssh.disconnect()
        print("\n [SUCCESS] Pipeline užbaigtas.")

    except Exception as e:
        print(f"\n [FATAL ERROR] {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
