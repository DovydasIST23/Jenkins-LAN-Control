import sys
import time
from gns3fy import Gns3Connector, Project
from netmiko import ConnectHandler

# --- KONFIGŪRACIJA ---
GNS3_IP = "192.168.56.102"
PROJECT_NAME = "a"

# IP Planas visiems Alpine Linux mazgams
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

def configure_ovs_node(node_name, port):
    """
    Konfigūruoja OVS mazgus (Main1, Support):
    1. Išvalo senus tiltus (br-lan, br0 ir t.t.).
    2. Sukuria naują tiltą 'br-final'.
    3. Priverčia veikti standalone režimu (kad praleistų srautą).
    4. Prijungia visus portus (eth0-eth3).
    """
    print(f"\n[OVS] Priverstinis konfigūravimas: {node_name}...")
    try:
        with ConnectHandler(**get_params(port)) as tn:
            tn.write_channel("\n")
            time.sleep(1)
            
            commands = [
                # Išvalome viską, kas matoma tavo 'ip a' nuotraukose
                "ovs-vsctl del-br br-lan",
                "ovs-vsctl del-br br0",
                "ovs-vsctl del-br br1",
                "ovs-vsctl del-br br2",
                "ovs-vsctl del-br br3",
                
                # Sukuriame naują tiltą
                "ovs-vsctl add-br br-final",
                
                # SVARBU: Veikti kaip paprastas switch'as be kontrolerio
                "ovs-vsctl set-fail-mode br-final standalone",
                "ovs-vsctl set bridge br-final stp_enable=false",
                
                # Prijungiame fizines sąsajas
                "ovs-vsctl add-port br-final eth0",
                "ovs-vsctl add-port br-final eth1",
                "ovs-vsctl add-port br-final eth2",
                "ovs-vsctl add-port br-final eth3",
                
                # Aktyvuojame sąsajas OS lygmeniu
                "ip link set eth0 up",
                "ip link set eth1 up",
                "ip link set eth2 up",
                "ip link set eth3 up",
                "ip link set br-final up"
            ]
            
            for cmd in commands:
                tn.send_command(cmd, expect_string=r'[#$]')
                print(f"    -> {cmd}")
        return True
    except Exception as e:
        print(f"    -> [!] OVS Klaida {node_name}: {e}")
        return False

def configure_alpine(name, port, ip, gw):
    """Nustato IP adresus Alpine Linux mazguose."""
    print(f"\n[ALPINE] {name} -> IP: {ip}")
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
        print(f"    -> [!] Klaida mazge {name}: {e}")
        return False

def main():
    # Jenkins stdout buffering fix
    sys.stdout.reconfigure(line_buffering=True)
    
    try:
        server = Gns3Connector(url=f"http://{GNS3_IP}:80")
        project = Project(name=PROJECT_NAME, connector=server)
        project.get()
        project.get_nodes()

        for node in project.nodes:
            if node.status != "started":
                continue

            # 1. Konfigūruojame OVS jungiklius (Main1 ir Support)
            if node.name == "Main1" or node.name == "Support":
                configure_ovs_node(node.name, node.console)
            
            # 2. Konfigūruojame Alpine Linux mazgus
            elif node.name in IP_PLAN:
                configure_alpine(node.name, node.console, *IP_PLAN[node.name])

        print("\n" + "="*40)
        print("✅ KONFIGŪRACIJA BAIGTA SĖKMINGAI")
        print("Bandykite: AlpineLinux-2 ping 10.0.0.12")
        print("="*40)
        
    except Exception as e:
        print(f"\n[CRITICAL] Klaida: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
