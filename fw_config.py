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

def apply_firewall_rules(port):
    """Įdiegia iptables taisykles AlpineRouter mazge srauto blokavimui."""
    print(f"\n[*] Jungiamasi prie AlpineRouter (port: {port}) ugniasienės konfigūravimui...")
    
    # Tinklų apibrėžimai pagal tavo IP planą
    networks = {
        "MAIN": "10.0.0.0/24",
        "ADMIN": "11.0.0.0/24",
        "SUPPORT": "10.1.0.0/24"
    }

    try:
        with ConnectHandler(**get_params(port)) as tn:
            tn.write_channel("\n")
            time.sleep(1)
            
            # 1. Išvalome esamas taisykles (nebūtina, bet saugu pradedant)
            # 2. Nustatome numatytąją politiką ACCEPT (kad neužsirakintume), 
            #    bet blokuojame specifinius perėjimus.
            
            cmds = [
                "iptables -F FORWARD",  # Išvalyti nukreipimo taisykles
                
                # Blokavimas: Admin <-> Main
                f"iptables -A FORWARD -s {networks['ADMIN']} -d {networks['MAIN']} -j DROP",
                f"iptables -A FORWARD -s {networks['MAIN']} -d {networks['ADMIN']} -j DROP",
                
                # Blokavimas: Admin <-> Support
                f"iptables -A FORWARD -s {networks['ADMIN']} -d {networks['SUPPORT']} -j DROP",
                f"iptables -A FORWARD -s {networks['SUPPORT']} -d {networks['ADMIN']} -j DROP",
                
                # Blokavimas: Support <-> Main
                f"iptables -A FORWARD -s {networks['SUPPORT']} -d {networks['MAIN']} -j DROP",
                f"iptables -A FORWARD -s {networks['MAIN']} -d {networks['SUPPORT']} -j DROP",
                
                # Išsaugome (Alpine Linux specifika, kad liktų po perkrovimo)
                "rc-update add iptables default || true",
                "/etc/init.d/iptables save || true"
            ]
            
            for cmd in cmds:
                output = tn.send_command(cmd, expect_string=r'[#$]')
                print(f"Vykdoma: {cmd}")
            
            print("\n>>> Ugniasienės taisyklės įdiegtos sėkmingai.")
            print(">>> Blokavimas aktyvuotas tarp Admin, Main ir Support segmentų.")
            
    except Exception as e:
        print(f"Klaida konfigūruojant ugniasienę: {e}")

def main():
    try:
        server = Gns3Connector(url=f"http://{GNS3_IP}:80")
        project = Project(name=PROJECT_NAME, connector=server)
        project.get()
        project.get_nodes()

        router_found = False
        for node in project.nodes:
            if node.name == "AlpineRouter" and node.status == "started":
                apply_firewall_rules(node.console)
                router_found = True
                break
        
        if not router_found:
            print("[!] Klaida: AlpineRouter nerastas arba neįjungtas.")

    except Exception as e:
        print(f"Kritinė klaida: {e}")

if __name__ == "__main__":
    main()
