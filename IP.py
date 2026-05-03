import os
import time
import requests
import paramiko
import re
from gns3fy import Gns3Connector, Project

# Nustatymai
GNS3_URL = os.environ.get("GNS3_SERVER_URL", "http://192.168.56.102:80")
PROJECT_NAME = "a"

# MikroTik / GNS3 VM SSH duomenys
GNS3_VM_HOST = "192.168.56.102"
GNS3_VM_USER = "gns3"
GNS3_VM_PASS = "gns3"

# =========================
# Pagalbinės funkcijos (API)
# =========================

def api_post(path, data):
    """Saugi užklausa: suvaldo tuščius GNS3 atsakymus po komandų vykdymo."""
    url = f"{GNS3_URL}{path}"
    try:
        response = requests.post(url, json=data)
        # Jei sėkmė, bet atsakymas tuščias (Docker execute atvejis)
        if response.status_code == 200 and not response.text.strip():
            return {"status": "success"}
        return response.json()
    except Exception:
        return {"status": "executed"}

def run_docker_cmd(project_id, node_id, cmd):
    """Vykdo komandą Docker konteineryje."""
    return api_post(f"/v2/projects/{project_id}/nodes/{node_id}/execute", {"command": cmd})

# =========================
# Konfigūravimo logika
# =========================

def mikrotik_ssh_config():
    """Konfigūruoja MikroTik sąsajas."""
    print("[INFO] Jungiamasi prie MikroTik per SSH...")
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(GNS3_VM_HOST, username=GNS3_VM_USER, password=GNS3_VM_PASS, timeout=10)

        # ether2=Port1(Admin), ether3=Port2(Main), ether4=Port3(Support)
        commands = [
            "/ip address add address=192.168.10.1/24 interface=ether2",
            "/ip address add address=192.168.20.1/24 interface=ether3",
            "/ip address add address=192.168.30.1/24 interface=ether4",
        ]

        for cmd in commands:
            ssh.exec_command(cmd)
            time.sleep(0.5)
        ssh.close()
        print("[OK] MikroTik IP adresai sukonfigūruoti.")
    except Exception as e:
        print(f"[ERROR] MikroTik SSH klaida: {e}")

def configure_alpine(project, node):
    """Priskiria IP adresus Alpine mazgams."""
    name = node.name
    
    # Skaičiaus ištraukimas iš pavadinimo (pvz., "AlpineLinux-2" -> 2)
    match = re.search(r'(\d+)', name)
    num = int(match.group(1)) if match else 0

    # IP adresų priskyrimo logika pagal schemas
    if num == 1:
        ip, gw = "192.168.10.10", "192.168.10.1"
    elif 2 <= num <= 8:
        ip, gw = f"192.168.20.{10+num}", "192.168.20.1"
    elif 9 <= num <= 10:
        ip, gw = f"192.168.30.{10+num}", "192.168.30.1"
    else:
        return

    print(f"[INFO] Konfigūruojamas {name} -> IP: {ip}")

    # „Super-safe“ metodas: bandoma uždėti IP ant visų interfeisų (eth0-eth2)
    # nes nuotraukoje matėme, kad eth0 indeksas gali būti pasikeitęs (pvz. 15)
    for i in range(3):
        iface = f"eth{i}"
        run_docker_cmd(project.project_id, node.node_id, f"ip addr add {ip}/24 dev {iface}")
        run_docker_cmd(project.project_id, node.node_id, f"ip link set {iface} up")
    
    # Nustatomas numatytasis šliuzas (Gateway)
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
    
    print("[INFO] Laukiama 20s, kol sistemos pilnai užsikraus...")
    time.sleep(20)

    # Vykdome konfigūravimą
    for node in project.nodes:
        if "Alpine" in node.name:
            configure_alpine(project, node)
        elif any(x in node.name for x in ["Main", "Admin", "Support"]):
            # OVS nustatymai
            run_docker_cmd(project.project_id, node.node_id, "ovs-vsctl add-br br0")
            run_docker_cmd(project.project_id, node.node_id, "ip link set br0 up")

    # MikroTik nustatymai
    mikrotik_ssh_config()
    
    print("\n[SUCCESS] Tinklo konfigūravimas baigtas.")

if __name__ == "__main__":
    main()
