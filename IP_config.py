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
# Get container list
# -------------------------
def get_all_containers(ssh):
    stdin, stdout, stderr = ssh.exec_command(
        "docker ps --format '{{.Names}}'"
    )
    return stdout.read().decode().strip().splitlines()


# -------------------------
# Find container by node name
# -------------------------
def find_container(containers, node_name):
    for c in containers:
        if node_name.lower() in c.lower():
            return c
    return None


# -------------------------
# Wait for containers (fix for "stuck installing")
# -------------------------
def wait_for_containers(ssh, timeout=60):
    print("\n[INFO] Waiting for containers to be ready...")

    for i in range(timeout):
        containers = get_all_containers(ssh)

        if containers:
            print(f"[OK] {len(containers)} containers detected")
            return containers

        time.sleep(1)

    print("[ERROR] No containers found")
    return []


# -------------------------
# Configure Alpine
# -------------------------
def configure_alpine(project, ssh, containers):
    print("\n[INFO] Configuring Alpine containers...")

    config = generate_ip_config()

    for node in project.nodes:
        if node.node_type != "docker":
            continue

        if node.name not in config:
            continue

        container = find_container(containers, node.name)
        if not container:
            print(f"[WARN] No container for {node.name}")
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
# Configure OVS switches
# -------------------------
def configure_ovs_switches(project, ssh, containers):
    print("\n[INFO] Configuring Open vSwitch nodes...")

    switch_names = ["Main1", "Support", "Admin"]

    for node in project.nodes:
        if node.name not in switch_names:
            continue

        container = find_container(containers, node.name)
        if not container:
            print(f"[WARN] No container for {node.name}")
            continue

        cmd = f"""
docker exec {container} sh -c "

echo 'Starting OVS services manually...'

# Create DB if missing
mkdir -p /var/run/openvswitch
mkdir -p /etc/openvswitch

ovsdb-tool create /etc/openvswitch/conf.db \
    /usr/share/openvswitch/vswitch.ovsschema 2>/dev/null || true

# Start OVS DB
ovsdb-server --remote=punix:/var/run/openvswitch/db.sock \
             --remote=db:Open_vSwitch,Open_vSwitch,manager_options \
             --pidfile --detach || true

# Init DB
ovs-vsctl --no-wait init

# Start vswitch daemon
ovs-vswitchd --pidfile --detach || true

echo 'Resetting bridge...'
ovs-vsctl --if-exists del-br br0
ovs-vsctl add-br br0

echo 'Adding interfaces...'
for iface in $(ls /sys/class/net | grep eth); do
    ovs-vsctl add-port br0 $iface
    ip link set $iface up
done

ip link set br0 up

echo 'OVS READY'
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

    # wait until all started
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

        time.sleep(5)

        ssh = ssh_connect()

        containers = wait_for_containers(ssh)
        if not containers:
            return

        configure_alpine(project, ssh, containers)
        configure_ovs_switches(project, ssh, containers)

        ssh.close()

        print("\n[SUCCESS] NETWORK FULLY CONFIGURED")

    except Exception as e:
        print(f"[ERROR] {e}")


if __name__ == "__main__":
    main()
