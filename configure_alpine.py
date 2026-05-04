import sys
import time
from gns3fy import Gns3Connector, Project
from netmiko import ConnectHandler

# --- KONFIGŪRACIJA ---
GNS3_IP = "192.168.56.102"
PROJECT_NAME = "a"

# IP Planas
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
    print(f"\n[OVS] Konfiguruojamas {node_name}...")
    try:
        with ConnectHandler(**get_params(port)) as tn:
            tn.write_channel("\n")
            time.sleep(1)
            
            # Priverstinis srauto leidimas (NORMAL action)
            commands = [
                "ovs-vsctl --if-exists del-br br-final",
                "ovs-vsctl add-br br-final",
                "ovs-vsctl set-fail-mode br-final standalone",
                "ovs-vsctl set bridge br-final stp_enable=false",
            ]
            
            for i in range(4):
                commands.append(f"ovs-vsctl add-port br-final eth{i}")
                commands.append(f"ip link set eth{i} up")
            
            # Pridedame IP patiems tiltams, kad jie butu "gyvi" GNS3 aplinkoje
            if node_name == "Main1":
                commands.append("ip addr add 10.0.0.100/24 dev br-final")
            else:
                commands.append("ip addr add 10.1.0.100/24 dev br-final")
                
            commands.append("ip link set br-final up")
            # Priverstinai nurodome OVS elgtis kaip paprastam switchui
            commands.append("ovs-ofctl add-flow br-final action=normal")
            
            for cmd in commands:
                tn.send_command(cmd, expect_string=r'[#$]')
        return True
    except Exception as e:
        print(f"    -> OVS Klaida: {e}")
        return False

def configure_alpine(name, port, ip, gw):
    print(f"[ALPINE] {name} -> {ip}")
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
        print(f"    -> Alpine Klaida: {e}")
        return False

def main():
    # Fix Jenkins encoding issues
    sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
    
    try:
        server = Gns3Connector(url=f"http://{GNS3_IP}:80")
        project = Project(name=PROJECT_NAME, connector=server)
        project.get()
        project.get_nodes()

        for node in project.nodes:
            if node.status != "started": continue
            if node.name in ["Main1", "Support"]:
                configure_ovs_node(node.name, node.console)
            elif node.name in IP_PLAN:
                configure_alpine(node.name, node.console, *IP_PLAN[node.name])

        print("\nKONFIGURACIJA BAIGTA")
        
    except Exception as e:
        print(f"Kritine klaida: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
