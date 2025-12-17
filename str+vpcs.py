import os
import time
import telnetlib
from gns3fy import Gns3Connector, Project

GATEWAY_IP = "192.168.1.1"


# -------------------------------
# Node Management Utilities
# -------------------------------

def list_nodes(project):
    """Print all nodes with useful information."""
    print("\n=== Node List ===")
    for node in project.nodes:
        print(
            f"Name: {node.name} | Type: {node.node_type} | Status: {node.status} "
            f"| Console: {node.console} | Node ID: {node.node_id}"
        )


def start_node(node):
    """Start a node if it is stopped."""
    if node.status != "started":
        node.start()
        print(f"Starting node: {node.name}")
        time.sleep(1)
    else:
        print(f"Node already running: {node.name}")


def stop_node(node):
    """Stop a node if it is running."""
    if node.status == "started":
        node.stop()
        print(f"Stopping node: {node.name}")
    else:
        print(f"Node already stopped: {node.name}")


def start_nodes_by_type(project, node_type_filter):
    """Start only nodes of a specific type."""
    print(f"\n=== Starting nodes of type: {node_type_filter} ===")
    for node in project.nodes:
        if node.node_type == node_type_filter:
            start_node(node)


# -------------------------------
# VPCS Automation (Added Code)
# -------------------------------

def run_vpcs_commands(node, commands):
    host = node.console_host
    port = node.console

    tn = telnetlib.Telnet(host, port, timeout=5)
    time.sleep(1)

    for cmd in commands:
        tn.write(cmd.encode("ascii") + b"\n")
        time.sleep(0.4)

    output = tn.read_very_eager().decode("ascii", errors="ignore")
    tn.close()
    return output


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
# Main Orchestration
# -------------------------------

def main():
    gns3_server_url = os.environ.get("GNS3_SERVER_URL", "http://192.168.56.102:80")
    project_name = "a"

    try:
        print(f"Connecting to GNS3 server at {gns3_server_url}...")
        connector = Gns3Connector(url=gns3_server_url)
        project = Project(name=project_name, connector=connector)
        project.get()

        print(f"Connected to project '{project_name}'")

        # Show all nodes
        list_nodes(project)

        # Start all VPCS nodes
        start_nodes_by_type(project, "vpcs")

        # Collect VPCS nodes
        vpcs_nodes = [n for n in project.nodes if n.node_type == "vpcs"]

        print(f"\n📊 Found {len(vpcs_nodes)} VPCS nodes")

        if not vpcs_nodes:
            print("No VPCS nodes found. Exiting.")
            return

        # Configure each VPCS
        for i, node in enumerate(vpcs_nodes, start=1):
            configure_vpcs(node, i)

        print("\n🎉 VPCS DHCP + Routing automation completed!")

    except Exception as e:
        print(f"Error: {e}")
        print("Failed to connect to the GNS3 server or retrieve project.")


if __name__ == "__main__":
    main()
