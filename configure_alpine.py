import sys
import time
from gns3fy import Gns3Connector, Project
from netmiko import ConnectHandler

# --- KONFIGŪRACIJA ---
GNS3_IP = "192.168.56.102"
PROJECT_NAME = "a"

# IP Planas visiems įrenginiams
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

def configure_ovs_node(node_name, port):
    """Konfigūruoja OVS mazgus: Main1, Support, Admin."""
    print(f"\n[OVS] {node_name} (Console: {port}) konfigūravimas...")
    try:
        with ConnectHandler(**get_params(port)) as tn:
            tn.write_channel("\n")
            time.sleep(1)
            
            # Išvalome viską ir sukuriame br-final
            commands = [
                "ovs-vsctl --if-exists del-br br-final",
                "ovs-vsctl --if-exists del-br br-lan",
                "ovs-vsctl --if-exists del-br br0", # Išvalome br0, jei toks liko iš praeitų bandymų
                "ovs-vsctl add-br br-final",
                "ovs-vsctl set-fail-mode br-final standalone",
                "ovs-vsctl set bridge br-final stp_enable=false"
            ]
            
            # Prijungiame fizinius portus (eth0-eth3)
            # Svarbu: eth0 turi jau nebepriklausyti br-lan, kad šis veiktų
            for i in range(4):
                commands.append(f"ovs-vsctl add-port br-final eth{i} -- set Interface eth{i} up")
                commands.append(f"ip link set eth{i} up")
            
            commands.append("ip link set br-final up")
            commands.append("ovs-ofctl add-flow br-final action=normal")
            
            # Management IP
            if node_name == "Main1":
                commands.append("ip addr add 10.0.0.100/24 dev br-final")
            elif node_name == "Support":
                commands.append("ip addr add 10.1.0.100/24 dev br-final")
            elif node_name == "Admin":
                commands.append("ip addr add 11.0.0.100/24 dev br-final")

            for cmd in commands:
                tn.send_command(cmd, expect_string=r'[#$]')
        return True
    except Exception as e:
        print(f"    -> [!] OVS Klaida: {e}")
        return False

def configure_alpine(name, port, ip, gw):
    """Priverstinis IP priskyrimas Alpine mazgams."""
    print(f"\n[ALPINE] {name} -> IP: {ip}")
    try:
        with ConnectHandler(**get_params(port)) as tn:
            tn.write_channel("\n")
            time.sleep(2) # Daugiau laiko Alpine atsibusti
            
            # Jei eth0 nerandamas, bandome priverstinai pakelti visas sąsajas
            cmds = [
                "ip link set eth0 up || true", 
                "ip addr flush dev eth0 || true",
                f"ip addr add {ip}/24 dev eth0",
                "ip link set eth0 up",
                f"ip route add default via {gw} || true"
            ]
            for cmd in cmds:
                res = tn.send_command(cmd, expect_string=r'[#$]')
                if "can't find device" in res:
                    print(f"    -> [!] Perspėjimas: {name} vis dar nemato eth0.")
        return True
    except Exception as e:
        print(f"    -> [!] Alpine Klaida: {e}")
        return False

def main():
    sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
    try:
        server = Gns3Connector(url=f"http://{GNS3_IP}:80")
        project = Project(name=PROJECT_NAME, connector=server)
        project.get()
        project.get_nodes()

        # 1. Konfigūruojame OVS mazgus (įskaitant Admin)
        ovs_list = ["Main1", "Support", "Admin"]
        for node in project.nodes:
            if node.name in ovs_list and node.status == "started":
                configure_ovs_node(node.name, node.console)

        # 2. Konfigūruojame Alpine mazgus
        for node in project.nodes:
            if node.name in IP_PLAN and node.status == "started":
                ip, gw = IP_PLAN[node.name]
                configure_alpine(node.name, node.console, ip, gw)

        print("\n✅ Konfigūracija baigta.")
    except Exception as e:
        print(f"Klaida: {e}")

if __name__ == "__main__":
    main()
