import sys
import time
from gns3fy import Gns3Connector, Project
from netmiko import ConnectHandler

# --- KONFIGURACIJA ---
GNS3_IP = "192.168.56.102"
PROJECT_NAME = "a"

# Nustatome išvesties koduotę Jenkins aplinkai
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Testavimo planas apimantis 10+ scenarijų pagal tavo topologiją
TEST_PLAN = [
    {
        "from": "AlpineLinux-1", 
        "targets": ["11.0.0.1", "11.0.0.100", "10.0.0.11", "10.1.0.10"]
    },
    {
        "from": "AlpineLinux-2", 
        "targets": ["10.0.0.1", "10.0.0.100", "11.0.0.2", "10.1.0.11"]
    },
    {
        "from": "AlpineLinux-4", 
        "targets": ["10.1.0.1", "10.1.0.100", "11.0.0.2", "10.0.0.12"]
    }
]

def get_params(port):
    return {
        'device_type': 'generic_telnet',
        'host': GNS3_IP,
        'port': port,
        'timeout': 10
    }

def run_extended_tests():
    try:
        server = Gns3Connector(url=f"http://{GNS3_IP}:80")
        project = Project(name=PROJECT_NAME, connector=server)
        project.get()
        project.get_nodes()

        nodes_map = {n.name: n.console for n in project.nodes if n.status == "started"}

        print("\n" + "="*70)
        print(" IŠPLĖSTINIS TINKLO DIAGNOSTIKOS TESTAS (10+ SCENARIJŲ) ")
        print("="*70 + "\n")

        overall_success = True
        test_count = 1

        for test in TEST_PLAN:
            source = test["from"]
            if source not in nodes_map:
                print(f"[!] Mazgas {source} nerastas arba neijungtas.")
                continue

            port = nodes_map[source]
            print(f"[*] TESTUOJAMA IS: {source} (Console: {port})")
            
            try:
                with ConnectHandler(**get_params(port)) as tn:
                    tn.write_channel("\n")
                    time.sleep(1)
                    
                    for target in test["targets"]:
                        print(f"  {test_count}. PING -> {target}: ", end="", flush=True)
                        
                        # Vykdome ping (3 paketai)
                        res = tn.send_command(f"ping -c 3 -W 2 {target}", expect_string=r'[#$]')
                        
                        if "3 packets transmitted, 3 packets received" in res:
                            print("[ OK ]")
                            
                            # Jei ping sekmingas ir taikinys kitame tinkle, darome traceroute
                            if target.split('.')[1] != "11" and "11.0.0" not in target:
                                print(f"     L- TRACE {target}: ", end="", flush=True)
                                trace = tn.send_command(f"traceroute -n -w 1 -q 1 -m 5 {target}", expect_string=r'[#$]')
                                if ".1" in trace:
                                    print("[ MARSRUTAS PER ROUTER ]")
                                else:
                                    print("[ TIESIOGINIS ARBA NEZINOMAS ]")
                        else:
                            print("[ KLAIDA ]")
                            overall_success = False
                        
                        test_count += 1
                    print("-" * 50)
            except Exception as e:
                print(f"  [!] Nepavyko prisijungti prie {source}: {e}")
                overall_success = False

        print("\n" + "="*70)
        if overall_success:
            print(" REZULTATAS: Visi tinklo testai sekmingi! ")
            sys.exit(0)
        else:
            print(" REZULTATAS: Aptikta tinklo pasiekiamumo klaidu! ")
            sys.exit(1)
        print("="*70 + "\n")

    except Exception as e:
        print(f"Kritine klaida vykdant skripta: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_extended_tests()
