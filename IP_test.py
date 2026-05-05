import sys
import time
import re
from gns3fy import Gns3Connector, Project
from netmiko import ConnectHandler

# --- KONFIGURACIJA ---
GNS3_IP = "192.168.56.102"
PROJECT_NAME = "a"

# Mazgų sąrašas paeiliui
NODE_ORDER = [
    "AlpineLinux-1", "AlpineLinux-2", "AlpineLinux-3", 
    "AlpineLinux-4", "AlpineLinux-5", "Admin", 
    "Support", "Main1", "AlpineRouter"
]

TARGET_IPS = ["11.0.0.1", "10.0.0.1", "10.1.0.1", "10.0.0.100", "10.1.0.100", "11.0.0.1", "10.0.0.11", "10.1.0.11", "10.0.0.12"]

def get_params(port):
    return {
        'device_type': 'generic_telnet',
        'host': GNS3_IP,
        'port': port,
        'timeout': 5,
        'fast_cli': True
    }

def run_ordered_diagnostics():
    try:
        server = Gns3Connector(url=f"http://{GNS3_IP}:80")
        project = Project(name=PROJECT_NAME, connector=server)
        project.get()
        
        all_nodes = {n.name: n.console for n in project.nodes if n.status == "started"}

        # Naudojame paprastus brūkšnius vietoj specialių rėmelių dėl Jenkins suderinamumo
        print("\n" + "="*80)
        print(" STRUKTURIZUOTAS TINKLO TESTAS ")
        print("="*80 + "\n")

        overall_success = True

        for node_name in NODE_ORDER:
            if node_name not in all_nodes:
                continue
                
            port = all_nodes[node_name]
            print(f"[*] MAZGAS: {node_name:15} | Konsole: {port}")
            
            try:
                with ConnectHandler(**get_params(port)) as ssh:
                    ssh.write_channel("\n")
                    time.sleep(0.3)

                    for ip in TARGET_IPS:
                        ping_res = ssh.send_command(f"ping -c 2 -W 1 {ip}", expect_string=r'[#$]')
                        
                        if "2 received" in ping_res or "2 packets received" in ping_res:
                            # Atliekame traceroute
                            trace_res = ssh.send_command(f"traceroute -n -w 1 -q 1 -m 3 {ip}", expect_string=r'[#$]')
                            # Ištraukiame visus IP iš traceroute (išskyrus pirmą eilutę su komanda)
                            hops = re.findall(r'^\s*\d+\s+(\d+\.\d+\.\d+\.\d+)', trace_res, re.MULTILINE)
                            
                            # Jei hops sąrašas tuščias arba yra tik 1 hopas, kuris sutampa su target IP
                            if not hops or (len(hops) == 1 and hops[0] == ip):
                                print(f"  [ OK ] Ping -> {ip:15} | Kelias: Tiesioginis (1-hop)")
                            else:
                                path = " -> ".join(hops)
                                print(f"  [ OK ] Ping -> {ip:15} | Kelias: {path}")
                        else:
                            print(f"  [FAIL] Ping -> {ip:15} | Rysio nera")
                            overall_success = False
                            
            except Exception as e:
                print(f"  [!] Klaida jungiantis prie {node_name}")
                overall_success = False
            print("-" * 80)

        # PAŠALINTI EMODŽI: Naudojame tik tekstą
        if overall_success:
            print("\nREZULTATAS: SEKMINGA (Visi tinklo mazgai pasiekiami)")
            sys.exit(0)
        else:
            print("\nREZULTATAS: KLAIDA (Aptikta nepasiekiamu mazgu)")
            sys.exit(1)

    except Exception as e:
        print(f"Sistemine klaida: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_ordered_diagnostics()
