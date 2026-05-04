import sys
import time
from gns3fy import Gns3Connector, Project
from netmiko import ConnectHandler

# --- KONFIGŪRACIJA ---
GNS3_IP = "192.168.56.102"
PROJECT_NAME = "a"

# IP Planas pagal tavo topologiją
# (IP_adresas, Gateway)
IP_PLAN = {
    "AlpineLinux-1": ("11.0.0.2",  "11.0.0.1"),
    "AlpineLinux-2": ("10.0.0.11", "10.0.0.1"),
    "AlpineLinux-3": ("10.0.0.12", "10.0.0.1"),
    "AlpineLinux-4": ("10.1.0.10", "10.1.0.1"),
    "AlpineLinux-5": ("10.1.0.11", "10.1.0.1")
}

# Jei OVS jungikliai turi IP valdymui, juos galima pridėti čia
OVS_NODES = ["OVS-1", "OVS-2", "OVS-3"]

def configure_alpine(node_name, console_port, ip, gw):
    """Konfigūruoja Alpine Linux per Telnet."""
    device_params = {
        'device_type': 'generic_telnet',
        'host': GNS3_IP,
        'port': console_port,
        'timeout': 10,
    }
    
    print(f"\n[PROCESS] Jungiamasi prie {node_name} (Port: {console_port})...")
    
    try:
        net_connect = ConnectHandler(**device_params)
        net_connect.write_channel("\n")
        time.sleep(1)
        
        commands = [
            "ip addr flush dev eth0",
            f"ip addr add {ip}/24 dev eth0",
            "ip link set eth0 up",
            f"ip route add default via {gw}"
        ]
        
        for cmd in commands:
            net_connect.send_command(cmd, expect_string=r'[#$]')
            print(f"  -> [OK] {cmd}")
            
        net_connect.disconnect()
        return True
    except Exception as e:
        print(f"  -> [!] Klaida mazge {node_name}: {e}")
        return False

def configure_ovs(node_name, console_port):
    """
    OVS konfigūracija (pvz., jei reikia įjungti bridge ar specifinius nustatymus).
    Paprastai GNS3 OVS veikia kaip L2 jungiklis be papildomos IP konfigūracijos,
    bet čia paruošta vieta komandoms.
    """
    print(f"\n[PROCESS] Tikrinamas jungiklis {node_name} (Port: {console_port})...")
    # Čia galėtum pridėti ovs-vsctl komandas, jei jų reikia
    return True

def main():
    sys.stdout.reconfigure(line_buffering=True)
    error_count = 0
    success_count = 0
    
    try:
        server_url = f"http://{GNS3_IP}:80"
        print(f"[INFO] Jungiamasi prie GNS3: {server_url}")
        
        server = Gns3Connector(url=server_url)
        project = Project(name=PROJECT_NAME, connector=server)
        project.get()
        project.get_nodes()

        for node in project.nodes:
            # 1. Konfigūruojame Alpine Linux
            if node.name in IP_PLAN:
                if node.status == "started":
                    if configure_alpine(node.name, node.console, *IP_PLAN[node.name]):
                        success_count += 1
                    else:
                        error_count += 1
                else:
                    print(f"[WARN] {node.name} neaktyvus. Praleidžiama.")

            # 2. Patikriname OVS mazgus (jei reikia)
            elif node.name in OVS_NODES:
                if node.status == "started":
                    configure_ovs(node.name, node.console)
                else:
                    print(f"[WARN] {node.name} neaktyvus.")

        print(f"\n--- REZULTATAI ---")
        print(f"Sėkmingai sukonfigūruota: {success_count}")
        print(f"Klaidos: {error_count}")

        if error_count > 0:
            sys.exit(1)
            
    except Exception as e:
        print(f"\n[ERROR] Kritinė klaida: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
