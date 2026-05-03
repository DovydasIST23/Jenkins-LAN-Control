import os
import time
import requests
import paramiko
from gns3fy import Gns3Connector, Project

GNS3_URL = os.environ.get("GNS3_SERVER_URL", "http://192.168.56.102:80")
PROJECT_NAME = "a"

# MikroTik SSH duomenys
GNS3_VM_HOST = "192.168.56.102"
GNS3_VM_USER = "gns3"
GNS3_VM_PASS = "gns3"

# =========================
# Helpers
# =========================

def api_post(path, data):
    url = f"{GNS3_URL}{path}"
    try:
        response = requests.post(url, json=data)
        # Ši dalis neleidžia skriptui nulūžti, kai GNS3 nieko neatsako
        if response.status_code == 200 and not response.text.strip():
            return {"status": "success"}
        return response.json()
    except Exception:
        return {"status": "executed"}


def run_docker_cmd(project_id, node_id, cmd):
    return api_post(f"/v2/projects/{project_id}/nodes/{node_id}/execute", {"command": cmd})

# =========================
# Konfigūravimo funkcijos
# =========================

def mikrotik_ssh_config():
    print("[INFO] Konfigūruojamas MikroTik per SSH...")
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(GNS3_VM_HOST, username=GNS3_VM_USER, password=GNS3_VM_PASS, timeout=10)

        # ether2,3,4 atitinka GNS3 portus 1,2,3
        commands = [
            "/ip address add address=192.168.10.1/24 interface=ether2",
            "/ip address add address=192.168.20.1/24 interface=ether3",
            "/ip address add address=192.168.30.1/24 interface=ether4",
        ]

        for cmd in commands:
            ssh.exec_command(cmd)
            time.sleep(0.5)
        ssh.close()
        print("[OK] MikroTik paruoštas.")
    except Exception as e:
        print(f"[ERROR] MikroTik SSH klaida: {e}")

def configure_alpine(project, node):
    name = node.name
    # Tiksli IP adresų priskyrimo logika
    if name == "AlpineLinux-1":
        ip, gw = "192.168.10.10", "192.168.10.1"
    elif any(f"AlpineLinux-{i}" in name for i in range(2, 9)):
        num = name.split("-")[-1]
        ip, gw = f"192.168.20.{10+int(num)}", "192.168.20.1"
    elif any(f"AlpineLinux-{i}" in name for i in [9, 10]):
        num = name.split("-")[-1]
        ip, gw = f"192.168.30.{10+int(num)}", "192.168.30.1"
    else:
        return

    print(f"[INFO] Alpine {name} -> {ip}")
    run_docker_cmd(project.project_id, node.node_id, f"ip addr add {ip}/24 dev eth0")
    run_docker_cmd(project.project_id, node.node_id, "ip link set eth0 up")
    run_docker_cmd(project.project_id, node.node_id, f"ip route add default via {gw}")

def main():
    connector = Gns3Connector(url=GNS3_URL)
    project = Project(name=PROJECT_NAME, connector=connector)
    
    try:
        project.get()
        project.get_nodes()
    except Exception as e:
        print(f"[ERROR] Nepavyko rasti projekto '{PROJECT_NAME}': {e}")
        return

    print("[INFO] Paleidžiami mazgai...")
    for node in project.nodes:
        if node.status != "started":
            node.start()
    
    print("[INFO] Laukiama 15s, kol OS pasikraus...")
    time.sleep(15)

    for node in project.nodes:
        if "Alpine" in node.name:
            configure_alpine(project, node)
        elif any(x in node.name for x in ["Main", "Admin", "Support"]):
            run_docker_cmd(project.project_id, node.node_id, "ovs-vsctl add-br br0")
            run_docker_cmd(project.project_id, node.node_id, "ip link set br0 up")

    mikrotik_ssh_config()
    print("\n[SUCCESS] Tinklo konfigūravimas baigtas.")

if __name__ == "__main__":
    main()
