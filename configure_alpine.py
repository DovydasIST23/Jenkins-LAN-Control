import sys
import time
from gns3fy import Gns3Connector, Project
from netmiko import ConnectHandler

# --- KONFIGURACIJA ---
GNS3_IP = "192.168.56.102"
PROJECT_NAME = "a"

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# IP Planas galiniams įrenginiams
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
    """Konfiguruoja AlpineRouter: įjungia forwarding ir priskiria IP adresus."""
    print(f"\n[ROUTER] AlpineRouter konfigūravimas (Console: {port})...")
    try:
        with ConnectHandler(**get_params(port)) as tn:
            tn.write_channel("\n")
            time.sleep(1)
            cmds = [
                # 1. Įjungiam IP Forwarding, kad paketas galėtų keliauti tarp eth0, eth1 ir eth2
                "sysctl -w net.ipv4.ip_forward=1",
                "echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf",
                # 2. Užtikriname, kad sąsajos būtų aktyvios ir turėtų IP
                "ip link set eth0 up",
                "ip link set eth1 up",
                "ip link set eth2 up",
                "ip addr flush dev eth0",
                "ip addr flush dev eth1",
                "ip addr flush dev eth2",
                "ip addr add 11.0.0.1/24 dev eth0",
                "ip addr add 10.0.0.1/24 dev eth1",
                "ip addr add 10.1.0.1/24 dev eth2"
            ]
            for cmd in cmds:
                tn.send_command(cmd, expect_string=r'[#$]')
            print("OK: AlpineRouter paruoštas maršrutizavimui.")
        return True
    except Exception as e:
        print(f"KLAIDA konfigūruojant Routerį: {e}")
        return False

def configure_ovs_logic(node_name, port):
    """Konfiguruoja OVS mazgus ir leidžia ICMP (ping) srautą."""
    print(f"\n[OVS] {node_name} konfigūravimas...")
    try:
        with ConnectHandler(**get_params(port)) as tn:
            tn.write_channel("\n")
            time.sleep(1)
            
            # Management IP ir Gateway paruošimas patiems switchams
            target_ip = ""
            target_gw = ""
            if node_name == "Admin": 
                target_ip, target_gw = "11.0.0.100/24", "11.0.0.1"
            elif node_name == "Main1": 
                target_ip, target_gw = "10.0.0.100/24", "10.0.0.1"
            elif node_name == "Support": 
                target_ip, target_gw = "10.1.0.100/24", "10.1.0.1"

            setup_cmds = [
                "ovs-vsctl --if-exists del-br br-final",
                "ovs-vsctl add-br br-final",
                "ovs-vsctl set-fail-mode br-final standalone"
            ]
            
            # Pridedame visus portus
            for i in range(4):
                setup_cmds.append(f"ovs-vsctl add-port br-final eth{i}")
                setup_cmds.append(f"ip link set eth{i} up")
            
            setup_cmds += [
                "ip link set br-final up",
                "ip addr flush dev br-final",
                f"ip addr add {target_ip} dev br-final",
                f"ip route add default via {target_gw} || true",
                # LEIDŽIAME VISĄ SRAUTĄ (įskaitant ping)
                "ovs-ofctl del-flows br-final",
                "ovs-ofctl add-flow br-final action=normal"
            ]

            for cmd in setup_cmds:
                tn.send_command(cmd, expect_string=r'[#$]')
            print(f"OK: {node_name} sukonfigūruotas (IP: {target_ip}).")
        return True
    except Exception as e:
        print(f"KLAIDA OVS {node_name}: {e}")
        return False

def configure_alpine_logic(name, port, ip, gw):
    """Konfiguruoja galinius Alpine mazgus su teisingu Gateway."""
    print(f"\n[ALPINE] {name} -> IP: {ip}")
    try:
        with ConnectHandler(**get_params(port)) as tn:
            tn.write_channel("\n")
            time.sleep(1)
            cmds = [
                "ip link set eth0 up",
                "ip addr flush dev eth0",
                f"ip addr add {ip}/24 dev eth0",
                # Išvalom senus maršrutus ir pridedam naują
                "ip route del default || true",
                f"ip route add default via {gw}"
            ]
            for cmd in cmds:
                tn.send_command(cmd, expect_string=r'[#$]')
            print(f"OK: {name} paruoštas.")
        return True
    except Exception as e:
        print(f"KLAIDA Alpine {name}: {e}")
        return False

def main():
    try:
        server = Gns3Connector(url=f"http://{GNS3_IP}:80")
        project = Project(name=PROJECT_NAME, connector=server)
        project.get()
        project.get_nodes()

        # 1 ETAPAS: Maršrutizatorius (svarbiausia dalis)
        for node in project.nodes:
            if node.name == "AlpineRouter" and node.status == "started":
                configure_alpine_router(node.console)

        # 2 ETAPAS: Switchai (kad jie patys būtų pinginami)
        ovs_names = ["Main1", "Support", "Admin"]
        for node in project.nodes:
            if node.name in ovs_names and node.status == "started":
                configure_ovs_logic(node.name, node.console)

        # 3 ETAPAS: Galiniai mazgai
        for node in project.nodes:
            if node.name in IP_PLAN and node.status == "started":
                ip, gw = IP_PLAN[node.name]
                configure_alpine_logic(node.name, node.console, ip, gw)

        print("\nKonfigūracija sėkmingai baigta. Galite bandyti ping tarp bet kurių įrenginių.")
    except Exception as e:
        print(f"KRITINĖ KLAIDA: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
