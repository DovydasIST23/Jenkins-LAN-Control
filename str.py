import os
from gns3fy import Gns3Connector, Project

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

def stop_nodes_by_type(project, node_type_filter):
    """Stop only nodes of a specific type."""
    print(f"\n=== Stopping nodes of type: {node_type_filter} ===")
    for node in project.nodes:
        if node.node_type == node_type_filter:
            stop_node(node)

def main():
    gns3_server_url = os.environ.get("GNS3_SERVER_URL", "http://192.168.56.102:80")
    project_name = "a"

    try:
        connector = Gns3Connector(url=gns3_server_url)
        print(f"Connecting to GNS3 server at {gns3_server_url}...")

        project = Project(name=project_name, connector=connector)
        project.get()
        print(f"Connected to project '{project_name}'.\n")

        # Show node info
        list_nodes(project)

        # Start all VPCS nodes (fix works here!)
        start_nodes_by_type(project, "vpcs")
        start_nodes_by_type(project, "mikrotik-1") 
        
        # Examples:
        # stop_nodes_by_type(project, "qemu")
        # node = project.get_node(name="R1")
        # start_node(node)

    except Exception as e:
        print(f"Error: {e}")
        print("Failed to connect to the GNS3 server or retrieve project.")

if __name__ == "__main__":
    main()
