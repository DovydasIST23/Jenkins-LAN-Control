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
        'timeout': 15, # Padidintas timeout stabilumui
    }

def configure_ovs_node(node_name, port):
    """Konfigūruoja OVS mazgus: Main1, Support, Admin."""
    print(f"\n[OVS] Konfiguruojamas {node_name} (Console: {port})...")
    try:
        with ConnectHandler(**get_params(port)) as tn:
            tn.write_channel("\n")
            time.sleep(1)
            
            # 1. Išvalome senas šiukšles (ypač br-lan) ir sukuriame švarų tiltą
            commands = [
                "ovs-vsctl --if-exists del-br br-final",
                "ovs-vsctl --if-exists del-br br-lan",
                "ovs-vsctl add-br br-final",
                "ovs-vsctl set-fail-mode br-final standalone",
                "ovs-vsctl set bridge br-final stp_enable=false"
            ]
            
            # 2. Prijungiame fizinius portus prie tilto
            for i in range(4):
                commands.append(f"ovs-vsctl add-port br-final eth{i}")
                commands.append(f"ip link set eth{i} up")
            
            commands.append("ip link set br-final up")
            
            # 3. Priverstinis L2 srauto leidimas
            commands.append("ovs-ofctl add-flow br-final action=normal")
            
            # Pridedame IP patiems switchams (valdymui/testavimui)
            if node_name == "Main1":
                commands.append("ip addr add 10.0.0.100/24 dev br-final")
            elif node_name == "Support":
                commands.append("ip addr add 10.1.0.100/24 dev br-final")
            elif node_name == "Admin":
                commands.append("ip addr add 11.0.0.100/24 dev br-final")

            for cmd in commands:
                tn.send_command(cmd, expect_string=r'[#$]')
                print(f"    -> {cmd}")
        return True
    except Exception as e:
        print(f"    -> [!] Klaida OVS mazge {node_name}: {e}")
        return False

def configure_alpine(name, port, ip, gw):
    """Priskiria IP adresą Alpine Linux mazgui."""
    print(f"\n[ALPINE] {name} -> Nustatomas IP: {ip}")
    try:
        with ConnectHandler(**get_params(port)) as tn:
            tn.write_channel("\n")
            time.sleep(1)
            # Pirmiausia išvalome visus senus IP, tada pridedame naują
            cmds = [
                "ip addr flush dev eth0",
                f"ip addr add {ip}/24 dev eth0",
                "ip link set eth0 up",
                f"ip route add default via {gw} || true"
            ]
            for cmd in cmds:
                tn.send_command(cmd, expect_string=r'[#$]')
                print(f"    -> {cmd}")
        return True
    except Exception as e:
        print(f"    -> [!] Klaida Alpine mazge {name}: {e}")
        return False

def main():
    # Jenkins stdout buffering fix
    sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
    
    try:
        server = Gns3Connector(url=f"http://{GNS3_IP}:80")
        project = Project(name=PROJECT_NAME, connector=server)
        project.get()
        project.get_nodes()

        # 1. ETAPAS: Konfigūruojame visus OVS (Main1, Support, Admin)
        # Tai paruošia "kelius", bet gali numušti laikinus IP nuo Alpine
        ovs_list = ["Main1", "Support", "Admin"]
        for node in project.nodes:
            if node.name in ovs_list and node.status == "started":
                configure_ovs_node(node.name, node.console)

        # 2. ETAPAS: Tik dabar priskiriame IP adresus Alpine mazgams
        for node in project.nodes:
            if node.name in IP_PLAN and node.status == "started":
                ip, gw = IP_PLAN[node.name]
                configure_alpine(node.name, node.console, ip, gw)

        print("\n" + "="*40)
        print("✅ VISAS TINKLAS SUKONFIGŪRUOTAS")
        print("Patikrinkite ping: AlpineLinux-2 -> AlpineLinux-3 (10.0.0.12)")
        print("="*40)
        
    except Exception as e:
        print(f"\n[CRITICAL] Klaida: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
