import json
import time
from INA219 import INA219

# Chargement config
with open("/home/thomas/hechicero/data/config.json", "r") as f:
    config = json.load(f)

ina = INA219(addr=0x43)

def run_loop():
    while True:
        try:
            bus_voltage = ina.getBusVoltage_V()
            current_ma = -ina.getCurrent_mA()
            p = max(0, min(100, int((bus_voltage - 3.0) / 1.2 * 100)))
            
            etat = "En charge ⚡" if current_ma > config["charge_threshold_ma"] else "Sur batterie 🔋"
            couleur = "green" if "En charge" in etat else "orange"
            
            with open("/home/thomas/hechicero/data/batterie.txt", "w") as f:
                f.write(f"{p}%|{etat}|{couleur}")
        except Exception as e:
            with open("/home/thomas/hechicero/data/batterie.txt", "w") as f:
                f.write("?%|Erreur|red")
        
        time.sleep(config["battery_check_interval_seconds"])

if __name__ == "__main__":
    run_loop()


# import smbus
# from INA219 import INA219

# # Initialisation de l'INA219
# # On s'assure qu'il est bien à l'adresse 0x43 comme détecté précédemment
# ina = INA219(addr=0x43)

# def update_status():
#     try:
#         # Lecture des valeurs
#         bus_voltage = ina.getBusVoltage_V()
#         current_ma = -ina.getCurrent_mA() # On inverse pour avoir un courant positif en charge
        
#         # Calcul du pourcentage (basé sur la formule de Waveshare)
#         # 3.0V = 0%, 4.2V = 100%
#         p = (bus_voltage - 3.0) / 1.2 * 100
#         p = max(0, min(100, int(p)))
        
#         # Logique de charge (Si courant > 50mA, la batterie est en train de charger)
#         if current_ma > 50:
#             etat = "En charge ⚡"
#             couleur = "green"
#         else:
#             etat = "Sur batterie 🔋"
#             couleur = "orange"
        
#         # Écriture dans le fichier formatée pour PHP
#         # Format : Pourcentage | État | Couleur
#         with open("/home/thomas/hechicero/data/batterie.txt", "w") as f:
#             f.write(f"{p}%|{etat}|{couleur}")
            
#     except Exception as e:
#         # En cas d'erreur (ex: HAT débranché), on écrit un état par défaut
#         with open("/home/thomas/hechicero/data/batterie.txt", "w") as f:
#             f.write("?%|Erreur|red")

# if __name__ == "__main__":
#     update_status()