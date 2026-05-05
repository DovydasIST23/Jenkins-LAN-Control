import time
from gns3fy import Gns3Connector, Project
from netmiko import ConnectHandler

# --- KONFIGURACIJA ---
GNS3_IP = "192.168.56.102"
PROJECT_NAME = "a"

# Išplėstas testų planas (10 scenarijų)
# Tikriname: vietinį ryšį, gateway, kitus tinklus ir switchų valdymą
TEST_PLAN = [
    # Iš AlpineLinux-1 (Admin tinklas)
    {"from": "AlpineLinux-1", "targets": ["11.0.0.1", "11.0.0.100", "10.0.0.11", "10.1.0.10"]},
    # Iš AlpineLinux-2 (Main tinklas)
    {"from": "AlpineLinux-2", "targets": ["10.0.0.1", "10.0.0.100", "11.0.0.2", "10.1.0.11"]},
    # Iš AlpineLinux-4 (Support tinklas)
    {"from": "AlpineLinux-4", "targets": ["10.1.0.1", "10.1.0.100", "10.0.0.12"]},
    # Iš AlpineRouter (Tikriname visas puses)
    {"from": "AlpineRouter", "targets": ["11.0.0.2", "10.0.0.11", "10.1.0.10"]}
]

def get_params(port):
    return {'device_type': 'generic_telnet', 'host': GNS3_IP, 'port': port, 'timeout': 10}

def run_extended_tests():
    server = Gns3Connector(url=f"http://{GNS3_IP}:80")
    project = Project(name=PROJECT_NAME, connector=server)
    project.get()
    project.get_nodes()

    nodes_map = {n.name: n.console for n in project.nodes if n.status == "started"}

    print(f"\n{'='*70}")
    print(f" IŠPLĖSTINIS TINKLO DIAGNOSTIKOS TESTAS (10+ SCENARIJŲ) ")
    print(f"{'='*70}\n")

    test_count = 0
    success_count = 0

    for test in TEST_PLAN:
        source_name = test["from"]
        if source_name not in nodes_map:
            print(f"[!] Mazgas {source_name} neaktyvus, praleidžiama.")
            continue
        
        port = nodes_map[source_name]
        try:
            with ConnectHandler(**get_params(port)) as tn:
                tn.write_channel("\n")
                print(f"[*] TESTUOJAMA IŠ: {source_name}")
                
                for target in test["targets"]:
                    test_count += 1
                    print(f"  {test_count}. PING -> {target}: ", end="", flush=True)
                    
                    # -c 2 pakanka greitam testui, -W 1 laukia 1 sek.
                    output = tn.send_command(f"ping -c 2 -W 1 {target}", expect_string=r'[#$]')
                    
                    if "2 packets transmitted, 2 packets received" in output:
                        print("✅ OK")
                        success_count += 1
                        
                        # Jei tai tarp-tinklinis ping, darom traceroute
                        if target.split('.')[1] != "11" and "11.0.0" not in target: # Labai paprasta logika
                            print(f"     └─ TRACE: ", end="", flush=True)
                            trace = tn.send_command(f"traceroute -n -w 1 -q 1 -m 5 {target}", expect_string=r'[#$]')
                            if ".1" in trace: # Tikriname ar matosi gateway .1 šuolis
                                print("✅ MARŠRUTAS TEISINGAS (per Gateway)")
                            else:
                                print("ℹ️ VIETINIS TINKLAS")
                    else:
                        print("❌ KLAIDA (No Reply)")
                print("-" * 50)
        except Exception as e:
            print(f"⚠️ Nepavyko prisijungti prie {source_name}: {e}")

    print(f"\n{'='*70}")
    print(f" REZULTATAI: Sėkmingi {success_count} iš {test_count} testų. ")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    run_extended_tests()
