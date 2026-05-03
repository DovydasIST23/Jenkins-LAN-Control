import os
import time
import requests
import paramiko
from gns3fy import Gns3Connector, Project

GNS3_URL = os.environ.get("GNS3_SERVER_URL", "http://192.168.56.102:80")
PROJECT_NAME = "a"

# MikroTik SSH prisijungimas (Jungiamės per GNS3 VM IP)
GNS3_VM_HOST = "192.168.56.102"
GNS3_VM_USER = "gns3"
GNS3_VM_PASS = "gns3"

def api_post(path, data):
    """Saugi API užklausa, išvengianti JSONDecodeError."""
    url = f"{GNS3_URL}{path}"
    try:
        response = requests.post(url, json=data)
        if not response.text.strip():
            return {"status": "ok"}
        return response.json()
    except:
        return {"status": "executed", "output": response.text}

def run_docker_cmd(project_id, node_id, cmd):
    return api_post(f"/v2/projects/{project_id}/nodes/{node_id}/execute", {"command": cmd})

def mikrotik_ssh_config():
    print(f"[INFO] Configuring MikroTik via SSH...")
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        # Jungiamės prie GNS3 VM, kuri peradresuoja į MikroTik (numatytasis portas dažniausiai 5000+ serija)
        # Jei MikroTik pasiekiamas tiesiogiai per 22 portą:
        ssh.connect(GNS3_VM_HOST, username=GNS3_VM_USER, password=GNS3_VM_PASS, timeout=10)

        # Naudojame ether2, ether3, ether4, nes jie atitinka GNS3 portus 1, 2, 3
        commands = [
            "/ip address remove [/ip address find address=\"192.168.10.1/24\"]",
            "/ip address add address=192.168.10.1/24 interface=ether2",
            "/ip address add address=192.168.20.1/24 interface=ether3",
            "/ip address add address=192.168.30.1/24 interface=ether4",
        ]

        for cmd in commands:
            ssh.exec_command(cmd)
            time.sleep(0.5)
        ssh.close()
        print("[OK] MikroTik configuration sent.")
    except Exception as e:
        print(f"[WARNING] MikroTik SSH connection failed: {e}")

def configure_alpine(project, node):
    name = node.name
    # Priskyrimo logika pagal pavadinimus tavo nuotraukoje
    if "AlpineLinux-1" in name:
        ip, gw = "192.168.10.10", "192.168.10.1"
    elif any(x in name for x in ["-2", "-3", "-4", "-5", "-6", "-7", "-8"]):
        num = name.split("-")[-1]
        ip, gw = f"192.168.20.{10+int(num)}", "192.168.20.1"
    elif any(x in name for x in ["-9", "-10"]):
        num = name.split("-")[-1]
        ip, gw = f"192.168.30.{10+int(num)}", "192.168.30.1"
    else: return

    print(f"[INFO] Configuring {name} ({ip})")
    cmds = [f"ip addr add {ip}/24 dev eth0", "ip link set eth0 up", f"ip route add default via {gw}"]
    for cmd in cmds:
        run_docker_cmd(project.project_id, node.node_id, cmd)

def main():
    connector = Gns3Connector(url=GNS3_URL)
    project = Project(name=PROJECT_NAME, connector=connector)
    project.get()
    project.get_nodes()

    # Paleidžiame mazgus
    for node in project.nodes:
        if node.status != "started": node.start()
    
    print("[INFO] Waiting 15s for boot...")
    time.sleep(15)

    # Konfigūruojame viską
    for node in project.nodes:
        if "Alpine" in node.name:
            configure_alpine(project, node)
        elif any(x in node.name for x in ["Main", "Admin", "Support"]):
            # OVS konfigūracija
            run_docker_cmd(project.project_id, node.node_id, "ovs-vsctl add-br br0")
            run_docker_cmd(project.project_id, node.node_id, "ip link set br0 up")

    mikrotik_ssh_config()

    # Greitas testas
    nodes_dict = {n.name: n for n in project.nodes}
    if "AlpineLinux-1" in nodes_dict:
        print("\n--- RUNNING PING TEST ---")
        res = run_docker_cmd(project.project_id, nodes_dict["AlpineLinux-1"].node_id, "ping -c 2 192.168.10.1")
        print(f"Result: {'SUCCESS' if '0% packet loss' in str(res) else 'FAIL'}")

if __name__ == "__main__":
    main()
