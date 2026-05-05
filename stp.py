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

def wait_for_nodes_to_stop(project, timeout=60):
    print("\n[INFO] Waiting for all nodes to stop...")
    for _ in range(timeout):
        project.get_nodes()
        # Tikriname, ar visi mazgai yra "stopped" būsenos
        if all(n.status == "stopped" for n in project.nodes):
            print("[OK] All nodes are stopped")
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
    # Naudojame aplinkos kintamąjį iš Jenkins arba numatytąjį adresą
    gns3_url = os.environ.get("GNS3_SERVER_URL", "http://192.168.56.102:80")
    project_name = "a"

    try:
        print(f"[INFO] Connecting to GNS3 at {gns3_url}")
        connector = Gns3Connector(url=gns3_url)

        project = Project(name=project_name, connector=connector)
        project.get()
        project.get_nodes()

        print(f"[OK] Connected to project: {project.name}")

        # Parodome esamą būseną prieš stabdymą
        list_nodes(project)

        # Stabdomi visi įrenginiai (Docker, MikroTik ir kt.)
        stop_all_nodes(project)

        # Laukiame, kol viskas užges
        if not wait_for_nodes_to_stop(project):
            print("[WARNING] Some nodes might still be shutting down.")
            return

        print("\n[SUCCESS] Topology is fully stopped")

    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == "__main__":
    main()
