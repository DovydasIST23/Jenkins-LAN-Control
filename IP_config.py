import os
import time
import requests
from gns3fy import Gns3Connector, Project

GNS3_URL = os.environ.get("GNS3_SERVER_URL", "http://192.168.56.102:3080")
PROJECT_NAME = "a"


# -------------------------
# Alpine Linux IP config
# -------------------------
NODE_CONFIG = {
    # Main network
    "PC1": ("10.0.0.10", "10.0.0.1"),
    "PC2": ("10.0.0.11", "10.0.0.1"),
    "PC3": ("10.0.0.12", "10.0.0.1"),
    "PC4": ("10.0.0.13", "10.0.0.1"),
    "PC5": ("10.0.0.14", "10.0.0.1"),
    "PC6": ("10.0.0.15", "10.0.0.1"),
    "PC7": ("10.0.0.16", "10.0.0.1"),

    # Support network
    "PC8": ("10.1.0.10", "10.1.0.1"),
    "PC9": ("10.1.0.11", "10.1.0.1"),

    # Admin network
    "IT": ("10.2.0.10", "10.2.0.1"),
}


def configure_alpine(project):
    print("\n[INFO] Configuring Alpine Docker nodes...")

    for name, (ip, gw) in NODE_CONFIG.items():
        try:
            node = project.get_node(name=name)

            startup_script = f"""
#!/bin/sh
ip addr add {ip}/24 dev eth0
ip link set eth0 up
ip route add default via {gw}

# keep container alive
while true; do sleep 3600; done
"""

            api_url = f"{GNS3_URL}/projects/{project.project_id}/nodes/{node.node_id}"

            payload = {
                "startup_script": startup_script
            }

            response = requests.put(api_url, json=payload)

            if response.status_code in [200, 201]:
                print(f"[OK] {name} -> {ip}")
            else:
                print(f"[WARN] {name}: {response.text}")

        except Exception as e:
            print(f"[ERROR] {name}: {e}")


# -------------------------
# MikroTik config
# -------------------------
def configure_mikrotik(project):
    print("\n[INFO] Configuring MikroTik router...")

    try:
        node = project.get_node(name="mikrotik-1")

        startup_script = """/ip address add address=10.0.0.1/24 interface=ether1
/ip address add address=10.1.0.1/24 interface=ether2
/ip address add address=10.2.0.1/24 interface=ether3
"""

        api_url = f"{GNS3_URL}/projects/{project.project_id}/nodes/{node.node_id}"

        payload = {
            "startup_config": startup_script
        }

        response = requests.put(api_url, json=payload)

        if response.status_code in [200, 201]:
            print("[OK] MikroTik configured")
        else:
            print(f"[WARN] MikroTik: {response.text}")

    except Exception as e:
        print(f"[ERROR] MikroTik: {e}")


# -------------------------
# Start nodes
# -------------------------
def start_nodes(project):
    print("\n[INFO] Starting nodes...")

    for node in project.nodes:
        if node.status != "started":
            print(f"Starting {node.name}")
            node.start()

    # wait until started
    for _ in range(60):
        project.get_nodes()
        if all(n.status == "started" for n in project.nodes):
            print("[OK] All nodes started")
            return True
        time.sleep(1)

    print("[ERROR] Nodes failed to start")
    return False


# -------------------------
# MAIN
# -------------------------
def main():
    try:
        print(f"[INFO] Connecting to {GNS3_URL}")
        connector = Gns3Connector(url=GNS3_URL)

        project = Project(name=PROJECT_NAME, connector=connector)
        project.get()
        project.get_nodes()

        print(f"[OK] Project: {project.name}")

        # Apply configs BEFORE starting
        configure_mikrotik(project)
        configure_alpine(project)

        # Small delay (important for GNS3 API consistency)
        time.sleep(3)

        if not start_nodes(project):
            return

        print("\n[SUCCESS] NETWORK CONFIGURED")

    except Exception as e:
        print(f"[ERROR] {e}")


if __name__ == "__main__":
    main()
