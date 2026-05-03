import os
import time
import requests
import paramiko
from gns3fy import Gns3Connector, Project

# Aplinkos kintamieji arba numatytosios reikšmės
GNS3_URL = os.environ.get("GNS3_SERVER_URL", "http://192.168.56.102:80")
PROJECT_NAME = "a"

# =========================
# SSH Info (MikroTik konfigūravimui)
# =========================
GNS3_VM_HOST = "192.168.56.102"
GNS3_VM_USER = "gns3"
GNS3_VM_PASS = "gns3"

# =========================
# Helpers
# =========================

def api_post(path, data):
    """Saugi POST užklausa, kuri neleidžia skriptui nulūžti gavus ne JSON atsakymą."""
    url = f"{GNS3_URL}{path}"
    try:
        response = requests.post(url, json=data)
        # GNS3 Docker execute dažnai grąžina tuščią atsakymą, kas nėra JSON
        if not response.text.strip():
            return {"status": "success", "output": ""}
        return response.json()
    except Exception as e:
        # Jei tai ne JSON, grąžiname tekstą kaip output
        return {"status": "executed", "output": response.text}

def wait_for_nodes(project, timeout=60):
    print("[INFO] Waiting for nodes to stabilize...")
    for _ in range(timeout):
        project.get_nodes()
        if all(n.status == "started" for n in project.nodes):
            print("[OK] All nodes are running")
            return True
        time.sleep(2)
    return False

# =========================
# Docker Command Execution
# =========================

def run_docker_cmd(project_id, node_id, cmd):
    # Grąžiname tik atsakymą iš saugios funkcijos
    return api_post(
        f"/v2/projects/{project_id}/nodes/{node_id}/execute",
        {"command": cmd}
    )

# =========================
# MikroTik via SSH
# =========================

def mikrotik_ssh_config(ip):
    print(f"[INFO] Connecting to MikroTik at {ip} via SSH...")
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Pridedame timeout, kad Jenkins nelauktų amžinai jei SSH nepasiekiamas
        ssh.connect(GNS3_VM_HOST, username=GNS3_VM_USER, password=GNS3_VM_PASS, timeout=10)

        commands = [
            "/ip address add address=192.168.10.1/24 interface=ether1",
            "/ip address add address=192.168.20.1/24 interface=ether2",
            "/ip address add address=192.168.30.1/24 interface=ether3",
        ]

        for cmd in commands:
            print(f"  [SSH] Executing: {cmd}")
            ssh.exec_command(cmd)
            time.sleep(1) # Maža pauzė tarp komandų

        ssh.close()
        print("[OK] MikroTik configured")
    except Exception as e:
        print(f"[ERROR] MikroTik SSH failed: {e}")

# =========================
# Config Functions
# =========================

def configure_ovs(project, node):
    print(f"[INFO] Configuring OVS Switch: {node.name}")
    cmds = [
        "ovs-vsctl add-br br0",
        "for i in 0 1 2 3 4 5 6 7; do ovs-vsctl add-port br0 eth$i; done",
        "ip link set br0 up"
    ]
    for cmd in cmds:
        run_docker_cmd(project.project_id, node.node_id, cmd)

def configure_alpine(project, node):
    name = node.name
    # Logika IP adresų priskyrimui pagal mazgo pavadinimą
    if "1" in name:
        ip, gw = "192.168.10.10", "192.168.10.1"
    elif any(x in name for x in ["2","3","4","5","6","7","8"]):
        try:
            num = int(name.split("-")[-1])
            ip, gw = f"192.168.20.{10 + num}", "192.168.20.1"
        except: ip, gw = "192.168.20.50", "192.168.20.1"
    elif any(x in name for x in ["9","10"]):
        try:
            num = int(name.split("-")[-1])
            ip, gw = f"192.168.30.{10 + num}", "192.168.30.1"
        except: ip, gw = "192.168.30.50", "192.168.30.1"
    else:
        return

    print(f"[INFO] Alpine {name} -> IP: {ip}, GW: {gw}")
    cmds = [
        f"ip addr add {ip}/24 dev eth0",
        "ip link set eth0 up",
        f"ip route add default via {gw}"
    ]
    for cmd in cmds:
        run_docker_cmd(project.project_id, node.node_id, cmd)

# =========================
# Ping Test
# =========================

def ping_test(project, node, target):
    print(f"[PING] Testing {node.name} -> {target}", end=" ")
    result = run_docker_cmd(project.project_id, node.node_id, f"ping -c 3 {target}")
    
    output = str(result.get("output", ""))
    # Tikriname ar pingas pavyko
    if "0% packet loss" in output or "3 packets transmitted, 3 received" in output:
        print("[OK]")
        return True
    else:
        print("[FAIL]")
        return False

# =========================
# MAIN
# =========================

def main():
    connector = Gns3Connector(url=GNS3_URL)
    project = Project(name=PROJECT_NAME, connector=connector)

    try:
        project.get()
        project.get_nodes()
    except Exception as e:
        print(f"[ERROR] Could not find project '{PROJECT_NAME}': {e}")
        return

    print("[INFO] Starting all nodes...")
    for node in project.nodes:
        if node.status != "started":
            node.start()

    if not wait_for_nodes(project):
        print("[ERROR] Nodes failed to start in time")
        return

    print("[INFO] Waiting for OS to boot (15s)...")
    time.sleep(15)

    # Konfigūruojame mazgus
    for node in project.nodes:
        if "Alpine" in node.name:
            configure_alpine(project, node)
        elif any(x in node.name for x in ["Main", "Admin", "Support", "OVS"]):
            configure_ovs(project, node)

    # MikroTik konfigūracija
    mikrotik_ssh_config(GNS3_VM_HOST)

    # Tinklo testai
    print("\n--- STARTING NETWORK TESTS ---")
    nodes_dict = {n.name: n for n in project.nodes}
    
    # Testų vykdymas (tikriname ar mazgai egzistuoja projekte)
    test_cases = [
        ("AlpineLinux-1", "192.168.10.1"),
        ("AlpineLinux-2", "192.168.20.1"),
        ("AlpineLinux-9", "192.168.30.1")
    ]

    for node_name, target_ip in test_cases:
        if node_name in nodes_dict:
            ping_test(project, nodes_dict[node_name], target_ip)

    print("\n[SUCCESS] Pipeline script finished")

if __name__ == "__main__":
    main()
