import sys
import time
from gns3fy import Gns3Connector, Project
from netmiko import ConnectHandler

# --- KONFIGŪRACIJA ---
GNS3_IP = "192.168.56.102"
PROJECT_NAME = "a"

# IP Planas galiniams mazgams
IP_PLAN = {
    "AlpineLinux-1": ("11.0.0.2",  "11.0.0.1"),
    "AlpineLinux-2": ("10.0.0.11", "10.0.0.1"),
    "AlpineLinux-3": ("10.0.0.12", "10.0.0.1"),
    "AlpineLinux-4": ("10.1.0.10", "10.1.0.1"),
    "AlpineLinux-5": ("10.1.0.11", "10.1.0.1")
}

def get_netmiko_params(port):
    return {
        'device_type': 'generic_telnet',
        'host': GNS3_IP,
        'port': port,
        'timeout': 10,
    }

def configure_alpine(node_name, port, ip, gw):
    """Konfigūruoja Alpine Linux IP adresus."""
    print(f"\n[ALPINE] Konfigūruojamas {node_name}...")
    try:
        net_connect = ConnectHandler(**get_netmiko_params(port))
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
            print(f"    -> [OK] {cmd}")
        
        net_connect.disconnect()
        return True
    except Exception as e:
        print(f"    -> [!] Klaida: {e}")
        return False

def configure_ovs_main(node_name, port):
    """
    Konfigūruoja Main1 (Open vSwitch).
    Iš tavo 'ip a' matome br0, br1, br2, br3. 
    Čia galime pridėti specifines OVS komandas.
    """
    print(f"\n[OVS] Konfigūruojamas pagrindinis jungiklis: {node_name}...")
    try:
        net_connect = ConnectHandler(**get_get_netmiko_params(port))
        net_connect.write_channel("\n")
        time.sleep(1)

        # Pavyzdinės OVS komandos (jei reikia sujungti portus į tiltus)
        # Šiuo atveju tiesiog pakeliame visas fizines sąsajas
        commands = [f"ip link set eth{i} up" for i in range(8)]
        
        for cmd in commands:
            net_connect.send_command(cmd, expect_string=r'[#$]')
            
        print(f"    -> [OK] Visos eth sąsajos įjungtos.")
        net_connect.disconnect()
        return True
    except Exception as e:
        print(f"    -> [!] OVS Klaida: {e}")
        return False

def main():
    sys.stdout.reconfigure(line_buffering=True)
    error_count = 0
    
    try:
        server = Gns3Connector(url=f"http://{GNS3_IP}:80")
        project = Project(name=PROJECT_NAME, connector=server)
        project.get()
        project.get_nodes()

        for node in project.nodes:
            if node.status != "started":
                continue

            # 1. Jei tai Alpine mazgas
            if node.name in IP_PLAN:
                if not configure_alpine(node.name, node.console, *IP_PLAN[node.name]):
                    error_count += 1
            
            # 2. Jei tai Main1 (OVS) arba kiti OVS jungikliai
            elif node.name == "Main1" or "OVS" in node.name:
                if not configure_ovs_main(node.name, node.console):
                    print(f"    [WARN] Nepavyko pilnai sukonfigūruoti {node.name}")

        if error_count > 0:
            print(f"\n[FAILED] Baigta su {error_count} klaidomis.")
            sys.exit(1)
        else:
            print("\n[SUCCESS] Tinklas paruoštas!")

    except Exception as e:
        print(f"Kritinė klaida: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
