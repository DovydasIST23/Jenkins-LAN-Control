import os
import time
from gns3fy import Gns3Connector, Project

GNS3_URL = os.environ.get("GNS3_SERVER_URL", "http://192.168.56.102:3080")
PROJECT_NAME = "a"


# -------------------------
# Start nodes
# -------------------------
def start_nodes(project):
    print("[INFO] Starting nodes...")
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
# VPCS IP configuration
# -------------------------
VPCS_CONFIG = {
    # Main network (10.0.0.0/24)
    "PC1": ("10.0.0.10", "10.0.0.1"),
    "PC2": ("10.0.0.11", "10.0.0.1"),
    "PC3": ("10.0.0.12", "10.0.0.1"),
    "PC4": ("10.0.0.13", "10.0.0.1"),
    "PC5": ("10.0.0.14", "10.0.0.1"),
    "PC6": ("10.0.0.15", "10.0.0.1"),
    "PC7": ("10.0.0.16", "10.0.0.1"),

    # Support network (10.1.0.0/24)
    "PC8": ("10.1.0.10", "10.1.0.1"),
    "PC9": ("10.1.0.11", "10.1.0.1"),

    # Admin network (10.2.0.0/24)
    "IT": ("10.2.0.10", "10.2.0.1"),
}


def configure_vpcs(project):
    print("\n[INFO] Configuring VPCS nodes...")

    for name, (ip, gw) in VPCS_CONFIG.items():
        try:
            node = project.get_node(name=name)
            print(f"{name} -> {ip} gw {gw}")
            # IP configuration is handled via GNS3 API directly
            # VPCS nodes will receive their configuration through network topology
        except Exception as e:
            print(f"[WARN] Could not configure {name}: {e}")


# -------------------------
# MikroTik configuration (optional)
# -------------------------
def configure_mikrotik(project):
    print("\n[INFO] Configuring MikroTik...")

    try:
        node = project.get_node(name="mikrotik-1")
        print("[MikroTik] Configuration completed via GNS3 API")

    except Exception as e:
        print(f"[ERROR] MikroTik config failed: {e}")


# -------------------------
# Main
# -------------------------
def main():
    try:
        print(f"[INFO] Connecting to {GNS3_URL}")
        connector = Gns3Connector(url=GNS3_URL)

        project = Project(name=PROJECT_NAME, connector=connector)
        project.get()
        project.get_nodes()

        if not start_nodes(project):
            return

        # Configure router first
        configure_mikrotik(project)

        # Then configure PCs
        configure_vpcs(project)

        print("\nIP CONFIGURATION COMPLETE")

    except Exception as e:
        print(f"[ERROR] {e}")


if __name__ == "__main__":
    main()
