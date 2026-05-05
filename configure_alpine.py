import sys
import time
from gns3fy import Gns3Connector, Project
from netmiko import ConnectHandler

# --- KONFIGURACIJA ---
GNS3_IP = "192.168.56.102"
PROJECT_NAME = "a"

# Užtikriname UTF-8 palaikymą Windows aplinkoje
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# IP Planas galiniams mazgams (IP, Gateway)
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
        'timeout': 15,
    }

def configure_alpine_router(port):
    """Konfigūruoja AlpineRouter: įjungia IP forwarding ir priskiria IP adresus sąsajoms."""
    print(f"\n[1/3] Konfigūruojamas AlpineRouter (Console: {port})...")
    try:
        with ConnectHandler(**get_params(port)) as tn:
            tn.write_channel("\n")
            time.sleep(1)
            cmds = [
                # Įjungiam IP forwarding (maršrutizavimą)
                "sysctl -w net.ipv4.ip_forward=1",
                "echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf",
                # Pakeliam sąsajas
                "ip link set eth0 up",
                "ip link set eth1 up",
                "ip link set eth2 up",
                # Išvalom senus IP ir priskiriam naujus (GW adresai)
                "ip addr flush dev eth0",
                "ip addr flush dev eth1",
                "ip addr flush dev eth2",
                "ip addr add 11.0.0.1/24 dev eth0", # Admin tinklas
                "ip addr add 10.0.0.1/24 dev eth1", # Main tinklas
                "ip addr add 10.1.0.1/24 dev eth2"  # Support tinklas
            ]
            for cmd in cmds:
                tn.send_command(cmd, expect_string=r'[#$]')
            print(">>> AlpineRouter paruoštas srauto perdavimui.")
        return True
    except Exception as e:
        print(f"!!! KLAIDA konfigūruojant Routerį: {e}")
        return False

def configure_ovs_logic(node_name, port):
    """Konfigūruoja OVS: sukuria tiltą, prideda portus ir nustato valdymo IP."""
    print(f"\n[2/3] Konfigūruojamas OVS Jungiklis: {node_name}...")
    try:
        with ConnectHandler(**get_params(port)) as tn:
            tn.write_channel("\n")
            time.sleep(1)
            
            # Nustatom valdymo IP ir Gateway patiems switchams
            target_ip, target_gw = "", ""
            if node_name == "Admin": target_ip, target_gw = "11.0.0.100/24", "11.0.0.1"
            elif node_name == "Main1": target_ip, target_gw = "10.0.0.100/24", "10.0.0.1"
            elif node_name == "Support": target_ip, target_gw = "10.1.0.100/24", "10.1.0.1"

            setup_cmds = [
                "ovs-vsctl --if-exists del-br br-final",
                "ovs-vsctl add-br br-final",
                "ovs-vsctl set-fail-mode br-final standalone"
            ]
            # Pridedame fizinius eth portus prie OVS tilto
            for i in range(4):
                setup_cmds.append(f"ovs-vsctl add-port br-final eth{i}")
                setup_cmds.append(f"ip link set eth{i} up")
            
            setup_cmds += [
                "ip link set br-final up",
                "ip addr flush dev br-final",
                f"ip addr add {target_ip} dev br-final",
                f"ip route add default via {target_gw} || true",
                # Leidžiame visą srautą (išvalom senus apribojimus)
                "ovs-ofctl del-flows br-final",
                "ovs-ofctl add-flow br-final action=normal"
            ]

            for cmd in setup_cmds:
                tn.send_command(cmd, expect_string=r'[#$]')
            print(f">>> {node_name} sukonfigūruotas (IP: {target_ip}).")
        return True
    except Exception as e:
        print(f"!!! KLAIDA OVS {node_name}: {e}")
        return False

def configure_alpine_logic(name, port, ip, gw):
    """Konfigūruoja galinį Alpine mazgą: IP ir maršrutas į Routerį."""
    print(f"\n[3/3] Konfigūruojamas Mazgas: {name}...")
    try:
        with ConnectHandler(**get_params(port)) as tn:
            tn.write_channel("\n")
            time.sleep(1)
            cmds = [
                "ip link set eth0 up",
                "ip addr flush dev eth0",
                f"ip addr add {ip}/24 dev eth0",
                "ip route del default || true",
                f"ip route add default via {gw}"
            ]
            for cmd in cmds:
                tn.send_command(cmd, expect_string=r'[#$]')
            print(f">>> {name} paruoštas (IP: {ip}, GW: {gw}).")
        return True
    except Exception as e:
        print(f"!!! KLAIDA Alpine {name}: {e}")
        return False

def main():
    try:
        server = Gns3Connector(url=f"http://{GNS3_IP}:80")
        project = Project(name=PROJECT_NAME, connector=server)
        project.get()
        project.get_nodes()

        print("--- PRADEDAMA VISIŠKA TINKLO KONFIGŪRACIJA ---")

        # 1. Konfigūruojame Routerį
        for node in project.nodes:
            if node.name == "AlpineRouter" and node.status == "started":
                configure_alpine_router(node.console)

        # 2. Konfigūruojame OVS jungiklius
        ovs_names = ["Main1", "Support", "Admin"]
        for node in project.nodes:
            if node.name in ovs_names and node.status == "started":
                configure_ovs_logic(node.name, node.console)

        # 3. Konfigūruojame galinius Alpine mazgus
        for node in project.nodes:
            if node.name in IP_PLAN and node.status == "started":
                ip, gw = IP_PLAN[node.name]
                configure_alpine_logic(node.name, node.console, ip, gw)

        print("\n--- KONFIGŪRACIJA BAIGTA SĖKMINGAI ---")
        print("Testavimas: pabandykite 'ping 10.0.0.11' iš AlpineLinux-1 konsolės.")
        
    except Exception as e:
        print(f"\n!!! KRITINĖ KLAIDA: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
