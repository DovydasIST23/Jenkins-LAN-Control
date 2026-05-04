import sys
import time
from gns3fy import Gns3Connector, Project
from netmiko import ConnectHandler

# --- KONFIGŪRACIJA ---
GNS3_IP = "192.168.56.102"
PROJECT_NAME = "a"

def get_params(port):
    return {
        'device_type': 'generic_telnet',
        'host': GNS3_IP,
        'port': port,
        'timeout': 10,
    }

def fix_main1_ovs(port):
    """
    Išvalo senas konfigūracijas ir sukuria vieną bendrą tiltą.
    """
    print(f"\n[OVS] Atliekamas Main1 pilnas perkrovimas...")
    try:
        with ConnectHandler(**get_params(port)) as tn:
            tn.write_channel("\n")
            time.sleep(1)
            
            # 1. Identifikuojame ir ištriname VISUS esamus tiltus, 
            # kad išlaisvintume eth sąsajas.
            cleanup_cmds = [
                "ovs-vsctl del-br br-lan",
                "ovs-vsctl del-br br0",
                "ovs-vsctl del-br br1",
                "ovs-vsctl del-br br2",
                "ovs-vsctl del-br br3"
            ]
            
            # 2. Sukuriame vieną naują tiltą
            setup_cmds = [
                "ovs-vsctl add-br br-final",
                "ovs-vsctl set bridge br-final protocols=OpenFlow10,OpenFlow13"
            ]
            
            # 3. Prijungiame sąsajas (eth0-eth3) prie naujo tilto.
            for i in range(4):
                setup_cmds.append(f"ovs-vsctl add-port br-final eth{i}")
                setup_cmds.append(f"ip link set eth{i} up")
            
            setup_cmds.append("ip link set br-final up")
            
            # Vykdymas
            for cmd in cleanup_cmds + setup_cmds:
                output = tn.send_command(cmd, expect_string=r'[#$]')
                print(f"    -> {cmd} {output}")
                
        print("[OVS] Main1 sėkmingai perkonfigūruotas.")
        return True
    except Exception as e:
        print(f"    -> [!] Klaida: {e}")
        return False

# Paleidimo logika lieka tokia pati
def main():
    sys.stdout.reconfigure(line_buffering=True)
    try:
        server = Gns3Connector(url=f"http://{GNS3_IP}:80")
        project = Project(name=PROJECT_NAME, connector=server)
        project.get()
        project.get_nodes()

        for node in project.nodes:
            if node.name == "Main1" and node.status == "started":
                fix_main1_ovs(node.console)

        print("\n[FINISH] OVS išvalytas ir sujungtas. Bandykite ping dabar.")
    except Exception as e:
        print(f"Klaida: {e}")

if __name__ == "__main__":
    main()
