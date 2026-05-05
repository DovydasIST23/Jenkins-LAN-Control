import os
import time
import sys
from gns3fy import Gns3Connector, Project

def main():
    # Paimame nustatymus
    gns3_url = os.environ.get("GNS3_SERVER_URL", "http://192.168.56.102:80")
    project_name = "a"

    try:
        print(f"[INFO] Jungiamasi prie GNS3: {gns3_url}")
        # timeout=15 užtikrina, kad skriptas nenueis į begalinį laukimą
        connector = Gns3Connector(url=gns3_url, timeout=15)
        
        project = Project(name=project_name, connector=connector)
        project.get()
        project.get_nodes()

        print(f"[OK] Projektas rastas: {project.name}")

        # Įjungiame visus mazgus
        for node in project.nodes:
            if node.status != "started":
                print(f"[+] Paleidžiamas mazgas: {node.name}")
                node.start()
            else:
                print(f"[!] Mazgas jau veikia: {node.name}")

        # Palaukiame 5 sek. kol GNS3 atnaujins statusus ir parodome sąrašą
        time.sleep(5)
        project.get_nodes()
        
        print("\n=== GALUTINĖ MAZGŲ BŪSENA ===")
        for n in project.nodes:
            print(f"Mazgas: {n.name} | Statusas: {n.status}")

        print("\n[SUCCESS] Skriptas baigė darbą sėkmingai.")

    except Exception as e:
        print(f"[ERROR] Klaida: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
