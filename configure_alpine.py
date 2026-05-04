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
    """
    Konfigūruoja OVS mazgus: Main1, Support, Admin.
    Išvalo senus tiltus, kurie blokuoja eth prievadus.
    """
    print(f"\n[OVS] Konfiguruojamas {node_name} (Prievadas: {port})...")
    try:
        with ConnectHandler(**get_params(port)) as tn:
            tn.write_channel("\n")
            time.sleep(1)
            
            # 1. Agresyvus senų tiltų valymas, kad atlaisvintume eth0, eth3 ir t.t.
            cleanup_cmds = [
                "ovs-vsctl --if-exists del-br br-lan",
                "ovs-vsctl --if-exists del-br br0",
                "ovs-vsctl --if-exists del-br br1",
                "ovs-vsctl --if-exists del-br br2",
                "ovs-vsctl --if-exists del-br br3",
                "ovs-vsctl --if-exists del-br br-final"
            ]
            for c in cleanup_cmds:
                tn.send_command(c, expect_string=r'[#$]')

            # 2. Naujo tilto kūrimas
            setup_cmds = [
                "ovs-vsctl add-br br-final",
                "ovs-vsctl set-fail-mode br-final standalone",
                "ovs-vsctl set bridge br-final stp_enable=false"
            ]
            
            # 3. Portų (eth0-eth3) prijungimas
            for i in range(4):
                setup_cmds.append(f"ovs-vsctl add-port br-final eth{i}")
                setup_cmds.append(f"ip link set eth{i} up")
            
            setup_cmds.append("ip link set br-final up")
            setup_cmds.append("ovs-ofctl add-flow br-final action=normal")
            
            # 4. Valdymo IP priskyrimas pačiam jungikliui
            if node_name == "Admin":
                setup_cmds.append("ip addr add 11.0.0.100/24 dev br-final")
            elif node_name == "Main1":
                setup_cmds.append("ip addr add 10.0.0.100/24 dev br-final")
            elif node_name == "Support":
                setup_cmds.append("ip addr add 10.1.0.100/24 dev br-final")

            for cmd in setup_cmds:
                tn.send_command(cmd, expect_string=r'[#$]')
                print(f"    -> {cmd}")
        return True
    except Exception as e:
        print(f"    -> [!] OVS Klaida mazge {node_name}: {e}")
        return False

def configure_alpine(name, port, ip, gw):
    """Priskiria IP adresą Alpine Linux mazgui, kai OVS jau paruoštas."""
    print(f"\n[ALPINE] {name} -> Nustatomas IP: {ip}")
    try:
        with ConnectHandler(**get_params(port)) as tn:
            tn.write_channel("\n")
            time.sleep(2) # Laukiam, kol sąsaja eth0 taps prieinama
            
            cmds = [
                "ip link set eth0 up || true",
                "ip addr flush dev eth0",
                f"ip addr add {ip}/24 dev eth0",
                f"ip route add default via {gw} || true"
            ]
            for cmd in cmds:
                output = tn.send_command(cmd, expect_string=r'[#$]')
                if "can't find device" in output:
                    print(f"    -> [!] KLAIDA: {name} vis dar nemato eth0!")
                else:
                    print(f"    -> {cmd}")
        return True
    except Exception as e:
        print(f"    -> [!] Alpine Klaida mazge {name}: {e}")
        return False

def main():
    sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
    try:
        server = Gns3Connector(url=f"http://{GNS3_IP}:80")
        project = Project(name=PROJECT_NAME, connector=server)
        project.get()
        project.get_nodes()

        # SVARBU: Pirmiausia sukonfigūruojame OVS (Admin, Main1, Support)
        ovs_list = ["Admin", "Main1", "Support"]
        for node in project.nodes:
            if node.name in ovs_list and node.status == "started":
                configure_ovs_node(node.name, node.console)

        # Antras etapas: IP priskyrimas Alpine mazgams
        for node in project.nodes:
            if node.name in IP_PLAN and node.status == "started":
                ip, gw = IP_PLAN[node.name]
                configure_alpine(node.name, node.console, ip, gw)

        print("\n" + "="*45)
        print("✅ KONFIGŪRACIJA BAIGTA SĖKMINGAI")
        print("Pabandykite ping iš Admin: ping 11.0.0.1")
        print("Pabandykite ping iš Main1: ping 10.0.0.12")
        print("="*45)
        
    except Exception as e:
        print(f"\n[CRITICAL] Klaida: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
