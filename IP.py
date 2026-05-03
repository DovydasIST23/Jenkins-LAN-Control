import os
import time
import requests
import paramiko
from gns3fy import Gns3Connector, Project

GNS3_URL = os.environ.get("GNS3_SERVER_URL", "http://192.168.56.102:80")
PROJECT_NAME = "a"
# =========================
# SHH Info
# =========================
GNS3_VM_HOST = "192.168.56.102"
GNS3_VM_USER = "gns3"
GNS3_VM_PASS = "gns3"

# =========================
# Helpers
# =========================

def api_post(path, data):
    url = f"{GNS3_URL}{path}"
    return requests.post(url, json=data).json()


def wait_for_nodes(project, timeout=60):
    print("[INFO] Waiting for nodes...")
    for _ in range(timeout):
        project.get_nodes()
        if all(n.status == "started" for n in project.nodes):
            print("[OK] Nodes running")
            return True
        time.sleep(1)
    return False


# =========================
# Docker Command Execution (NO TELNET)
# =========================

def run_docker_cmd(project_id, node_id, cmd):
    return api_post(
        f"/v2/projects/{project_id}/nodes/{node_id}/execute",
        {"command": cmd}
    )


# =========================
# MikroTik via SSH (NOT TELNET)
# =========================

def mikrotik_ssh_config(ip):
    print("[INFO] Configuring MikroTik via SSH")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    ssh.connect(GNS3_VM_HOST, username=GNS3_VM_USER, password=GNS3_VM_PASS)

    commands = [
        "/ip address add address=192.168.10.1/24 interface=ether1",
        "/ip address add address=192.168.20.1/24 interface=ether2",
        "/ip address add address=192.168.30.1/24 interface=ether3",
    ]

    for cmd in commands:
        ssh.exec_command(cmd)

    ssh.close()


# =========================
# Config Functions
# =========================

def configure_ovs(project, node):
    print(f"[INFO] OVS: {node.name}")

    cmds = [
        "ovs-vsctl add-br br0",
        "for i in 0 1 2 3 4 5 6 7; do ovs-vsctl add-port br0 eth$i; done",
        "ip link set br0 up"
    ]

    for cmd in cmds:
        run_docker_cmd(project.project_id, node.node_id, cmd)


def configure_alpine(project, node):
    name = node.name

    if "1" in name:
        ip = "192.168.10.10"
        gw = "192.168.10.1"

    elif any(x in name for x in ["2","3","4","5","6","7","8"]):
        num = int(name.split("-")[-1])
        ip = f"192.168.20.{10 + num}"
        gw = "192.168.20.1"

    elif any(x in name for x in ["9","10"]):
        num = int(name.split("-")[-1])
        ip = f"192.168.30.{10 + num}"
        gw = "192.168.30.1"

    else:
        return

    print(f"[INFO] Alpine {name} -> {ip}")

    cmds = [
        f"ip addr add {ip}/24 dev eth0",
        "ip link set eth0 up",
        f"ip route add default via {gw}"
    ]

    for cmd in cmds:
        run_docker_cmd(project.project_id, node.node_id, cmd)


# =========================
# Ping Test
# =========================

def ping_test(project, node, target):
    print(f"[PING] {node.name} -> {target}")

    result = run_docker_cmd(
        project.project_id,
        node.node_id,
        f"ping -c 3 {target}"
    )

    output = str(result)

    if "0% packet loss" in output:
        print("[OK]")
        return True
    else:
        print("[FAIL]")
        return False


# =========================
# MAIN
# =========================

def main():
    connector = Gns3Connector(url=GNS3_URL)
    project = Project(name=PROJECT_NAME, connector=connector)

    project.get()
    project.get_nodes()

    print("[INFO] Starting nodes...")
    for node in project.nodes:
        if node.status != "started":
            node.start()

    if not wait_for_nodes(project):
        print("[ERROR] Nodes failed to start")
        return

    time.sleep(15)

    # Configure Docker nodes
    for node in project.nodes:
        if "Alpine" in node.name:
            configure_alpine(project, node)

        elif any(x in node.name for x in ["Main", "Admin", "Support"]):
            configure_ovs(project, node)

    # MikroTik (replace with actual mgmt IP!)
    mikrotik_ssh_config("192.168.56.102")

    # Tests
    nodes = {n.name: n for n in project.nodes}

    ping_test(project, nodes["AlpineLinux-1"], "192.168.10.1")
    ping_test(project, nodes["AlpineLinux-2"], "192.168.20.1")
    ping_test(project, nodes["AlpineLinux-9"], "192.168.30.1")

    ping_test(project, nodes["AlpineLinux-1"], "192.168.20.12")

    print("\n[SUCCESS] Network test completed")


if __name__ == "__main__":
    main()
