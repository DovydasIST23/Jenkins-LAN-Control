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
# SSH CONNECT
# -------------------------
def ssh_connect():
    print("[INFO] Connecting via SSH to GNS3 VM...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(GNS3_VM_HOST, username=GNS3_VM_USER, password=GNS3_VM_PASS)
    return ssh


# -------------------------
# EXEC SSH COMMAND
# -------------------------
def ssh_exec(ssh, cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    output = stdout.read().decode()
    error = stderr.read().decode()

    if output:
        print(output.strip())
    if error:
        print("[ERR]", error.strip())


# -------------------------
# Configure Alpine via Docker
# -------------------------
def configure_alpine_ssh(project, ssh):
    print("\n[INFO] Configuring Alpine containers via SSH...")

    config = generate_ip_config()

    for node in project.nodes:
        if node.node_type != "docker":
            continue

        if node.name not in config:
            continue

        ip, gw = config[node.name]

        # Container name in GNS3 = node name (usually)
        cmd = f"""
docker exec {node.name} sh -c "
ip addr add {ip}/24 dev eth0;
ip link set eth0 up;
ip route add default via {gw};
"
"""

        print(f"[CFG] {node.name} -> {ip}")
        ssh_exec(ssh, cmd)


# -------------------------
# Configure MikroTik via console
# -------------------------
def configure_mikrotik_ssh(ssh):
    print("\n[INFO] Configuring MikroTik via SSH console...")

    # Find MikroTik screen session
    cmd_find = "screen -ls | grep mikrotik || true"
    ssh_exec(ssh, cmd_find)

    # Send commands (basic example)
    mikrotik_cmds = [
        "/ip address add address=10.0.0.1/24 interface=ether1",
        "/ip address add address=10.1.0.1/24 interface=ether2",
        "/ip address add address=10.2.0.1/24 interface=ether3",
    ]

    for cmd in mikrotik_cmds:
        send_cmd = f'screen -S mikrotik-1 -X stuff "{cmd}\\n"'
        ssh_exec(ssh, send_cmd)


# -------------------------
# Start nodes (API)
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

        time.sleep(5)  # allow containers to boot

        ssh = ssh_connect()

        configure_alpine_ssh(project, ssh)
        configure_mikrotik_ssh(ssh)

        ssh.close()

        print("\n[SUCCESS] FULL NETWORK CONFIGURED")

    except Exception as e:
        print(f"[ERROR] {e}")


if __name__ == "__main__":
    main()
