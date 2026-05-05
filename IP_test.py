import sys
import time
import re
from gns3fy import Gns3Connector, Project
from netmiko import ConnectHandler

# --- KONFIGURACIJA ---
GNS3_IP = "192.168.56.102"
PROJECT_NAME = "a"

# UTF-8 palaikymas Jenkins/Console
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def get_params(port):
    return {
        'device_type': 'generic_telnet',
        'host': GNS3_IP,
        'port': port,
        'timeout': 5,
        'fast_cli': True
    }

def run_diagnostics():
    try:
        server = Gns3Connector(url=f"http://{GNS3_IP}:80")
        project = Project(name=PROJECT_NAME, connector=server)
        project.get()
        
        # Surandame visus veikiančius mazgus iš tavo topologijos
        nodes = {n.name: n.console for n in project.nodes if n.status == "started"}
        
        # Tikslinis IP sąrašas testavimui (pagal tavo schemas)
        # Pridėk čia visus IP, kuriuos tavo tinklas turi pasiekti
        target_ips = ["11.0.0.1", "10.0.0.1", "10.1.0.1", "10.0.0.100", "10.1.0.100"]

        print(f"\n{'='*75}")
        print(f" TINKLO AUTOMATINIS TESTAVIMAS: {PROJECT_NAME.upper()} ")
        print(f"{'='*75}\n")

        overall_success = True

        for node_name, port in nodes.items():
            print(f"[*] Jungiamasi prie: {node_name:15} (Port: {port})")
            
            try:
                with ConnectHandler(**get_params(port)) as ssh:
                    ssh.write_channel("\n")
                    time.sleep(0.5)

                    # Kiekvienam mazgui testuojame kelis IP
                    for ip in target_ips:
                        # PING (tik 2 paketai, kad būtų greitai)
                        res = ssh.send_command(f"ping -c 2 -W 1 {ip}", expect_string=r'[#$]')
                        
                        if "2 received" in res or "2 packets received" in res:
                            # TRACEROUTE (tik jei reikia vizualizuoti kelią per routerį)
                            # Darome tik jei IP nėra tame pačiame potinklyje (supaprastinta logika)
                            trace_info = ""
                            if "10." in ip:
                                trace_res = ssh.send_command(f"traceroute -n -w 1 -q 1 -m 4 {ip}", expect_string=r'[#$]')
                                hops = re.findall(r'\d+\.\d+\.\d+\.\d+', trace_res)
                                if len(hops) > 1:
                                    path = " -> ".join(hops[1:])
                                    trace_info = f" | PATH: {path}"

                            print(f"  [ OK ] Ping -> {ip:15}{trace_info}")
                        else:
                            print(f"  [FAIL] Ping -> {ip:15}")
                            overall_success = False
                            
            except Exception as e:
                print(f"  [!] Klaida su mazgu {node_name}: {e}")
                overall_success = False
            print("-" * 75)

        print(f"\nGALUTINIS REZULTATAS: {'✅ SĖKMĖ' if overall_success else '❌ KLAIDA'}")
        sys.exit(0 if overall_success else 1)

    except Exception as e:
        print(f"KRITINĖ KLAIDA: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_diagnostics()
