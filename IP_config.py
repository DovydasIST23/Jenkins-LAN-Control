import os
import time
from gns3fy import Gns3Connector, Project

GNS3_URL = os.environ.get("GNS3_SERVER_URL", "http://192.168.56.102:80")
PROJECT_NAME = "a"
# -------------------------
# MAIN
# -------------------------
def main():
    try:
        print(f"[INFO] Connecting to GNS3 API {GNS3_URL}")
        connector = Gns3Connector(url=GNS3_URL)
        project = Project(name=PROJECT_NAME, connector=connector)
        project.get()
        project.get_nodes()

        print(f"[OK] Project loaded: {project.name}")

        if not start_nodes(project):
            print("[WARN] Some nodes are not started, but proceeding...")

        # Trumpas palaukimas stabilumui
        time.sleep(2)

        configure_alpine(project)
        configure_ovs_switches(project)

        print("\n[SUCCESS] NETWORK FULLY CONFIGURED VIA API")

    except Exception as e:
        print(f"[ERROR] {e}")

# -------------------------
# IP PLAN
# -------------------------
def generate_ip_config():
    config = {}
    # AlpineLinux-2 iki AlpineLinux-7
    for i in range(2, 8):
        config[f"AlpineLinux-{i}"] = (f"10.0.0.{9+i}", "10.0.0.1")

    config["AlpineLinux-1"] = ("11.0.0.1", "11.0.0.1")
    config["AlpineLinux-8"] = ("10.1.0.10", "10.1.0.1")
    config["AlpineLinux-9"] = ("10.1.0.11", "10.1.0.1")
    config["AlpineLinux-10"] = ("10.2.0.10", "10.2.0.1")
    return config

# -------------------------
# Configure Alpine via API
# -------------------------
def configure_alpine(project):
    print("\n[INFO] Configuring Alpine containers via API...")
    config = generate_ip_config()

    for node in project.nodes:
        if node.node_type == "docker" and node.name in config:
            ip, gw = config[node.name]
            
            # Komandos vykdomos tiesiai konteinerio viduje per API
            cmd = f"sh -c 'ip addr flush dev eth0; ip addr add {ip}/24 dev eth0; ip link set eth0 up; ip route add default via {gw}'"
            
            print(f"[CFG] {node.name} -> {ip}")
            try:
                node.run_executable(cmd)
            except Exception as e:
                print(f"[ERR] Failed to config {node.name}: {e}")

# -------------------------
# Configure OVS switches via API
# -------------------------
def configure_ovs_switches(project):
    print("\n[INFO] Configuring OVS switches via API...")
    # Pridėjau ir Admin-IT, nes tavo log'e matėsi toks pavadinimas
    switch_names = ["Main1", "Support", "Admin", "Admin-IT", "Main"]

    for node in project.nodes:
        if node.name in switch_names:
            # OVS konfigūracijos skriptas
            cmd = "sh -c 'ovs-vsctl --if-exists del-br br0; ovs-vsctl add-br br0; for iface in $(ls /sys/class/net | grep eth); do ovs-vsctl --may-exist add-port br0 $iface; ip link set $iface up; done; ip link set br0 up'"
            
            print(f"[CFG] OVS Switch {node.name}")
            try:
                node.run_executable(cmd)
            except Exception as e:
                print(f"[ERR] Failed to config switch {node.name}: {e}")

# -------------------------
# Start nodes
# -------------------------
def start_nodes(project):
    print("\n[INFO] Checking/Starting nodes...")
    for node in project.nodes:
        if node.status != "started":
            print(f"Starting {node.name}")
            node.start()

    for _ in range(30):
        project.get_nodes()
        if all(n.status == "started" for n in project.nodes):
            print("[OK] All nodes started")
            return True
        time.sleep(1)
    return False


if __name__ == "__main__":
    main()
