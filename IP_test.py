import sys, time
from gns3fy import Gns3Connector, Project
from netmiko import ConnectHandler

GNS3_IP, PROJ_NAME = "192.168.56.102", "a"

if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Sutankintas planas: [Iš kur] -> [Taikiniai]
PLAN = {
    "AlpineLinux-1": ["11.0.0.1", "11.0.0.100", "10.0.0.11", "10.1.0.10"],
    "AlpineLinux-2": ["10.0.0.1", "10.0.0.100", "11.0.0.2"],
    "AlpineLinux-3": ["10.0.0.1", "10.0.0.12"],
    "AlpineLinux-4": ["10.1.0.1", "10.1.0.100", "11.0.0.2"],
    "AlpineLinux-5": ["10.1.0.1", "10.1.0.11"],
    "AlpineRouter":  ["11.0.0.2", "10.0.0.11", "10.1.0.10"]
}

def run_tests():
    try:
        server = Gns3Connector(url=f"http://{GNS3_IP}:80")
        nodes = {n.name: n.console for n in Project(name=PROJ_NAME, connector=server).get_nodes() if n.status == "started"}
        
        errs = 0
        print(f"\n{'='*50}\n TINKLO PATIKRA: {time.strftime('%H:%M:%S')}\n{'='*50}")

        for src, targets in PLAN.items():
            if src not in nodes: continue
            print(f"\n[HOST: {src}]")
            try:
                with ConnectHandler(device_type='generic_telnet', host=GNS3_IP, port=nodes[src], timeout=10) as tn:
                    for target in targets:
                        # Trumpas ping (2 paketai taupant laiką)
                        out = tn.send_command(f"ping -c 2 -W 1 {target}", expect_string=r'[#$]')
                        ok = "2 packets transmitted, 2 packets received" in out
                        status = "[ OK ]" if ok else "[ FAIL ]"
                        print(f"  -> {target.ljust(15)} {status}")
                        
                        if not ok: errs += 1
                        
                        # Traceroute tik jei kirtome routerį
                        if ok and target.split('.')[1] != src.split('-')[-1]: 
                            tr = tn.send_command(f"traceroute -n -w 1 -q 1 -m 5 {target}", expect_string=r'[#$]')
                            hops = tr.strip().split('\n')[1:]
                            print(f"     Trace: {' -> '.join([h.split()[1] for h in hops if len(h.split())>1])}")
            except Exception as e:
                print(f"  !! Connection error: {e}")
                errs += 1

        print(f"\n{'='*50}\nREZULTATAS: {'KLAIDOS: ' + str(errs) if errs else 'VISKAS OK'}\n{'='*50}")
        sys.exit(1 if errs else 0)
    except Exception as e:
        print(f"Fatal: {e}"); sys.exit(1)

if __name__ == "__main__":
    run_tests()
