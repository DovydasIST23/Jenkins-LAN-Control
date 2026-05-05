import sys
import time
from gns3fy import Gns3Connector, Project
from netmiko import ConnectHandler

# --- KONFIGURACIJA ---
GNS3_IP = "192.168.56.102"
PROJECT_NAME = "a"

# Užtikriname UTF-8 išvestį Jenkins aplinkai
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# PILNAS TESTAVIMO PLANAS (Visi mazgai ir switch IP)
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
        "from": "AlpineLinux-3", 
        "targets": ["10.0.0.1", "10.0.0.12", "11.0.0.2"]
    },
    {
        "from": "AlpineLinux-4", 
        "targets": ["10.1.0.1", "10.1.0.100", "11.0.0.2", "10.0.0.11"]
    },
    {
        "from": "AlpineLinux-5", 
        "targets": ["10.1.0.1", "10.1.0.11", "11.0.0.2"]
    },
    {
        "from": "AlpineRouter", 
        "targets": ["11.0.0.2", "10.0.0.11", "10.1.0.10", "11.0.0.100"]
    }
]

def get_params(port):
    return {
        'device_type': 'generic_telnet',
        'host': GNS3_IP,
        'port': port,
        'timeout': 15,
        'fast_cli': False
    }

def run_diagnostics():
    try:
        server = Gns3Connector(url=f"http://{GNS3_IP}:80")
        project = Project(name=PROJECT_NAME, connector=server)
        project.get()
        project.get_nodes()

        nodes_map = {n.name: n.console for n in project.nodes if n.status == "started"}

        print("\n" + "="*80)
        print("   VISUOTINIS TINKLO TESTAVIMAS: PING & TRACEROUTE (REAL-TIME CONSOLE)")
        print("="*80 + "\n")

        overall_errors = 0

        for test in TEST_PLAN:
            source = test["from"]
            if source not in nodes_map:
                print(f"[!] Mazgas {source} nerastas arba neijungtas. Praleidziama.")
                continue

            port = nodes_map[source]
            print(f"\n>>> PRISIJUNGTA PRIE: {source} (Port: {port})")
            
            try:
                with ConnectHandler(**get_params(port)) as tn:
                    # Isvalome terminala pries pradedant
                    tn.write_channel("\n")
                    time.sleep(0.5)
                    
                    for target in test["targets"]:
                        if not target: continue
                        
                        print(f"\n[ TESTAS ] {source} # ping -c 3 {target}")
                        # Siunciame komanda ir iskart spausdiname rezultata
                        ping_output = tn.send_command(f"ping -c 3 -W 2 {target}", expect_string=r'[#$]')
                        print(ping_output)
                        
                        if "3 packets transmitted, 3 packets received" not in ping_output:
                            overall_errors += 1

                        # Traceroute vykdome tik tarp skirtingu potinkliu (pvz. is 11 i 10)
                        if target.split('.')[0] == "10" or (source == "AlpineLinux-4" and "11." in target):
                            print(f"\n[ TESTAS ] {source} # traceroute -n {target}")
                            trace_output = tn.send_command(f"traceroute -n -w 1 -q 1 -m 8 {target}", expect_string=r'[#$]')
                            print(trace_output)
                        
                    print("\n" + "-" * 60)
            except Exception as e:
                print(f"  [ KLAIDA ] Nepavyko atlikti testu is {source}: {e}")
                overall_errors += 1

        print("\n" + "="*80)
        if overall_errors == 0:
            print(" GALUTINIS REZULTATAS: ✅ Visi tinklo mazgai pasiekiami! ")
            sys.exit(0)
        else:
            print(f" GALUTINIS REZULTATAS: ❌ Aptikta {overall_errors} rysio klaidu! ")
            sys.exit(1)

    except Exception as e:
        print(f"Kritine skripto klaida: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_diagnostics()
