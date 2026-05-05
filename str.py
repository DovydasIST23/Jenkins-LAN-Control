import os
import time
import sys
from gns3fy import Gns3Connector, Project
# Pakeista iš paramiko į netmiko
from netmiko import ConnectHandler 

def list_nodes(project):
    print("\n=== NODE LIST ===")
    for node in project.nodes:
        print(
            f"{node.name} | Type: {node.node_type} | "
            f"Status: {node.status} | ID: {node.node_id}"
        )

def wait_for_nodes(project, timeout=60):
    print("\n[INFO] Waiting for all nodes to start...")
    for _ in range(timeout):
        project.get_nodes()
        if all(n.status == "started" for n in project.nodes):
            print("[OK] All nodes are running")
            return True
        time.sleep(1)
    print("[ERROR] Timeout waiting for nodes")
    return False

def start_all_nodes(project):
    print("\n=== STARTING ALL NODES ===")
    for node in project.nodes:
        if node.status != "started":
            print(f"Starting: {node.name}")
            node.start()
        else:
            print(f"Already running: {node.name}")

def main():
    # Naudojame aplinkos kintamąjį arba numatytąjį URL
    gns3_url = os.environ.get("GNS3_SERVER_URL", "http://192.168.56.102:80")
    project_name = "a"

    try:
        print(f"[INFO] Connecting to GNS3 at {gns3_url}")
        connector = Gns3Connector(url=gns3_url)

        project = Project(name=project_name, connector=connector)
        project.get()
        project.get_nodes()

        print(f"[OK] Connected to project: {project.name}")

        list_nodes(project)

        # Paleidžiame įrenginius
        start_all_nodes(project)

        if not wait_for_nodes(project):
            sys.exit(1) # Pranešame Jenkins apie klaidą

        print("\n[SUCCESS] Topology is fully running")

    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
