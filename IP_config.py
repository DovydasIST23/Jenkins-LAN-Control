import os
import time
import sys
import paramiko
from gns3fy import Gns3Connector, Project

# Priverčiame Python iškart spausdinti tekstą (kad Jenkins nelygintų)
sys.stdout.reconfigure(line_buffering=True)

GNS3_URL = os.environ.get("GNS3_SERVER_URL", "http://192.168.56.102:80")
PROJECT_NAME = "a"

def main():
    try:
        print(f"[INFO] Jungiamasi prie GNS3 API: {GNS3_URL}")
        connector = Gns3Connector(url=GNS3_URL)
        project = Project(name=PROJECT_NAME, connector=connector)
        project.get()
        project.get_nodes()

        print(f"[OK] Projektas įkeltas: {project.name}")

        # 1. Paleidžiame mazgus
        if not start_nodes(project):
            print("[WARN] Ne visi mazgai pasileido laiku.")

        # 2. Palaukiame, kol OS viduje užsikraus servisai
        print("[INFO] Laukiama 5s sistemos stabilizavimo...")
        time.sleep(5)

        # 3. Konfigūruojame tinklą ir SSH
        configure_alpine_and_ssh(project)
        configure_ovs_switches(project)

        print("\n[SUCCESS] TINKLAS SUKONFIGŪRUOTAS!")

    except Exception as e:
        print(f"\n[CRITICAL ERROR] {e}")
        sys.exit(1)

def generate_ip_config():
    config = {}
    for i in range(2, 8):
        config[f"AlpineLinux-{i}"] = (f"10.0.0.{9+i}", "10.0.0.1")
    config["AlpineLinux-1"] = ("11.0.0.1", "11.0.0.1")
    config["AlpineLinux-8"] = ("10.1.0.10", "10.1.0.1")
    config["AlpineLinux-9"] = ("10.1.0.11", "10.1.0.1")
    config["AlpineLinux-10"] = ("10.2.0.10", "10.2.0.1")
    return config

def start_nodes(project):
    print("[INFO] Mazgų būsenos patikra...")
    for node in project.nodes:
        if node.status != "started":
            print(f"[START] Paleidžiamas {node.name}...")
            node.start()
    
    for i in range(15):
        project.get_nodes()
        not_ready = [n.name for n in project.nodes if n.status != "started"]
        if not not_ready:
            print("[OK] Visi mazgai veikia.")
            return True
        print(f"[WAIT] Dar kraunasi ({i}/15): {not_ready}")
        time.sleep(2)
    return False

def configure_alpine_and_ssh(project):
    print("\n[INFO] Alpine konfigūravimas (IP + SSH)...")
    config = generate_ip_config()

    for node in project.nodes:
        if node.node_type == "docker" and node.name in config:
            ip, gw = config[node.name]
            
            # IP nustatymas + SSH instaliavimas/paleidimas vienu ypu
            # Pastaba: Alpine turi turėti internetą, kad 'apk add' veiktų, 
            # arba SSH turi būti atvaizde (image).
            commands = (
                f"ip addr flush dev eth0; "
                f"ip addr add {ip}/24 dev eth0; "
                f"ip link set eth0 up; "
                f"ip route add default via {gw}; "
                f"echo 'root:root' | chpasswd; " # Nustatome slaptažodį Paramiko
                f"apk add --no-cache openssh; " # Instaliuojame SSH (jei nėra)
                f"ssh-keygen -A; /usr/sbin/sshd" # Generuojame raktus ir paleidžiame
            )
            
            cmd = f"sh -c '{commands}'"
            print(f"[CFG] {node.name} -> IP: {ip}")
            try:
                node.run_executable(cmd)
            except Exception as e:
                print(f"[ERR] Nepavyko sukonfigūruoti {node.name}: {e}")

def configure_ovs_switches(project):
    print("\n[INFO] OVS Switch konfigūravimas...")
    switch_names = ["Main1", "Support", "Admin", "Admin-IT", "Main"]
    for node in project.nodes:
        if node.name in switch_names:
            cmd = "sh -c 'ovs-vsctl --if-exists del-br br0; ovs-vsctl add-br br0; " \
                  "for iface in $(ls /sys/class/net | grep eth); do ovs-vsctl --may-exist add-port br0 $iface; " \
                  "ip link set $iface up; done; ip link set br0 up'"
            try:
                print(f"[CFG] OVS {node.name}")
                node.run_executable(cmd)
            except:
                print(f"[WARN] {node.name} API komanda nepraėjo (galbūt switch tipas nepalaiko)")

if __name__ == "__main__":
    main()
