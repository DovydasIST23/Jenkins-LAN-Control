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

def start_node(connector, node):
    """Start a node if it is stopped."""
    if node.status != "started":
        connector.start_node(project_id=node.project_id, node_id=node.node_id)
        print(f"Starting node: {node.name}")
    else:
        print(f"Node already running: {node.name}")

def stop_node(connector, node):
    """Stop a node if it is running."""
    if node.status == "started":
        connector.stop_node(project_id=node.project_id, node_id=node.node_id)
        print(f"Stopping node: {node.name}")
    else:
        print(f"Node already stopped: {node.name}")

def start_nodes_by_type(connector, project, node_type_filter):
    """Start only nodes of a specific type (e.g., 'vpcs', 'qemu', 'dynamips')."""
    print(f"\n=== Starting nodes of type: {node_type_filter} ===")
    for node in project.nodes:
        if node.node_type == node_type_filter:
            start_node(connector, node)

def stop_nodes_by_type(connector, project, node_type_filter):
    """Stop only nodes of a specific type."""
    print(f"\n=== Stopping nodes of type: {node_type_filter} ===")
    for node in project.nodes:
        if node.node_type == node_type_filter:
            stop_node(connector, node)

def main():
    # Retrieve GNS3 server URL from environment variables or use a default value
    gns3_server_url = os.environ.get("GNS3_SERVER_URL", "http://192.168.56.102:80")
    project_name = "a"

    try:
        # Connect to GNS3 server
        connector = Gns3Connector(url=gns3_server_url)
        print(f"Connecting to GNS3 server at {gns3_server_url}...")

        project = Project(name=project_name, connector=connector)
        project.get()
        print(f"Connected to project '{project_name}'.\n")

        # Show all node info
        list_nodes(project)

        # Example actions ---------------------------------------------

        # Start one specific node
        # my_node = project.get_node(name="R1")
        # start_node(connector, my_node)

        # Start all VPCS nodes
        start_nodes_by_type(connector, project, "vpcs")

        # Stop all QEMU nodes
        # stop_nodes_by_type(connector, project, "qemu")

        # Start all nodes
        # connector.start_all_nodes(project_id=project.project_id)

        # Stop all nodes
        # connector.stop_all_nodes(project_id=project.project_id)

    except Exception as e:
        print(f"Error: {e}")
        print("Failed to connect to the GNS3 server or retrieve project.")

if __name__ == "__main__":
    main()
