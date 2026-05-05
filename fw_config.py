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

def apply_route_blocking(port):
    """Blokuoja kelius tarp tinklu naudojant Blackhole maršrutus."""
    print(f"\n[*] Jungiamasi prie AlpineRouter (port: {port})...")
    
    # Tinklai pagal tavo ipconfig planą
    networks = {
        "MAIN": "10.0.0.0/24",
        "ADMIN": "11.0.0.0/24",
        "SUPPORT": "10.1.0.0/24"
    }

    try:
        with ConnectHandler(**get_params(port)) as tn:
            tn.write_channel("\n")
            time.sleep(1)
            
            print("[*] Vykdomas srauto izoliavimas per maršrutizavimo lentelę...")
            
            # Išvalome galimus senus blackhole maršrutus, kad išvengtume klaidų
            # Tada pridedame naujus blackhole maršrutus
            # PASTABA: Tai blokuos srautą tik maršrutizatoriuje. 
            # Įrenginiai savo potinklio viduje vis tiek bendraus.
            
            cmds = [
                # Admin negali pasiekti kitu
                f"ip route add blackhole {networks['MAIN']} || true",
                f"ip route add blackhole {networks['SUPPORT']} || true",
                
                # Main negali pasiekti kitu
                f"ip route add blackhole {networks['ADMIN']} || true",
                # (Support-Main ryšio blokavimas)
                f"ip route add blackhole {networks['SUPPORT']} || true",
                
                # Support negali pasiekti kitu
                f"ip route add blackhole {networks['ADMIN']} || true",
                f"ip route add blackhole {networks['MAIN']} || true"
            ]
            
            for cmd in cmds:
                tn.send_command(cmd, expect_string=r'[#$]')
                print(f"Vykdoma: {cmd}")
            
            print("\n>>> TINKLAI IZOLIUOTI: Naudojamas Blackhole maršrutizavimas.")
            
    except Exception as e:
        print(f"Klaida: {e}")

def main():
    try:
        server = Gns3Connector(url=f"http://{GNS3_IP}:80")
        project = Project(name=PROJECT_NAME, connector=server)
        project.get()
        project.get_nodes()

        for node in project.nodes:
            if node.name == "AlpineRouter" and node.status == "started":
                apply_route_blocking(node.console)
                break
    except Exception as e:
        print(f"Kritinė klaida: {e}")

if __name__ == "__main__":
    main()
