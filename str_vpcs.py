import os
import time
import socket
from gns3fy import Gns3Connector, Project

GATEWAY_IP = "192.168.1.1"


# -------------------------------
# Node utilities
# -------------------------------

def list_nodes(project):
    print("\n=== Node List ===")
    for node in project.nodes:
        print(
            f"Name: {node.name} | "
            f"Type: {node.node_type} | "
            f"Status: {node.status} | "
            f"Console: {node.console}"
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

def run_vpcs_commands(node, commands, gns3_host):
    port = node.console
    output = b""

    if port is None:
        raise RuntimeError(f"{node.name} has no console port")

    with socket.create_connection((gns3_host, port), timeout=10) as s:
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


def configure_vpcs(node, index, gns3_host):
    commands = [
        f"set pcname PC{index}",
        "ip dhcp",
        f"gw {GATEWAY_IP}",
        "save",
        f"ping {GATEWAY_IP} -c 2"
    ]

    print(f"\nConfiguring {node.name} -> PC{index}")
    output = run_vpcs_commands(node, commands, gns3_host)

    if "bytes from" in output.lower():
        print(f"{node.name}: Gateway reachable")
    else:
        print(f"{node.name}: Gateway NOT reachable")


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

    gns3_host = connector.host

    print(f"Connected to project '{project_name}'")

    list_nodes(project)

    start_nodes_by_type(project, "vpcs")

    vpcs_nodes = [n for n in project.nodes if n.node_type == "vpcs"]
    print(f"\nFound {len(vpcs_nodes)} VPCS nodes")

    if not vpcs_nodes:
        print("No VPCS nodes found.")
        return

    for i, node in enumerate(vpcs_nodes, start=1):
        configure_vpcs(node, i, gns3_host)

    print("\nVPCS automation completed successfully!")


if __name__ == "__main__":
    main()
