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
        'timeout': 10,
    }

def configure_ovs_logic(node_name, port):
    """
    Konfigūruoja OVS: Išvalo senus tiltus, sukuria naują ir aktyvuoja portus.
    IP adresas priskiriamas pačiam tiltui tik pabaigoje.
    """
    print(f"\n[OVS] {node_name} konfigūravimas...")
    try:
        with ConnectHandler(**get_params(port)) as tn:
            tn.write_channel("\n")
            time.sleep(1)
            
            # 1. Švarus tiltų valymas (pašalina br-lan, kuris matomas tavo nuotraukose)
            commands = [
                "ovs-vsctl --if-exists del-br br-final",
                "ovs-vsctl --if-exists del-br br-lan",
                "ovs-vsctl add-br br-final",
                "ovs-vsctl set-fail-mode br-final standalone"
            ]
            
            # 2. Portų prijungimas ir pakėlimas
            for i in range(4):
                commands.append(f"ovs-vsctl add-port br-final eth{i}")
                commands.append(f"ip link set eth{i} up")
            
            commands.append("ip link set br-final up")
            
            # 3. IP priskyrimas OVS mazgui (Management IP)
            if node_name == "Main1":
                commands.append("ip addr flush dev br-final")
                commands.append("ip addr add 10.0.0.100/24 dev br-final")
            elif node_name == "Support":
                commands.append("ip addr flush dev br-final")
                commands.append("ip addr add 10.1.0.100/24 dev br-final")

            for cmd in commands:
                tn.send_command(cmd, expect_string=r'[#$]')
        return True
    except Exception as e:
        print(f"    -> [!] OVS Klaida: {e}")
        return False

def configure_alpine_logic(name, port, ip, gw):
    """Priskiria IP adresą Alpine Linux mazgui."""
    print(f"[ALPINE] {name} -> Nustatomas IP: {ip}")
    try:
        with ConnectHandler(**get_params(port)) as tn:
            tn.write_channel("\n")
            time.sleep(1)
            # Flush komanda išvalo senus/klaidingus IP adresus
            cmds = [
                "ip addr flush dev eth0",
                f"ip addr add {ip}/24 dev eth0",
                "ip link set eth0 up",
                f"ip route add default via {gw} || true" 
            ]
            for cmd in cmds:
                tn.send_command(cmd, expect_string=r'[#$]')
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

        # SVARBU: Pirmiausia paruošiame OVS tiltus, tada dedame IP ant Alpine
        ovs_nodes = [n for n in project.nodes if n.name in ["Main1", "Support"]]
        alpine_nodes = [n for n in project.nodes if n.name in IP_PLAN]

        for node in ovs_nodes:
            if node.status == "started":
                configure_ovs_logic(node.name, node.console)

        for node in alpine_nodes:
            if node.status == "started":
                ip, gw = IP_PLAN[node.name]
                configure_alpine_logic(node.name, node.console, ip, gw)

        print("\n✅ Konfigūracija baigta. IP adresai priskirti visiems aktyviems mazgams.")
        
    except Exception as e:
        print(f"Kritinė klaida: {e}")

if __name__ == "__main__":
    main()
