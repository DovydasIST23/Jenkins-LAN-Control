import sys
import time
from gns3fy import Gns3Connector, Project
from netmiko import ConnectHandler

# --- KONFIGURACIJA ---
GNS3_IP = "192.168.56.102"
PROJECT_NAME = "a"

# Užtikriname, kad stdout naudos UTF-8 Windows aplinkoje
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

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

def configure_ovs_logic(node_name, port):
    """Konfiguruoja OVS mazgus, isvalo senus tiltus ir sujungia portus."""
    print(f"\n[OVS] {node_name} konfigūravimas (Console: {port})...")
    try:
        with ConnectHandler(**get_params(port)) as tn:
            tn.write_channel("\n")
            time.sleep(1)
            
            # Agresyvus valymas, kad eth portai nebutu "busy"
            cleanup_cmds = [
                "ovs-vsctl --if-exists del-br br-final",
                "ovs-vsctl --if-exists del-br br-lan",
                "ovs-vsctl --if-exists del-br br0",
                "ovs-vsctl add-br br-final",
                "ovs-vsctl set-fail-mode br-final standalone"
            ]
            
            for cmd in cleanup_cmds:
                tn.send_command(cmd, expect_string=r'[#$]')
            
            # Portu prijungimas (eth0-eth3)
            setup_cmds = []
            for i in range(4):
                setup_cmds.append(f"ovs-vsctl add-port br-final eth{i}")
                setup_cmds.append(f"ip link set eth{i} up")
            
            setup_cmds.append("ip link set br-final up")
            setup_cmds.append("ovs-ofctl add-flow br-final action=normal")
            
            # Management IP priskyrimas patiems switchams
            if node_name == "Main1":
                setup_cmds.append("ip addr add 10.0.0.100/24 dev br-final")
            elif node_name == "Support":
                setup_cmds.append("ip addr add 10.1.0.100/24 dev br-final")
            elif node_name == "Admin":
                setup_cmds.append("ip addr add 11.0.0.100/24 dev br-final")

            for cmd in setup_cmds:
                tn.send_command(cmd, expect_string=r'[#$]')
            
            print(f"OK: {node_name} sukonfiguruotas.")
        return True
    except Exception as e:
        print(f"KLAIDA OVS {node_name}: {e}")
        return False

def configure_alpine_logic(name, port, ip, gw):
    """Priskiria IP adresa Alpine mazgui."""
    print(f"\n[ALPINE] {name} -> IP: {ip}")
    try:
        with ConnectHandler(**get_params(port)) as tn:
            tn.write_channel("\n")
            time.sleep(2) # Laukiam, kol eth0 atsiras OS lygmenyje
            
            cmds = [
                "ip link set eth0 up || true",
                "ip addr flush dev eth0",
                f"ip addr add {ip}/24 dev eth0",
                f"ip route add default via {gw} || true"
            ]
            for cmd in cmds:
                output = tn.send_command(cmd, expect_string=r'[#$]')
                if "can't find device" in output:
                    print(f"ISPĖJIMAS: {name} vis dar nemato eth0!")
            
            print(f"OK: {name} sukonfiguruotas.")
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

        # 1 ETAPAS: Konfiguruojame visus OVS
        ovs_names = ["Main1", "Support", "Admin"]
        for node in project.nodes:
            if node.name in ovs_names and node.status == "started":
                configure_ovs_logic(node.name, node.console)

        # 2 ETAPAS: Konfiguruojame visus Alpine
        for node in project.nodes:
            if node.name in IP_PLAN and node.status == "started":
                ip, gw = IP_PLAN[node.name]
                configure_alpine_logic(node.name, node.console, ip, gw)

        print("\nKonfiguracija baigta.")
        
    except Exception as e:
        print(f"KRITINE KLAIDA: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
