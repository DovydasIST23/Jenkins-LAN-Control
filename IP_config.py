import os
import time
import sys
import paramiko
from gns3fy import Gns3Connector, Project

# Išjungiame buferizavimą Jenkins konsolei
sys.stdout.reconfigure(line_buffering=True)

# -------------------------
# KONFIGŪRACIJA
# -------------------------
GNS3_URL = os.environ.get("GNS3_SERVER_URL", "http://192.168.56.102:80")
PROJECT_NAME = "a"

GNS3_VM_HOST = "192.168.56.102"
GNS3_VM_USER = "gns3"
GNS3_VM_PASS = "gns3"

# -------------------------
# IP PLANAS
# -------------------------
def get_ip_plan():
    return {
        "AlpineLinux-1": ("11.0.0.2",  "11.0.0.1"),
        "AlpineLinux-2": ("10.0.0.11", "10.0.0.1"),
        "AlpineLinux-3": ("10.0.0.12", "10.0.0.1"),
        "AlpineLinux-8": ("10.1.0.10", "10.1.0.1"),
        "AlpineLinux-9": ("10.1.0.11", "10.1.0.1"),
        "AlpineLinux-10": ("10.2.0.10", "10.2.0.1")
    }

# -------------------------
# PAGALBINĖS SSH FUNKCIJOS
# -------------------------
def ssh_connect():
    print(f"[INFO] Jungiamasi prie GNS3 VM per SSH ({GNS3_VM_HOST})...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(GNS3_VM_HOST, username=GNS3_VM_USER, password=GNS3_VM_PASS)
    return ssh

def ssh_exec(ssh, cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if out: print(out)
    if err: print(f"[ERR] {err}")
    return out

# -------------------------
# KONFIGŪRAVIMAS
# -------------------------
def configure_alpine(project, ssh):
    print("\n[INFO] Konfigūruojami Alpine konteineriai...")
    ip_plan = get_ip_plan()
    
    for node in project.nodes:
        if node.node_type == "docker" and node.name in ip_plan:
            ip, gw = ip_plan[node.name]
            
            # Gauname Docker ID pagal GNS3 Node ID
            container_id = ssh_exec(ssh, f'docker ps --filter "label=com.gns3.node.id={node.node_id}" --format "{{{{.ID}}}}"')
            
            if not container_id:
                print(f"[ERROR] Nerastas konteineris mazgui {node.name}")
                continue

            cmd = f'docker exec {container_id} sh -c "ip addr flush dev eth0; ip addr add {ip}/24 dev eth0; ip link set eth0 up; ip route add default via {gw}"'
            print(f"[CFG] {node.name} -> {ip}")
            ssh_exec(ssh, cmd)

def configure_mikrotik(ssh):
    print("\n[INFO] Konfigūruojamas MikroTik...")
    # Ieškome MikroTik screen sesijos
    screens = ssh_exec(ssh, "screen -ls")
    
    session_name = None
    for line in screens.splitlines():
        if "mikrotik" in line.lower():
            session_name = line.strip().split("\t")[0]
            break

    if not session_name:
        print("[ERROR] MikroTik sesija nerasta per 'screen -ls'")
        return

    print(f"[OK] Rasta sesija: {session_name}")
    
    commands = [
        "/ip address add address=11.0.0.1/24 interface=ether1",
        "/ip address add address=10.0.0.1/24 interface=ether2",
        "/ip address add address=10.1.0.1/24 interface=ether3",
        "/ip address add address=10.2.0.1/24 interface=ether4"
    ]

    for cmd in commands:
        # Siunčiame komandas į screen sesiją
        full_cmd = f'screen -S {session_name} -X stuff "{cmd}\\r"'
        ssh_exec(ssh, full_cmd)
        time.sleep(1)

def start_nodes(project):
    print("[INFO] Mazgų paleidimas...")
    project.get_nodes()
    for node in project.nodes:
        if node.status != "started":
            print(f"  -> Paleidžiamas {node.name}")
            node.start()
    
    # Laukiame kol visi pasileis
    for _ in range(30):
        project.get_nodes()
        if all(n.status == "started" for n in project.nodes):
            print("[OK] Visi mazgai paruošti.")
            return True
        time.sleep(2)
    return False

# -------------------------
# PAGRINDINIS
# -------------------------
def main():
    try:
        print(f"[INFO] Pradedama GNS3 automatizacija: {GNS3_URL}")
        connector = Gns3Connector(url=GNS3_URL)
        project = Project(name=PROJECT_NAME, connector=connector)
        project.get()

        if not start_nodes(project):
            print("[ERROR] Nepavyko paleisti visų mazgų.")
            sys.exit(1)

        # SSH operacijos
        ssh = ssh_connect()
        
        # 1. Alpine konfigūravimas
        configure_alpine(project, ssh)
        
        # 2. Trumpa pauzė prieš MikroTik
        time.sleep(5)
        
        # 3. MikroTik konfigūravimas
        configure_mikrotik(ssh)
        
        ssh.close()
        print("\n[SUCCESS] TINKLO KONFIGŪRAVIMAS BAIGTAS")

    except Exception as e:
        print(f"\n[CRITICAL ERROR] {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
