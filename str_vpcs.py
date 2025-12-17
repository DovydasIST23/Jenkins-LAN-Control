import os
import time
import socket
from gns3fy import Gns3Connector, Project

GATEWAY_IP = "192.168.56.1"


# -------------------------------
# Node utilities
# -------------------------------

def list_nodes(project):
    print("\n=== Node List ===")
    for node in project.nodes:
        print(
            f"Name: {node.name} | Type: {node.node_type} | "
            f"Status: {node.status} | Console: {node.console}"
        )


def start_node(node):
    if node.status != "started":
        node.start()
        print(f"Starting node: {node.name}")
        time.sleep(1)


def start_nodes_by_type(project, node_type):
    print(f"\n=== Starting {node_type} nodes ===")
    for node in project.nodes:
        if node.node_type == node_type:
            start_node(node)


# -------------------------------
# VPCS socket automation
# -------------------------------

def run_vpcs_commands(node, commands):
    host = node.console_host
    port = node.console

    output = b""

    with socket.create_connection((host, port), timeout=5) as s:
        s.settimeout(2)
        time.sleep(1)

        for cmd in commands:
            s.sendall(cmd.encode("ascii") + b"\n")
            time.sleep(0.4)

        try:
            while True:
                data = s.recv(4096)
                if not data:
                    break
                output += data
        except socket.timeout:
            pass

    return output.decode("ascii", errors="ignore")


def configure_vpcs(node, index):
    commands = [
        f"set pcname PC{index}",
        "ip dhcp",
        f"gw {GATEWAY_IP}",
        "save",
        f"ping {GATEWAY_IP} -c 2"
    ]

    print(f"\nConfiguring {node.name} → PC{index}")
    output = run_vpcs_commands(node, commands)

    if "bytes from" in output.lower():
        print(f"✅ {node.name}: Gateway reachable")
    else:
        print(f"⚠️ {node.name}: Gateway NOT reachable")


# -------------------------------
# Main
# -------------------------------

def main():
    gns3_server_url = os.environ.get(
        "GNS3_SERVER_URL", "http://192.168.56.102:80"
    )
    project_name = "a"

    connector = Gns3Connector(url=gns3_server_url)
    project = Project(name=project_name, connector=connector)
    project.get()
    project.open()
    
    print(f"Connected to project '{project_name}'")

    list_nodes(project)

    start_nodes_by_type(project, "vpcs")

    vpcs_nodes = [n for n in project.nodes if n.node_type == "vpcs"]

    print(f"\n📊 Found {len(vpcs_nodes)} VPCS nodes")

    if not vpcs_nodes:
        print("No VPCS nodes found.")
        return

    for i, node in enumerate(vpcs_nodes, start=1):
        configure_vpcs(node, i)

    print("\n🎉 VPCS automation completed successfully!")


if __name__ == "__main__":
    main()

