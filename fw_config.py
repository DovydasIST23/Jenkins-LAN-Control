def apply_route_blocking(port):
    """Blokuoja ryšius ištrindamas maršrutus (be iptables)."""
    print(f"\n[*] Jungiamasi prie AlpineRouter (port: {port})...")
    
    try:
        with ConnectHandler(**get_params(port)) as tn:
            tn.write_channel("\n")
            time.sleep(1)
            
            # Norint blokuoti ryšį tarp Admin, Main ir Support,
            # tiesiog laikinai pašaliname maršrutus į tuos tinklus
            # arba išjungiame konkrečias sąsajas (eth0, eth1, eth2).
            
            print("[*] Vykdomas fizinis sąsajų blokavimas...")
            cmds = [
                # Išjungia sąsajas - tai 100% nutraukia ryšį
                "ip link set eth0 down", # Blokuoja Main
                "ip link set eth1 down", # Blokuoja Admin
                "ip link set eth2 down"  # Blokuoja Support
            ]
            
            for cmd in cmds:
                tn.send_command(cmd, expect_string=r'[#$]')
                print(f"Vykdoma: {cmd}")
            
            print("\n>>> TINKLAI IZOLIUOTI: Sąsajos išjungtos.")
            
    except Exception as e:
        print(f"Klaida: {e}")
