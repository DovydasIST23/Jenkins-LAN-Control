import sys
import time
from gns3fy import Gns3Connector, Project
from netmiko import ConnectHandler

# --- KONFIGURACIJA ---
GNS3_IP = "192.168.56.102"
PROJECT_NAME = "a"

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

def get_params(port):
    return {
        'device_type': 'generic_telnet',
        'host': GNS3_IP,
        'port': port,
        'timeout': 15,
    }

def apply_physical_block(port):
    """Blokuoja tinklus isjungdamas interfeisus (Garantuotas blokavimas)."""
    print(f"\n[*] Jungiamasi prie AlpineRouter (Console port: {port})...")
    
    try:
        with ConnectHandler(**get_params(port)) as tn:
            # Uztikriname, kad terminalas aktyvus
            tn.write_channel("\n")
            time.sleep(1)
            
            print("[*] ISJUNGIAMOS TINKLO SASAJOS...")
            # eth0 = Main, eth1 = Admin, eth2 = Support
            cmds = [
                "ip link set eth0 down",
                "ip link set eth1 down",
                "ip link set eth2 down"
            ]
            
            for cmd in cmds:
                output = tn.send_command(cmd, expect_string=r'[#$]')
                print(f"Vykdoma: {cmd} -> Rezultatas: {output.strip() if output else 'OK'}")
            
            print("\n>>> BLOKAVIMAS ATLIKTAS: Visos routerio sasajos isjungtos.")
            return True
    except Exception as e:
        print(f"Klaida vykdant komandas: {e}")
        return False

def main():
    try:
        print(f"[*] Jungiamasi prie GNS3 serverio: {GNS3_IP}")
        server = Gns3Connector(url=f"http://{GNS3_IP}:80")
        project = Project(name=PROJECT_NAME, connector=server)
        project.get()
        project.get_nodes()

        router_found = False
        for node in project.nodes:
            if node.name == "AlpineRouter" and node.status == "started":
                apply_physical_block(node.console)
                router_found = True
                break
        
        if not router_found:
            print("[!] KLAIDA: AlpineRouter nerastas arba neijungtas!")

    except Exception as e:
        print(f"KRITINE KLAIDA: {e}")

if __name__ == "__main__":
    main()
