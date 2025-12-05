import os
from gns3fy import Gns3Connector, Project

def main():
    # Retrieve GNS3 server URL from environment variables or use a default value
    gns3_server_url = os.environ.get("GNS3_SERVER_URL", "http://192.168.56.102:80")
    project_name = "MyAutomatedLab"  # Ensure this project exists in your GNS3 VM

    try:
        # Connect to the GNS3 server
        server = Gns3Connector(url=gns3_server_url)
        print(f"Connecting to GNS3 server at {gns3_server_url}...")

        # Retrieve the project
        project = Project(server=server, name=project_name)
        project.get()
        print(f"Successfully connected to project '{project_name}' on GNS3 server.")

        # Example: Start all nodes in the project (uncomment if needed)
        # server.start_all_nodes(project_id=project.project_id)
        print("Automation logic can be added here.")

    except Exception as e:
        print(f"Error: {e}")
        print("Failed to connect to the GNS3 server or retrieve the project.")

if __name__ == "__main__":
    main()