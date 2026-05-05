import os
import time
from gns3fy import Gns3Connector, Project
# Netmiko paruošimas būsimoms SSH užduotims
from netmiko import ConnectHandler 

def list_nodes(project):
    print("\n=== NODE LIST ===")
    for node in project.nodes:
        print(
            f"{node.name} | Type: {node.node_type} | "
            f"Status: {node.status} | ID: {node.node_id}"
        )

def wait_for_nodes_stop(project, timeout=60):
    print("\n[INFO] Waiting for all nodes to stop...")
    for _ in range(timeout):
        project.get_nodes()
        if all(n.status == "stopped" for n in project.nodes):
            print("[OK] All nodes have stopped")
            return True
        time.sleep(1)
    print("[ERROR] Timeout waiting for nodes to stop")
    return False

def stop_all_nodes(project):
    print("\n=== STOPPING ALL NODES ===")
    for node in project.nodes:
        if node.status != "stopped":
            print(f"Stopping: {node.name}")
            node.stop()
        else:
            print(f"Already stopped: {node.name}")

def main():
    gns3_url = os.environ.get("GNS3_SERVER_URL", "http://192.168.56.102:80")
    project_name = "a"

    try:
        print(f"[INFO] Connecting to GNS3 at {gns3_url}")
        connector = Gns3Connector(url=gns3_url)
        project = Project(name=project_name, connector=connector)
        project.get()
        project.get_nodes()

        print(f"[OK] Connected to project: {project.name}")
        
        # Parodome esamą būseną
        list_nodes(project)

        # Atliekame stabdymą
        stop_all_nodes(project)

        if not wait_for_nodes_stop(project):
            return

        print("\n[SUCCESS] All devices in topology are stopped")

    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == "__main__":
    main()
