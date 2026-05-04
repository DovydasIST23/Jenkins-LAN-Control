import sys
import time
from gns3fy import Gns3Connector, Project
from netmiko import ConnectHandler

# Nustatymai
GNS3_IP = "192.168.56.102"
PROJECT_NAME = "a"

# IP Planas: (IP_adresas, Gateway)
IP_PLAN = {
    "AlpineLinux-1": ("11.0.0.2",  "11.0.0.1"),
    "AlpineLinux-2": ("10.0.0.11", "10.0.0.1"),
    "AlpineLinux-3": ("10.0.0.12", "10.0.0.1"),
    "AlpineLinux-4": ("10.1.0.10", "10.1.0.1"),
    "AlpineLinux-5": ("10.1.0.11", "10.1.0.1")
}

def configure_node(node_name, console_port, ip, gw):
    """Konfigūruoja mazgą per Telnet naudojant netmiko."""
    device_params = {
        'device_type': 'generic_telnet',
        'host': GNS3_IP,
        'port': console_port,
        'timeout': 10,
    }
    
    print(f"\n[PROCESS] Jungiamasi prie {node_name} (Port: {console_port})...")
    
    try:
        # Prisijungiame
        net_connect = ConnectHandler(**device_params)
        
        # Alpine Linux konsolėje kartais reikia paspausti Enter, kad pamatytume promptą
        net_connect.write_channel("\n")
        time.sleep(1)
        
        commands = [
            "ip addr flush dev eth0",
            f"ip addr add {ip}/24 dev eth0",
            "ip link set eth0 up",
            f"ip route add default via {gw}"
        ]
        
        for cmd in commands:
            # Siunčiame komandą ir laukiame rezultato
            output = net_connect.send_command(cmd, expect_string=r'[#$]')
            print(f"  -> [OK] {cmd}")
            
        net_connect.disconnect()
        return True
    except Exception as e:
        print(f"  -> [!] Klaida konfigūruojant {node_name}: {e}")
        return False

def main():
    # Užtikriname, kad Jenkins matytų printus iškart
    sys.stdout.reconfigure(line_buffering=True)
    
    error_count = 0
    success_count = 0
    
    try:
        server_url = f"http://{GNS3_IP}:80"
        print(f"[INFO] Jungiamasi prie GNS3 API: {server_url}")
        
        server = Gns3Connector(url=server_url)
        project = Project(name=PROJECT_NAME, connector=server)
        project.get()
        project.get_nodes()

        for node in project.nodes:
            if node.name in IP_PLAN:
                if node.status != "started":
                    print(f"[WARN] Mazgas {node.name} neaktyvus (išjungtas). Praleidžiama.")
                    continue

                ip, gw = IP_PLAN[node.name]
                # Gauname konsolės portą iš GNS3 API
                console_port = node.console
                
                if console_port is None:
                    print(f"[!] Mazgas {node.name} neturi konsolės porto!")
                    error_count += 1
                    continue

                if configure_node(node.name, console_port, ip, gw):
                    success_count += 1
                else:
                    error_count += 1

        print(f"\n--- ATASKAITA ---")
        print(f"Sėkmingai sukonfigūruota: {success_count}")
        print(f"Klaidos: {error_count}")

        if error_count > 0:
            sys.exit(1)
            
    except Exception as e:
        print(f"\n[ERROR] Kritinė klaida: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
