import sys
import time
from gns3fy import Gns3Connector, Project
from netmiko import ConnectHandler

# --- KONFIGŪRACIJA ---
GNS3_IP = "192.168.56.102"
PROJECT_NAME = "a"

# Užtikriname, kad stdout naudos UTF-8, kad išvengtume koduotės klaidų
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# IP Planas specifiniams mazgams
IP_PLAN = {
    "AlpineLinux-1": ("11.0.0.2", "11.0.0.1"),
    "AlpineLinux-3": ("10.0.0.12", "10.0.0.1")
}

def get_params(port):
    return {
        'device_type': 'generic_telnet',
        'host': GNS3_IP,
        'port': port,
        'timeout': 15,
    }

def configure_admin_ovs(port):
    """Sutvarko Admin OVS: išvalo senus tiltus ir sujungia eth0-eth3."""
    print(f"\n[OVS] Tvarkomas Admin mazgas (Port: {port})...")
    try:
        with ConnectHandler(**get_params(port)) as tn:
            tn.write_channel("\n")
            time.sleep(1)
            
            commands = [
                "ovs-vsctl --if-exists del-br br-lan",
                "ovs-vsctl --if-exists del-br br-final",
                "ovs-vsctl add-br br-final",
                "ovs-vsctl set-fail-mode br-final standalone",
                # Prijungiame visus portus: eth3 (i Mikrotik) ir eth0 (i Alpine1)
                "ovs-vsctl add-port br-final eth0",
                "ovs-vsctl add-port br-final eth1",
                "ovs-vsctl add-port br-final eth2",
                "ovs-vsctl add-port br-final eth3",
                "ip link set eth0 up",
                "ip link set eth1 up",
                "ip link set eth2 up",
                "ip link set eth3 up",
                "ip link set br-final up",
                "ip addr add 11.0.0.100/24 dev br-final",
                "ovs-ofctl add-flow br-final action=normal"
            ]
            
            for cmd in commands:
                tn.send_command(cmd, expect_string=r'[#$]')
            print("OK: Admin OVS sukonfiguruotas.")
    except Exception as e:
        print(f"ERROR: Admin OVS klaida: {e}")

def configure_alpine(name, port, ip, gw):
    """Nustato IP adresa Alpine mazgui."""
    print(f"\n[ALPINE] Nustatomas {name} (IP: {ip})...")
    try:
        with ConnectHandler(**get_params(port)) as tn:
            tn.write_channel("\n")
            time.sleep(2)
            
            cmds = [
                "ip link set eth0 up",
                "ip addr flush dev eth0",
                f"ip addr add {ip}/24 dev eth0",
                f"ip route add default via {gw} || true"
            ]
            for cmd in cmds:
                tn.send_command(cmd, expect_string=r'[#$]')
            print(f"OK: {name} IP nustatytas.")
    except Exception as e:
        print(f"ERROR: {name} klaida: {e}")

def main():
    try:
        server = Gns3Connector(url=f"http://{GNS3_IP}:80")
        project = Project(name=PROJECT_NAME, connector=server)
        project.get()
        project.get_nodes()

        for node in project.nodes:
            if node.status == "started":
                # 1. Konfiguruojame Admin OVS
                if node.name == "Admin":
                    configure_admin_ovs(node.console)
                
                # 2. Konfiguruojame Alpine1 ir Alpine3
                if node.name in IP_PLAN:
                    ip, gw = IP_PLAN[node.name]
                    configure_alpine(node.name, node.console, ip, gw)

        print("\nKonfiguracija baigta sėkmingai.")
        
    except Exception as e:
        print(f"Kritinė klaida: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
