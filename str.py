import os
import time
import sys
from gns3fy import Gns3Connector, Project
from netmiko import ConnectHandler

def list_nodes(project):
    print("\n=== NODE LIST ===")
    for node in project.nodes:
        print(f"{node.name} | Status: {node.status}")

def main():
    # Naudojame trumpesnį timeout jungiantis
    gns3_url = os.environ.get("GNS3_SERVER_URL", "http://192.168.56.102:80")
    project_name = "a"

    try:
        print(f"[INFO] Connecting to GNS3: {gns3_url}...")
        # timeout=10 neleis skriptui kabėti, jei IP nepasiekiamas
        connector = Gns3Connector(url=gns3_url, timeout=10)
        
        project = Project(name=project_name, connector=connector)
        project.get()
        project.get_nodes()

        print(f"[OK] Connected to: {project.name}")

        # Paleidimas
        for node in project.nodes:
            if node.status != "started":
                print(f"Starting: {node.name}")
                node.start()
        
        # Trumpas laukimas ir statuso patikra
        time.sleep(2)
        project.get_nodes()
        list_nodes(project)
        
        print("\n[SUCCESS] Script finished.")

    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        sys.exit(1) # Pranešame Jenkinsui, kad įvyko klaida

if __name__ == "__main__":
    main()
