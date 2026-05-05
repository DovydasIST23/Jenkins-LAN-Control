import sys
import time
import re
from gns3fy import Gns3Connector, Project
from netmiko import ConnectHandler

# --- KONFIGURACIJA ---
GNS3_IP = "192.168.56.102"
PROJECT_NAME = "a"

# Nustatome mazgų sąrašą PAEILUI (kaip norėjai)
NODE_ORDER = [
    "AlpineLinux-1", "AlpineLinux-2", "AlpineLinux-3", 
    "AlpineLinux-4", "AlpineLinux-5", "Admin", 
    "Support", "Main1", "AlpineRouter"
]

# Pagrindiniai tinklo taikiniai testavimui
TARGET_IPS = ["11.0.0.1", "10.0.0.1", "10.1.0.1", "10.0.0.100", "10.1.0.100"]

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
        
        # Sukuriame žemėlapį iš visų projekto mazgų
        all_nodes = {n.name: n.console for n in project.nodes if n.status == "started"}

        print(f"\n{'='*80}")
        print(f" STRUKTŪRIZUOTAS TINKLO TESTAS (Pagal mazgų seką) ")
        print(f"{'='*80}\n")

        overall_success = True

        # Vykdome testus pagal nustatytą NODE_ORDER seką
        for node_name in NODE_ORDER:
            if node_name not in all_nodes:
                continue
                
            port = all_nodes[node_name]
            print(f"[*] MAZGAS: {node_name:15} | Konsolė: {port}")
            
            try:
                with ConnectHandler(**get_params(port)) as ssh:
                    ssh.write_channel("\n")
                    time.sleep(0.3)

                    for ip in TARGET_IPS:
                        # 1. PING testas
                        ping_res = ssh.send_command(f"ping -c 2 -W 1 {ip}", expect_string=r'[#$]')
                        
                        if "2 received" in ping_res or "2 packets received" in ping_res:
                            # 2. TRACEROUTE (tik jei kelias > 1 hop)
                            trace_res = ssh.send_command(f"traceroute -n -w 1 -q 1 -m 3 {ip}", expect_string=r'[#$]')
                            hops = re.findall(r'\d+\.\d+\.\d+\.\d+', trace_res)
                            
                            # Filtruojame: jei randa tik patį taikinį, vadinasi 1 hop (Direct)
                            # Jei randa daugiau nei 1 IP (pvz. maršrutizatorių ir tada taikinį) - rodom kelią
                            if len(hops) > 1:
                                path = " -> ".join(hops[1:])
                                print(f"  [ OK ] Ping -> {ip:15} | Kelias: {path}")
                            else:
                                print(f"  [ OK ] Ping -> {ip:15} | Kelias: Tiesioginis (1-hop)")
                        else:
                            print(f"  [FAIL] Ping -> {ip:15} | Ryšio nėra")
                            overall_success = False
                            
            except Exception as e:
                print(f"  [!] Nepavyko prisijungti: {e}")
                overall_success = False
            print("-" * 80)

        print(f"\nREZULTATAS: {'✅ VISKAS VEIKIA' if overall_success else '❌ RASTA PROBLEMŲ'}")
        sys.exit(0 if overall_success else 1)

    except Exception as e:
        print(f"Kritinė klaida: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_ordered_diagnostics()
