import sys
import time
from gns3fy import Gns3Connector, Project
from netmiko import ConnectHandler

GNS3_IP = "192.168.56.102"
PROJECT_NAME = "a"

# Užtikriname, kad Admin pusė yra 11.0.0.0/24 potinklyje
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

def configure_ovs(node_name, port):
    print(f"\n[OVS] {node_name} konfigūravimas...")
    try:
        with ConnectHandler(**get_params(port)) as tn:
            # Išvalome senas konfigūracijas
            cmds = [
                "ovs-vsctl --if-exists del-br br-final",
                "ovs-vsctl add-br br-final",
                "ovs-vsctl set-fail-mode br-final standalone"
            ]
            
            # Prijungiame visus portus ir juos įjungiame
            for i in range(8): # Padidinta iki 8 portų Admin/Main mazgams
                cmds.append(f"ovs-vsctl add-port br-final eth{i} -- set Interface eth{i} up || true")
                cmds.append(f"ip link set eth{i} up || true")
            
            cmds.append("ip link set br-final up")
            
            # IP priskyrimas pačiam OVS (Admin mazgui svarbu 11.0.0.100)
            if node_name == "Admin":
                cmds.append("ip addr add 11.0.0.100/24 dev br-final")
            elif node_name == "Main1":
                cmds.append("ip addr add 10.0.0.100/24 dev br-final")
                
            for cmd in cmds:
                tn.send_command(cmd, expect_string=r'[#$]')
    except Exception as e:
        print(f"Klaida {node_name}: {e}")

def configure_alpine(name, port, ip, gw):
    print(f"[ALPINE] {name} -> {ip}")
    try:
        with ConnectHandler(**get_params(port)) as tn:
            # Priverstinis eth0 paieškojimas
            cmds = [
                "ip link set eth0 up",
                "ip addr flush dev eth0",
                f"ip addr add {ip}/24 dev eth0",
                f"ip route add default via {gw} || true"
            ]
            for cmd in cmds:
                tn.send_command(cmd, expect_string=r'[#$]')
    except Exception as e:
        print(f"Klaida {name}: {e}")

# ... (main dalis lieka tokia pati, kaip tavo paskutiniame sėkmingame paleidime)
