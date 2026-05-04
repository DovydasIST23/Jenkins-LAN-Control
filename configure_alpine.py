import sys
import time
from gns3fy import Gns3Connector, Project
from netmiko import ConnectHandler

# --- KONFIGŪRACIJA ---
GNS3_IP = "192.168.56.102"
PROJECT_NAME = "a"

# IP adresai galiniams taškams
IP_PLAN = {
    "AlpineLinux-1": ("11.0.0.2",  "11.0.0.1"),
    "AlpineLinux-2": ("10.0.0.11", "10.0.0.1"),
    "AlpineLinux-3": ("10.0.0.12", "10.0.0.1"),
    "AlpineLinux-4": ("10.1.0.10", "10.1.0.1"),
    "AlpineLinux-5": ("10.1.0.11", "10.1.0.1")
}

def get_params(port):
    return {
        'device_type': 'generic_telnet',
        'host': GNS3_IP,
        'port': port,
        'timeout': 10,
    }

def configure_main_ovs(port):
    """Sutvarko Main1 OVS, kad jis veiktų kaip paprastas switch'as."""
    print(f"\n[OVS] Konfigūruojamas Main1 (Switch režimas)...")
    try:
        with ConnectHandler(**get_params(port)) as tn:
            tn.write_channel("\n")
            time.sleep(1)
            
            # 1. Pašaliname senus tiltus, kad nebūtų konfliktų
            # 2. Sukuriame vieną pagrindinį tiltą br-lan
            # 3. Prijungiame visas eth sąsajas (kurios matomos tavo 'ip a')
            
            commands = [
                "ovs-vsctl del-br br-lan", # Išvalome seną
                "ovs-vsctl del-br br0",    # Išvalome šiukšles
                "ovs-vsctl del-br br1",
                "ovs-vsctl add-br br-lan", # Sukuriame naują švarų tiltą
            ]
            
            # Prijungiame sąsajas (tikriname eth0 iki eth3, nes jos dažniausiai naudojamos)
            # Pagal tavo nuotrauką Main1 turi eth0, eth1, eth2, eth3
            for i in range(4):
                commands.append(f"ovs-vsctl add-port br-lan eth{i}")
                commands.append(f"ip link set eth{i} up")
            
            commands.append("ip link set br-lan up")
            
            for cmd in commands:
                tn.send_command(cmd, expect_string=r'[#$]')
                print(f"    -> {cmd}")
                
        return True
    except Exception as e:
        print(f"    -> [!] OVS Klaida: {e}")
        return False

def configure_alpine(name, port, ip, gw):
    """Nustato Alpine Linux IP."""
    print(f"\n[ALPINE] {name} -> {ip}")
    try:
        with ConnectHandler(**get_params(port)) as tn:
            tn.write_channel("\n")
            time.sleep(1)
            cmds = [
                "ip addr flush dev eth0",
                f"ip addr add {ip}/24 dev eth0",
                "ip link set eth0 up",
                f"ip route add default via {gw}"
            ]
            for cmd in cmds:
                tn.send_command(cmd, expect_string=r'[#$]')
        return True
    except Exception as e:
        print(f"    -> [!] Klaida: {e}")
        return False

def main():
    sys.stdout.reconfigure(line_buffering=True)
    try:
        server = Gns3Connector(url=f"http://{GNS3_IP}:80")
        project = Project(name=PROJECT_NAME, connector=server)
        project.get()
        project.get_nodes()

        for node in project.nodes:
            if node.status != "started": continue
            
            if node.name == "Main1":
                configure_main_ovs(node.console)
            elif node.name in IP_PLAN:
                configure_alpine(node.name, node.console, *IP_PLAN[node.name])

        print("\n[FINISH] Viskas sukonfigūruota. Bandykite ping iš AlpineLinux-2.")
        
    except Exception as e:
        print(f"Klaida: {e}")

if __name__ == "__main__":
    main()
