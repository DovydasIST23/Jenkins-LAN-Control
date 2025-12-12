import os
from gns3fy import Gns3Connector, Project

def main():
    # Retrieve GNS3 server URL from environment variables or use a default value
    gns3_server_url = os.environ.get("GNS3_SERVER_URL", "http://192.168.56.102:80")
    project_name = "a"  # Name of the project in GNS3

    try:
        # Connect to the GNS3 server
        connector = Gns3Connector(url=gns3_server_url)
        print(f"Connecting to GNS3 server at {gns3_server_url}...")

        # Retrieve the project
        project = Project(name=project_name, connector=connector)
        project.get()
        print(f"Successfully connected to project '{project_name}' on GNS3 server.")

        # Example: Start all nodes in the project (uncomment if needed)
        # connector.start_all_nodes(project_id=project.project_id)
        print("Automation logic can be added here.")

    except Exception as e:
        print(f"Error: {e}")
        print("Failed to connect to the GNS3 server or retrieve the project.")

        # if __name__ == "__main__":
        #  main()

for node in project.nodes:
    print(f"Node: {node.name} -- Node Type: {node.node_type} -- Status: {node.status}")