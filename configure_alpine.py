import os
import sys
import time
import logging
import traceback
from netmiko import ConnectHandler
from gns3fy import Gns3Connector, Project

# Įjungiame Netmiko vidinį debug logą į failą
logging.basicConfig(filename='ssh_debug.log', level=logging.DEBUG)
logger = logging.getLogger("netmiko")

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
    ssh = None
    
    try:
        print(f"--- DEBUG PRADŽIA ---")
        print(f"[1] Jungiamasi prie API: {GNS3_URL}")
        server = Gns3Connector(url=GNS3_URL)
        project = Project(name=PROJECT_NAME, connector=server)
        project.get()
        project.get_nodes()
        print(f"[OK] API ryšys veikia. Rastas projektas: {project.name}")

        vm_params = {
            'device_type': 'generic_termserver_telnet',
            'host': GNS3_IP,
            'username': 'gns3',
            'password': 'gns3',
            'port': 22,
            'session_log': 'session_output.txt', # Įrašys visą terminalo vaizdą
            'timeout': 60,
            'auth_timeout': 60,
        }

        print(f"[2] Atidariamas SSH kanalas į {GNS3_IP}...")
        ssh = ConnectHandler(**vm_params)
        
        print(f"[3] SSH Prisijungta. Laukiama 10s, kol VM paruoš meniu...")
        time.sleep(10)

        # Patikriname ką matome ekrane prieš siunčiant
        initial_output = ssh.read_channel()
        print(f"[DEBUG] Terminalo vaizdas prisijungus:\n{initial_output}")

        print(f"[4] Siunčiamas '7' (Shell)...")
        ssh.write_channel("7\n")
        
        # Tikriname ar po išsiuntimo ryšys vis dar gyvas
        time.sleep(5)
        if not ssh.remote_conn.get_transport().is_active():
            print("[CRITICAL] Ryšys nutrūko iškart po '7' išsiuntimo!")
            raise ConnectionError("Host machine aborted connection after command 7")

        shell_output = ssh.read_channel()
        print(f"[DEBUG] Terminalo vaizdas po '7':\n{shell_output}")

        for node in project.nodes:
            if node.node_type == "docker" and node.name in IP_PLAN:
                print(f"\n[5] Ruošiamas mazgas: {node.name}")
                cmd = f"docker ps -q --filter 'label=com.gns3.node.id={node.node_id}'\n"
                ssh.write_channel(cmd)
                time.sleep(2)
                print(f"[DEBUG] Docker PS atsakymas: {ssh.read_channel()}")

        ssh.disconnect()
        print("\n--- DEBUG PABAIGA: SĖKMĖ ---")

    except Exception as e:
        print(f"\n[!!!] KRITINĖ KLAIDA: {str(e)}")
        print("-" * 30)
        traceback.print_exc() # Parodys tikslią eilutę
        print("-" * 30)
        
        # Jei failas egzistuoja, bandom parodyti sesijos pabaigą
        if os.path.exists('session_output.txt'):
            print("[DEBUG] Paskutinės terminalo eilutės prieš klaidą:")
            with open('session_output.txt', 'r') as f:
                print(f.readlines()[-10:])
        
        sys.exit(1)

if __name__ == "__main__":
    main()
