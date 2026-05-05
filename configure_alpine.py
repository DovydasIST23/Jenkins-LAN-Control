import sys
import time
from gns3fy import Gns3Connector, Project
from netmiko import ConnectHandler

# --- KONFIGURACIJA ---
GNS3_IP = "192.168.56.102"
PROJECT_NAME = "a"

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
    """Konfigūruoja AlpineRouter: įjungia forwarding ir priverstinai pakelia sąsajas."""
    print(f"\n[ROUTER] Konfigūruojamas AlpineRouter...")
    try:
        with ConnectHandler(**get_params(port)) as tn:
            tn.write_channel("\n")
            time.sleep(1)
            cmds = [
                # Įjungiam maršrutizavimą (Kritinė dalis!)
                "sysctl -w net.ipv4.ip_forward=1",
                "echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf",
                # Priverstinis sąsajų aktyvavimas
                "ip link set eth0 up",
                "ip link set eth1 up",
                "ip link set eth2 up",
                # IP adresų priskyrimas
                "ip addr flush dev eth0",
                "ip addr flush dev eth1",
                "ip addr flush dev eth2",
                "ip addr add 11.0.0.1/24 dev eth0",
                "ip addr add 10.0.0.1/24 dev eth1",
                "ip addr add 10.1.0.1/24 dev eth2"
            ]
            for cmd in cmds:
                tn.send_command(cmd, expect_string=r'[#$]')
            print("OK: AlpineRouter dabar maršrutizuoja srautą.")
        return True
    except Exception as e:
        print(f"KLAIDA Routeryje: {e}")
        return False

def configure_ovs_logic(node_name, port):
    """Konfigūruoja OVS ir užtikrina, kad jis praleistų visą srautą."""
    print(f"\n[OVS] Konfigūruojamas {node_name}...")
    try:
        with ConnectHandler(**get_params(port)) as tn:
            tn.write_channel("\n")
            time.sleep(1)
            
            target_ip, target_gw = "", ""
            if node_name == "Admin": target_ip, target_gw = "11.0.0.100/24", "11.0.0.1"
            elif node_name == "Main1": target_ip, target_gw = "10.0.0.100/24", "10.0.0.1"
            elif node_name == "Support": target_ip, target_gw = "10.1.0.100/24", "10.1.0.1"

            setup_cmds = [
                "ovs-vsctl --if-exists del-br br-final",
                "ovs-vsctl add-br br-final",
                "ovs-vsctl set-fail-mode br-final standalone"
            ]
            for i in range(4):
                setup_cmds.append(f"ovs-vsctl add-port br-final eth{i}")
                setup_cmds.append(f"ip link set eth{i} up")
            
            setup_cmds += [
                "ip link set br-final up",
                "ip addr flush dev br-final",
                f"ip addr add {target_ip} dev br-final",
                # Išvalom srauto taisykles (Flows), kad niekas nebūtų blokuojama
                "ovs-ofctl del-flows br-final",
                "ovs-ofctl add-flow br-final action=normal",
                f"ip route add default via {target_gw} || true"
            ]
            for cmd in setup_cmds:
                tn.send_command(cmd, expect_string=r'[#$]')
            print(f"OK: {node_name} sukonfigūruotas.")
        return True
    except Exception as e:
        print(f"KLAIDA OVS: {e}")
        return False

def configure_alpine_logic(name, port, ip, gw):
    """Konfigūruoja galinius mazgus su švariu maršrutu."""
    print(f"\n[NODE] Konfigūruojamas {name}...")
    try:
        with ConnectHandler(**get_params(port)) as tn:
            tn.write_channel("\n")
            time.sleep(1)
            cmds = [
                "ip link set eth0 up",
                "ip addr flush dev eth0",
                f"ip addr add {ip}/24 dev eth0",
                # Išvalom senus maršrutus, kad nebūtų konfliktų
                "ip route del default || true",
                f"ip route add default via {gw}"
            ]
            for cmd in cmds:
                tn.send_command(cmd, expect_string=r'[#$]')
            print(f"OK: {name} paruoštas.")
        return True
    except Exception as e:
        print(f"KLAIDA Mazge: {e}")
        return False

def main():
    try:
        server = Gns3Connector(url=f"http://{GNS3_IP}:80")
        project = Project(name=PROJECT_NAME, connector=server)
        project.get()
        project.get_nodes()

        # 1. Konfigūruojame Routerį pirmiausia
        for node in project.nodes:
            if node.name == "AlpineRouter" and node.status == "started":
                configure_alpine_router(node.console)

        # 2. Konfigūruojame Jungiklius
        ovs_names = ["Main1", "Support", "Admin"]
        for node in project.nodes:
            if node.name in ovs_names and node.status == "started":
                configure_ovs_logic(node.name, node.console)

        # 3. Konfigūruojame Galinius mazgus
        for node in project.nodes:
            if node.name in IP_PLAN and node.status == "started":
                ip, gw = IP_PLAN[node.name]
                configure_alpine_logic(node.name, node.console, ip, gw)

        print("\nKonfigūracija baigta. Tikrinkite ping tarp tinklų.")
    except Exception as e:
        print(f"KRITINĖ KLAIDA: {e}")

if __name__ == "__main__":
    main()
