import os
import time
import paramiko
from gns3fy import Gns3Connector, Project

# -------------------------
# CONFIG
# -------------------------
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

    for i in range(1, 8):
        config[f"AlpineLinux-{i}"] = (f"10.0.0.{9+i}", "10.0.0.1")

    config["AlpineLinux-8"] = ("10.1.0.10", "10.1.0.1")
    config["AlpineLinux-9"] = ("10.1.0.11", "10.1.0.1")
    config["AlpineLinux-10"] = ("10.2.0.10", "10.2.0.1")

    return config


# -------------------------
# SSH
# -------------------------
def ssh_connect():
    print("[INFO] Connecting to GNS3 VM via SSH...")
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
# Docker container lookup
# -------------------------
def get_container_name(ssh, node_id):
    cmd = f'docker ps --filter "label=com.gns3.node.id={node_id}" --format "{{{{.Names}}}}"'
    stdin, stdout, stderr = ssh.exec_command(cmd)
    return stdout.read().decode().strip()


# -------------------------
# Configure Alpine
# -------------------------
def configure_alpine(project, ssh):
    print("\n[INFO] Configuring Alpine containers...")

    config = generate_ip_config()

    for node in project.nodes:
        if node.node_type != "docker":
            continue

        if node.name not in config:
            print(f"[SKIP] {node.name}")
            continue

        ip, gw = config[node.name]

        container_name = get_container_name(ssh, node.node_id)

        if not container_name:
            print(f"[ERROR] No container found for {node.name}")
            continue

        cmd = f"""
docker exec {container_name} sh -c "
ip addr add {ip}/24 dev eth0;
ip link set eth0 up;
ip route add default via {gw};
"
"""

        print(f"[CFG] {node.name} ({container_name}) -> {ip}")
        ssh_exec(ssh, cmd)


# -------------------------
# Configure MikroTik
# -------------------------
def configure_mikrotik(ssh):
    print("\n[INFO] Configuring MikroTik...")

    stdin, stdout, stderr = ssh.exec_command("screen -ls")
    screens = stdout.read().decode()

    print("[DEBUG] Available screens:")
    print(screens)

    session_name = None

    for line in screens.splitlines():
        if "mikrotik" in line.lower():
            session_name = line.strip().split(".")[-1]
            break

    if not session_name:
        print("[ERROR] MikroTik screen not found")
        return

    print(f"[OK] Found MikroTik session: {session_name}")

    commands = [
        "/ip address add address=10.0.0.1/24 interface=ether1",
        "/ip address add address=10.1.0.1/24 interface=ether2",
        "/ip address add address=10.2.0.1/24 interface=ether3",
    ]

    for cmd in commands:
        send_cmd = f'screen -S {session_name} -X stuff "{cmd}\\n"'
        ssh_exec(ssh, send_cmd)


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

        # Start nodes
        if not start_nodes(project):
            return

        # Wait for containers to fully boot
        time.sleep(10)

        # SSH into GNS3 VM
        ssh = ssh_connect()

        # Configure Alpine containers
        configure_alpine(project, ssh)

        # Wait for MikroTik to boot properly
        time.sleep(10)

        # Configure MikroTik
        configure_mikrotik(ssh)

        ssh.close()

        print("\n[SUCCESS] NETWORK FULLY CONFIGURED")

    except Exception as e:
        print(f"[ERROR] {e}")


if __name__ == "__main__":
    main()
