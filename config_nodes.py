import paramiko
import time

def configure_mikrotik(ip, user, password, commands):
    try:
        # Sukuriamas SSH klientas
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        print(f"Jungiamasi prie {ip}...")
        client.connect(ip, username=user, password=password, port=22, timeout=10)
        
        # Vykdomos komandos
        for cmd in commands:
            print(f"Vykdoma: {cmd}")
            stdin, stdout, stderr = client.exec_command(cmd)
            time.sleep(1)
            
        print("Konfigūracija baigta sėkmingai.")
        client.close()
    except Exception as e:
        print(f"Klaida: {e}")

if __name__ == "__main__":
    # Tavo GNS3 VM IP (jei naudojamas 'NAT' tinklas mazgui) 
    # Arba tiesioginis mazgo IP, jei jis pasiekiamas iš PC
    NODE_IP = "192.168.56.102" 
    
    # Mikrotik numatytieji duomenys
    USER = "admin"
    PASS = "" 

    # Pavyzdinės komandos (pvz., pakeisti pavadinimą ar nustatyti IP)
    config_commands = [
        "/system identity set name=Jenkins-Controlled-Router",
        "/ip address add address=10.0.0.1/24 interface=ether1"
    ]

    configure_mikrotik(NODE_IP, USER, PASS, config_commands)
