import sys
import time
from gns3fy import Gns3Connector, Project
from netmiko import ConnectHandler

# --- KONFIGŪRACIJA ---
GNS3_IP = "192.168.56.102"
PROJECT_NAME = "a"

# IP Planas Alpine mazgams
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

def configure_main1_ovs(port):
    """
    Konfigūruoja Main1 (OVS):
    eth0 -> mikrotik
    eth1, eth2, eth3 -> alpine mazgai
    """
    print(f"\n[OVS] Konfigūruojamas Main1 (Switching mode)...")
    try:
        with ConnectHandler(**get_params(port)) as tn:
            tn.write_channel("\n")
            time.sleep(1)
            
            # Komandų seka:
            # 1. Sukuriam br0 tiltą (jei nėra)
            # 2. Pridedam visas sąsajas į br0
            # 3. Pakeliam visas sąsajas
            
            commands = [
                "ovs-vsctl --if-exists del-br br0",
                "ovs-vsctl add-br br0",
            ]
            
            # Pridedame sąsajas eth0, eth1, eth2, eth3 į tiltą
            for i in range(4):
                commands.append(f"ovs-vsctl add-port br0 eth{i}")
                commands.append(f"ip link set eth{i} up")
            
            commands.append("ip link set br0 up")
            
            for cmd in commands:
                tn.send_command(cmd, expect_string=r'[#$]')
                print(f"    -> {cmd}")
                
        print("[OVS] Main1 konfigūracija baigta.")
        return True
    except Exception as e:
        print(f"    -> [!] OVS Klaida: {e}")
        return False

def configure_alpine(name, port, ip, gw):
    """Standartinis IP nustatymas Alpine mazguose."""
    print(f"\n[ALPINE] {name} (Port: {port})")
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
                configure_main1_ovs(node.console)
            elif node.name in IP_PLAN:
                configure_alpine(node.name, node.console, *IP_PLAN[node.name])

        print("\n[FINISH] Tinklas paruoštas. Bandykite PING.")
        
    except Exception as e:
        print(f"Kritinė klaida: {e}")

if __name__ == "__main__":
    main()
