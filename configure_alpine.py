import os
import sys
import time
import logging
from netmiko import ConnectHandler
from gns3fy import Gns3Connector, Project

# Įjungiame Netmiko debug logus į failą Jenkins aplanke
logging.basicConfig(filename='netmiko_global.log', level=logging.DEBUG)

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
        print("--- [1] API DEBUG ---")
        server = Gns3Connector(url=GNS3_URL)
        project = Project(name=PROJECT_NAME, connector=server)
        project.get()
        project.get_nodes()
        print(f"[OK] Projektas '{PROJECT_NAME}' rastas.")

        # Naudojame 'generic_termserver_telnet', bet nurodome portą 22 (SSH)
        # Tai priverčia Netmiko prisijungti prie SSH, bet elgtis kaip su Telnet (nieko nelaukti)
        vm_params = {
            'device_type': 'generic_termserver_telnet',
            'host': GNS3_IP,
            'username': 'gns3',
            'password': 'gns3',
            'port': 22,
            'session_log': 'raw_session.log', # Čia bus viskas, ką matė skriptas
        }

        print(f"--- [2] SSH DEBUG ---")
        print(f"Jungiamasi prie {GNS3_IP}:22 (be prompt tikrinimo)...")
        ssh = ConnectHandler(**vm_params)
        
        print("Laukiama 5s, kol VM išspjaus meniu...")
        time.sleep(5)
        
        # Priverstinai skaitome viską, kas yra buferyje
        initial_view = ssh.read_channel()
        print(f"--- [3] TERMINALO VAIZDAS PRISIJUNGUS ---\n{initial_view}\n-------------------")

        print("Siunčiamas '7' (Shell)...")
        ssh.write_channel("7\n")
        time.sleep(3)
        
        after_seven = ssh.read_channel()
        print(f"--- [4] VAIZDAS PO '7' ---\n{after_seven}\n-------------------")

        for node in project.nodes:
            if node.node_type == "docker" and node.name in IP_PLAN:
                ip, gw = IP_PLAN[node.name]
                print(f"\n[NODE] {node.name} config...")

                # Siunčiame ID paiešką
                find_cmd = f"docker ps -q --filter 'label=com.gns3.node.id={node.node_id}'\n"
                ssh.write_channel(find_cmd)
                time.sleep(2)
                
                ps_res = ssh.read_channel()
                print(f"Docker PS atsakymas:\n{ps_res}")
                
                # Ieškome ID (12 simbolių šešioliktainis)
                container_id = None
                for line in ps_res.splitlines():
                    clean = line.strip()
                    if len(clean) >= 12 and clean.isalnum():
                        container_id = clean
                        break

                if container_id:
                    print(f"Rasta ID: {container_id}. Siunčiame IP: {ip}")
                    ssh.write_channel(f"docker exec {container_id} ip addr flush dev eth0\n")
                    ssh.write_channel(f"docker exec {container_id} ip addr add {ip}/24 dev eth0\n")
                    ssh.write_channel(f"docker exec {container_id} ip link set eth0 up\n")
                    ssh.write_channel(f"docker exec {container_id} ip route add default via {gw}\n")
                    time.sleep(1)
                else:
                    print("Konteinerio ID nerastas šiame atsakyme.")

        ssh.disconnect()
        print("\n--- [SUCCESS] SKRIPTAS BAIGĖ DARBĄ ---")

    except Exception as e:
        print(f"\n--- [FATAL ERROR] ---")
        print(f"Klaidos tipas: {type(e).__name__}")
        print(f"Žinutė: {e}")
        if os.path.exists('raw_session.log'):
            print("\nPaskutinės 5 eilutės iš raw_session.log:")
            with open('raw_session.log', 'r') as f:
                print("".join(f.readlines()[-5:]))
        sys.exit(1)

if __name__ == "__main__":
    main()
