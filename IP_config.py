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
# Get ALL container names
# -------------------------
def get_all_containers(ssh):
    cmd = "docker ps --format '{{.Names}}'"
    stdin, stdout, stderr = ssh.exec_command(cmd)
    names = stdout.read().decode().strip().splitlines()
    return names


# -------------------------
# Configure Alpine
# -------------------------
def configure_alpine(project, ssh):
    print("\n[INFO] Configuring Alpine containers...")

    config = generate_ip_config()

    # get docker containers
    containers = get_all_containers(ssh)

    # get GNS3 docker nodes
    docker_nodes = [n for n in project.nodes if n.node_type == "docker"]

    # sort both lists to align order
    docker_nodes.sort(key=lambda x: x.name)
    containers.sort()

    for i, node in enumerate(docker_nodes):
        if node.name not in config:
            continue

        if i >= len(containers):
            print(f"[ERROR] No container for {node.name}")
            continue

        container_name = containers[i]
        ip, gw = config[node.name]

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

        ssh.close()

        print("\n[SUCCESS] NETWORK CONFIGURED")

    except Exception as e:
        print(f"[ERROR] {e}")


if __name__ == "__main__":
    main()
