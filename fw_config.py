import sys
import time
from gns3fy import Gns3Connector, Project
from netmiko import ConnectHandler

GNS3_IP = "192.168.56.102"
PROJECT_NAME = "a"

def get_params(port):
    return {
        'device_type': 'generic_telnet',
        'host': GNS3_IP,
        'port': port,
        'timeout': 15,
    }

def configure_firewall(node_name, port):
    """Nustato OpenFlow taisykles srauto kontrolei."""
    print(f"\n[FIREWALL] Konfigūruojamas {node_name} saugumas...")
    
    # IP adresų priskyrimas identifikavimui taisyklėse
    ADMIN_NET = "11.0.0.0/24"
    MAIN_NET = "10.0.0.0/24"
    SUPPORT_NET = "10.1.0.0/24"

    cmds = []
    # 1. Išvalome senas taisykles
    cmds.append("ovs-ofctl del-flows br-final")
    
    # 2. Standartinis leidimas ARP srautui (būtinas, kad veiktų tinklas)
    cmds.append("ovs-ofctl add-flow br-final priority=100,arp,action=normal")

    if node_name == "Admin":
        # Admin leidžia viską į Main ir Support (ir atgal)
        cmds.append(f"ovs-ofctl add-flow br-final priority=50,ip,nw_dst={MAIN_NET},action=normal")
        cmds.append(f"ovs-ofctl add-flow br-final priority=50,ip,nw_dst={SUPPORT_NET},action=normal")
        cmds.append("ovs-ofctl add-flow br-final priority=10,ip,action=drop") # Viskas kita - drop

    elif node_name == "Main1":
        # Main leidžia atsakymus tik į Admin. Į Support - blokuoja.
        cmds.append(f"ovs-ofctl add-flow br-final priority=50,ip,nw_dst={ADMIN_NET},action=normal")
        cmds.append(f"ovs-ofctl add-flow br-final priority=40,ip,nw_dst={SUPPORT_NET},action=drop")
        cmds.append("ovs-ofctl add-flow br-final priority=10,ip,action=drop")

    elif node_name == "Support":
        # Support leidžia į Main ir Admin.
        cmds.append(f"ovs-ofctl add-flow br-final priority=50,ip,nw_dst={MAIN_NET},action=normal")
        cmds.append(f"ovs-ofctl add-flow br-final priority=50,ip,nw_dst={ADMIN_NET},action=normal")
        cmds.append("ovs-ofctl add-flow br-final priority=10,ip,action=drop")

    try:
        with ConnectHandler(**get_params(port)) as tn:
            tn.write_channel("\n")
            for cmd in cmds:
                tn.send_command(cmd, expect_string=r'[#$]')
        print(f"OK: {node_name} firewall sukonfigūruotas.")
    except Exception as e:
        print(f"KLAIDA {node_name}: {e}")

def main():
    try:
        server = Gns3Connector(url=f"http://{GNS3_IP}:80")
        project = Project(name=PROJECT_NAME, connector=server)
        project.get()
        project.get_nodes()

        ovs_names = ["Main1", "Support", "Admin"]
        for node in project.nodes:
            if node.name in ovs_names and node.status == "started":
                configure_firewall(node.name, node.console)

        print("\nSaugumo konfigūracija baigta.")
    except Exception as e:
        print(f"KRITINĖ KLAIDA: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
