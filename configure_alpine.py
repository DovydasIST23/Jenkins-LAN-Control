import sys
import time
from gns3fy import Gns3Connector, Project
from netmiko import ConnectHandler

# --- KONFIGŪRACIJA ---
GNS3_IP = "192.168.56.102"
PROJECT_NAME = "a"

# IP Planas (ping testui: Alpine2 -> 10.0.0.11, Alpine3 -> 10.0.0.12)
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

def configure_ovs_as_switch(name, port):
    """
    Sukonfigūruoja OVS Main1 kaip paprastą switch'ą.
    Sujungia visas fizines sąsajas į vieną tiltą 'br-lan'.
    """
    print(f"\n[OVS CONFIG] Konfigūruojamas {name} srauto praleidimui...")
    try:
        with ConnectHandler(**get_params(port)) as tn:
            tn.write_channel("\n")
            time.sleep(1)
            
            # 1. Sukuriame naują švarų tiltą (jei jo nėra)
            # 2. Pridedame visas fizines sąsajas (eth0-eth7) į tą tiltą
            # 3. Pakeliame tiltą ir sąsajas
            
            ovs_cmds = [
                "ovs-vsctl --if-exists del-br br-lan", # Išvalome seną, jei buvo
                "ovs-vsctl add-br br-lan",             # Sukuriame naują tiltą
            ]
            
            # Pridedame visas sąsajas prie tilto
            for i in range(8):
                ovs_cmds.append(f"ovs-vsctl add-port br-lan eth{i}")
                ovs_cmds.append(f"ip link set eth{i} up")
            
            ovs_cmds.append("ip link set br-lan up")
            
            for cmd in ovs_cmds:
                tn.send_command(cmd, expect_string=r'[#$]')
                
            print(f"    -> [SUCCESS] OVS sukonfigūruotas. eth0-7 sujungti per br-lan.")
        return True
    except Exception as e:
        print(f"    -> [!] OVS Klaida: {e}")
        return False

def configure_alpine(name, port, ip, gw):
    """Standartinė Alpine IP konfigūracija."""
    print(f"\n[ALPINE] {name} IP: {ip}")
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
                configure_ovs_as_switch(node.name, node.console)
            elif node.name in IP_PLAN:
                configure_alpine(node.name, node.console, *IP_PLAN[node.name])

        print("\n[FINISH] Konfigūracija baigta. Galite bandyti: AlpineLinux-2 ping 10.0.0.12")
        
    except Exception as e:
        print(f"Kritinė klaida: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
