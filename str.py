import os
import time
from gns3fy import Gns3Connector, Project


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


def stop_all_nodes(project):
    print("\n=== STOPPING ALL NODES ===")
    for node in project.nodes:
        if node.status == "started":
            print(f"Stopping: {node.name}")
            node.stop()


def main():
    gns3_url = os.environ.get("GNS3_SERVER_URL", "http://192.168.56.102:3080")
    project_name = "a"

    try:
        print(f"[INFO] Connecting to GNS3 at {gns3_url}")
        connector = Gns3Connector(url=gns3_url)

        project = Project(name=project_name, connector=connector)
        project.get()
        project.get_nodes()

        print(f"[OK] Connected to project: {project.name}")

        list_nodes(project)

        # Start everything (Docker + MikroTik)
        start_all_nodes(project)

        if not wait_for_nodes(project):
            return

        print("\n[SUCCESS] Topology is fully running")

    except Exception as e:
        print(f"[ERROR] {e}")


if __name__ == "__main__":
    main()
