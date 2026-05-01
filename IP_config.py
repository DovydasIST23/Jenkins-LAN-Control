import os
import time
import paramiko
from gns3fy import Gns3Connector, Project

GNS3_URL = os.environ.get("GNS3_SERVER_URL", "http://192.168.56.102:80")
PROJECT_NAME = "a"

GNS3_VM_HOST = "192.168.56.102"
GNS3_VM_USER = "gns3"
GNS3_VM_PASS = "gns3"


# -------------------------
# IP PLAN
# -------------------------
def generate_ip_config():
    config = {}

    for i in range(2, 8):
        config[f"AlpineLinux-{i}"] = (f"10.0.0.{9+i}", "10.0.0.1")

    config["AlpineLinux-1"] = ("11.0.0.1", "11.0.0.1")
    config["AlpineLinux-8"] = ("10.1.0.10", "10.1.0.1")
    config["AlpineLinux-9"] = ("10.1.0.11", "10.1.0.1")
    config["AlpineLinux-10"] = ("10.2.0.10", "10.2.0.1")

    return config


# -------------------------
# SSH
# -------------------------
def ssh_connect():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(GNS3_VM_HOST, username=GNS3_VM_USER, password=GNS3_VM_PASS)
    return ssh


def ssh_exec(ssh, cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode()
    err = stderr.read().decode()

    if out:
        print(out.strip())
    if err:
        print("[ERR]", err.strip())


# -------------------------
# Get container mapping (NAME -> container)
# -------------------------
def get_container_map(ssh):
    cmd = "docker ps --format '{{.Names}}'"
    stdin, stdout, stderr = ssh.exec_command(cmd)
    names = stdout.read().decode().strip().splitlines()

    mapping = {}
    for c in names:
        # GNS3 container names usually contain node name
        for node_name in c.split("-"):
            mapping[c] = c

    return names


# -------------------------
# Find container by node name
# -------------------------
def find_container(containers, node_name):
    for c in containers:
        if node_name.lower() in c.lower():
            return c
    return None


# -------------------------
# Configure Alpine
# -------------------------
def configure_alpine(project, ssh):
    print("\n[INFO] Configuring Alpine containers...")

    config = generate_ip_config()
    containers = get_container_map(ssh)

    for node in project.nodes:
        if node.node_type != "docker":
            continue

        if node.name not in config:
            continue

        container = find_container(containers, node.name)
        if not container:
            print(f"[ERROR] Container not found for {node.name}")
            continue

        ip, gw = config[node.name]

        cmd = f"""
docker exec {container} sh -c "
ip addr flush dev eth0;
ip addr add {ip}/24 dev eth0;
ip link set eth0 up;
ip route add default via {gw};
"
"""
        print(f"[CFG] {node.name} -> {ip}")
        ssh_exec(ssh, cmd)


# -------------------------
# Configure OVS Switches
# -------------------------
def configure_ovs_switches(project, ssh):
    print("\n[INFO] Configuring OVS switches...")

    switch_names = ["Main1", "Support", "Admin"]
    containers = get_container_map(ssh)

    for node in project.nodes:
        if node.name not in switch_names:
            continue

        container = find_container(containers, node.name)
        if not container:
            print(f"[ERROR] Container not found for {node.name}")
            continue

        cmd = f"""
docker exec {container} sh -c "
# Clean old config
ovs-vsctl --if-exists del-br br0

# Create bridge
ovs-vsctl add-br br0

# Add all eth interfaces
for iface in $(ls /sys/class/net | grep eth); do
    ovs-vsctl add-port br0 $iface
    ip link set $iface up
done

ip link set br0 up
"
"""
        print(f"[CFG] OVS Switch {node.name}")
        ssh_exec(ssh, cmd)


# -------------------------
# Start nodes
# -------------------------
def start_nodes(project):
    print("\n[INFO] Starting nodes...")

    for node in project.nodes:
        if node.status != "started":
            print(f"Starting {node.name}")
            node.start()

    for _ in range(60):
        project.get_nodes()
        if all(n.status == "started" for n in project.nodes):
            print("[OK] All nodes started")
            return True
        time.sleep(1)

    print("[ERROR] Nodes failed to start")
    return False


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
            return

        time.sleep(10)

        ssh = ssh_connect()

        configure_alpine(project, ssh)
        configure_ovs_switches(project, ssh)

        ssh.close()

        print("\n[SUCCESS] NETWORK FULLY CONFIGURED")

    except Exception as e:
        print(f"[ERROR] {e}")


if __name__ == "__main__":
    main()
