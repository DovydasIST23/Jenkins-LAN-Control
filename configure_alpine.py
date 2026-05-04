import time
from netmiko import ConnectHandler

# Konfigūracija
GNS3_IP = "192.168.56.102"
ADMIN_PORT = 5020  # Admin OVS konsolės portas
ALPINE1_PORT = 5003 # AlpineLinux-1 konsolės portas (patikrinkite GNS3)

def get_params(port):
    return {
        'device_type': 'generic_telnet',
        'host': GNS3_IP,
        'port': port,
        'timeout': 15,
    }

def fix_admin_ovs():
    print("\n[OVS] Admin mazgo tvarkymas...")
    try:
        with ConnectHandler(**get_params(ADMIN_PORT)) as tn:
            # 1. Išvalome visus senus tiltus, kurie gali blokuoti eth sąsajas
            tn.send_command("ovs-vsctl --if-exists del-br br-lan")
            tn.send_command("ovs-vsctl --if-exists del-br br-final")
            
            # 2. Sukuriame naują švarų tiltą
            tn.send_command("ovs-vsctl add-br br-final")
            tn.send_command("ovs-vsctl set-fail-mode br-final standalone")
            
            # 3. Prijungiame visus fizinius portus prie br-final
            # Svarbu: eth3 (į MikroTik) ir eth0 (į Alpine1) turi būti čia
            for i in range(4):
                tn.send_command(f"ovs-vsctl add-port br-final eth{i}")
                tn.send_command(f"ip link set eth{i} up")
            
            # 4. Priskiriame IP pačiam Admin jungikliui
            tn.send_command("ip link set br-final up")
            tn.send_command("ip addr add 11.0.0.100/24 dev br-final")
            
            # 5. Leidžiame visą srautą
            tn.send_command("ovs-ofctl add-flow br-final action=normal")
            print("✅ Admin OVS sukonfigūruotas.")
    except Exception as e:
        print(f"❌ Admin klaida: {e}")

def fix_alpine1():
    print("\n[ALPINE] AlpineLinux-1 IP nustatymas...")
    try:
        with ConnectHandler(**get_params(ALPINE1_PORT)) as tn:
            tn.send_command("ip link set eth0 up")
            tn.send_command("ip addr flush dev eth0")
            tn.send_command("ip addr add 11.0.0.2/24 dev eth0")
            tn.send_command("ip route add default via 11.0.0.1")
            print("✅ AlpineLinux-1 IP nustatytas: 11.0.0.2")
    except Exception as e:
        print(f"❌ Alpine1 klaida: {e}")

if __name__ == "__main__":
    fix_admin_ovs()
    fix_alpine1()
