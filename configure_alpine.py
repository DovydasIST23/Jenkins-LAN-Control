import sys
import time
from gns3fy import Gns3Connector, Project
from netmiko import ConnectHandler

# --- KONFIGŪRACIJA ---
GNS3_IP = "192.168.56.102"
PROJECT_NAME = "a"

# Pilnas IP Planas visiems tinklo mazgams
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
    """Konfigūruoja OVS mazgus (Main1, Support) kaip L2 switch'us."""
    print(f"\n[OVS] Pilnas perkonfigūravimas: {node_name}...")
    try:
        with ConnectHandler(**get_params(port)) as tn:
            tn.write_channel("\n")
            time.sleep(1)
            
            # 1. Išvalome senus tiltus ir sukuriame naują br-final
            commands = [
                "ovs-vsctl --if-exists del-br br-final",
                "ovs-vsctl --if-exists del-br br-lan",
                "ovs-vsctl add-br br-final",
                "ovs-vsctl set-fail-mode br-final standalone",
                "ovs-vsctl set bridge br-final stp_enable=false",
            ]
            
            # 2. Prijungiame visas galimas sąsajas (eth0-eth3)
            for i in range(4):
                commands.append(f"ovs-vsctl add-port br-final eth{i}")
                commands.append(f"ip link set eth{i} up")
            
            # 3. Aktyvuojame tiltą
            commands.append("ip link set br-final up")
            
            # 4. Priverstinai nurodome leisti standartinį srautą (L2 switching)
            commands.append("ovs-ofctl add-flow br-final action=normal")
            
            for cmd in commands:
                tn.send_command(cmd, expect_string=r'[#$]')
                print(f"    -> {cmd}")
        return True
    except Exception as e:
        print(f"    -> OVS Klaida mazge {node_name}: {e}")
        return False

def configure_alpine(name, port, ip, gw):
    """Priverstinai priskiria IP adresą ir vartus Alpine mazgui."""
    print(f"\n[ALPINE] {name} konfigūracija -> IP: {ip}, GW: {gw}")
    try:
        with ConnectHandler(**get_params(port)) as tn:
            tn.write_channel("\n")
            time.sleep(1)
            cmds = [
                "ip addr flush dev eth0",
                f"ip addr add {ip}/24 dev eth0",
                "ip link set eth0 up",
                f"ip route add default via {gw}" # Maršrutas į MikroTik vartus
            ]
            for cmd in cmds:
                tn.send_command(cmd, expect_string=r'[#$]')
                print(f"    -> {cmd}")
        return True
    except Exception as e:
        print(f"    -> Alpine Klaida mazge {name}: {e}")
        return False

def main():
    # Užtikriname teisingą kodavimą Jenkins aplinkai
    sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
    
    try:
        server = Gns3Connector(url=f"http://{GNS3_IP}:80")
        project = Project(name=PROJECT_NAME, connector=server)
        project.get()
        project.get_nodes()

        # Konfigūruojame visus mazgus iš eilės
        for node in project.nodes:
            if node.status != "started":
                print(f"[SKIP] Mazgas {node.name} neįjungtas.")
                continue
                
            if node.name in ["Main1", "Support"]:
                configure_ovs_node(node.name, node.console)
            elif node.name in IP_PLAN:
                ip, gw = IP_PLAN[node.name]
                configure_alpine(node.name, node.console, ip, gw)

        print("\n" + "="*40)
        print("✅ TINKLO KONFIGŪRACIJA BAIGTA")
        print("Srautas tarp AlpineLinux-2 (10.0.0.11) ir AlpineLinux-3 (10.0.0.12) turi veikti.")
        print("="*40)
        
    except Exception as e:
        print(f"\n[CRITICAL] Klaida: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
