import os
import sys
import time
from netmiko import ConnectHandler
from gns3fy import Gns3Connector, Project

# Nustatymai
GNS3_IP = "192.168.56.102"
GNS3_URL = f"http://{GNS3_IP}:80"
PROJECT_NAME = "a"
GNS3_VM_USER = "gns3"
GNS3_VM_PASS = "gns3"

IP_PLAN = {
    "AlpineLinux-1": ("11.0.0.2",  "11.0.0.1"),
    "AlpineLinux-2": ("10.0.0.11", "10.0.0.1"),
    "AlpineLinux-3": ("10.0.0.12", "10.0.0.1"),
    "AlpineLinux-8": ("10.1.0.10", "10.1.0.1"),
    "AlpineLinux-9": ("10.1.0.11", "10.1.0.1"),
    "AlpineLinux-10": ("10.2.0.10", "10.2.0.1")
}

def configure_docker_nodes(project):
    print("\n[DEBUG] === Docker konfigūracija ===")
    vm_params = {
        'device_type': 'linux',
        'host': GNS3_IP,
        'username': GNS3_VM_USER,
        'password': GNS3_VM_PASS,
        # Pridėta: laukiame bet kokio prompt'o, kad išvengtume "Pattern not detected"
        'expect_string': r'[\$\#\>]', 
    }
    try:
        ssh_conn = ConnectHandler(**vm_params)
        for node in project.nodes:
            if node.node_type == "docker" and node.name in IP_PLAN:
                ip, gw = IP_PLAN[node.name]
                cmd = f'docker ps --filter "label=com.gns3.node.id={node.node_id}" --format "{{{{.ID}}}}"'
                container_id = ssh_conn.send_command(cmd).strip()
                if container_id:
                    print(f"  -> {node.name} ({ip})")
                    ssh_conn.send_command(f'docker exec {container_id} ip addr flush dev eth0')
                    ssh_conn.send_command(f'docker exec {container_id} ip addr add {ip}/24 dev eth0')
                    ssh_conn.send_command(f'docker exec {container_id} ip link set eth0 up')
                    ssh_conn.send_command(f'docker exec {container_id} ip route add default via {gw}')
        ssh_conn.disconnect()
    except Exception as e:
        print(f"[CRITICAL] Docker klaida: {e}")

def configure_mikrotik(project):
    print("\n[DEBUG] === MikroTik konfigūracija ===")
    mt_node = next((n for n in project.nodes if "mikrotik" in n.name.lower()), None)
    if not mt_node: return

    # PAKEISTA: Naudojamas 'generic_telnet', nes Netmiko RouterOS per Telnet yra problematiškas
    mt_params = {
        'device_type': 'generic_telnet',
        'host': GNS3_IP,
        'port': mt_node.console,
        'username': 'admin',
        'password': '',
    }
    try:
        net_conn = ConnectHandler(**mt_params)
        # Siunčiame komandas tiesiai į terminalą
        commands = [
            "/ip address add address=11.0.0.1/24 interface=ether1\r",
            "/ip address add address=10.0.0.1/24 interface=ether2\r",
            "/ip address add address=10.1.0.1/24 interface=ether3\r",
            "/ip address add address=10.2.0.1/24 interface=ether4\r"
        ]
        for cmd in commands:
            net_conn.write_channel(cmd)
            time.sleep(1)
        print("[SUCCESS] MikroTik komandos nusiųstos.")
        net_conn.disconnect()
    except Exception as e:
        print(f"[CRITICAL] MikroTik klaida: {e}")

def main():
    connector = Gns3Connector(url=GNS3_URL)
    project = Project(name=PROJECT_NAME, connector=connector)
    project.get()
    project.get_nodes()
    configure_docker_nodes(project)
    configure_mikrotik(project)

if __name__ == "__main__":
    main()
