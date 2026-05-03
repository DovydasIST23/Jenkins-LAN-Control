import requests
import time

# GNS3 Serverio nustatymai
GNS3_URL = "http://192.168.56"
PROJECT_NAME = "Tavo_Projekto_Vardas" # Įrašyk tikslų pavadinimą

def get_ids():
    # Gauname projekto ID
    p_resp = requests.get(f"{GNS3_URL}/projects")
    p_id = [p['project_id'] for p in p_resp.json() if p['name'] == PROJECT_NAME][0]
    
    # Gauname mikrotik-1 ID
    n_resp = requests.get(f"{GNS3_URL}/projects/{p_id}/nodes")
    n_id = [n['node_id'] for n in n_resp.json() if "mikrotik-1" in n['name']][0]
    
    return p_id, n_id

def send_console_command(p_id, n_id, command):
    # Siunčiame tekstą tiesiai į įrenginio konsolę
    url = f"{GNS3_URL}/projects/{p_id}/nodes/{n_id}/console"
    # Pridedame \r\n, kad emuliuotume "Enter" paspaudimą
    requests.post(url, data=f"{command}\r\n".encode('ascii'))
    print(f"Išsiųsta: {command}")
    time.sleep(1)

def run_config():
    try:
        p_id, n_id = get_ids()
        print(f"Rastas Projektas: {p_id}, Mazgas: {n_id}")

        # Mikrotik konfigūravimas per konsolę (be slaptažodžio, jei naujas)
        commands = [
            "/system identity set name=Jenkins-Router",
            "/ip address add address=192.168.1.1/24 interface=ether2",
            "/ip address add address=192.168.2.1/24 interface=ether3"
        ]

        for cmd in commands:
            send_console_command(p_id, n_id, cmd)

        print("Konfigūracija baigta!")
    except Exception as e:
        print(f"Klaida: {e}")

if __name__ == "__main__":
    run_config()
