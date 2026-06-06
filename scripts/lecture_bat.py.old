import smbus
import os

# Configuration
BUS = smbus.SMBus(1)
ADDRESS = 0x2D
FILE_PATH = "/home/thomas/hechicero/scripts/batterie.txt"

""" def get_data():
    try:
        # 1. Lecture du pourcentage (Registre 0x02)
        pct = BUS.read_word_data(ADDRESS, 0x02)
        pct = min(max(pct, 0), 100)
        
        # 2. Lecture du statut alimentation (Registre 0x04)
        # Note: 0x04 sur le HAT (D) indique l'état d'alimentation externe
        status_raw = BUS.read_word_data(ADDRESS, 0x04)
        
        # Logique de statut (à ajuster selon tes tests de débranchement)
        status = "Secteur" if status_raw > 0 else "Batterie"
        
        return pct, status
    except Exception as e:
        return 0, "Erreur"
 """
def get_data():
    try:
        # Pourcentage (on garde 0x02)
        pct = BUS.read_word_data(ADDRESS, 0x02)
        pct = min(max(pct, 0), 100)
        
        # TEST : Lecture du registre 0x00 au lieu de 0x04
        status_raw = BUS.read_word_data(ADDRESS, 0x00)
        
        # Parfois, c'est un bit spécifique dans le registre 0x00 ou 0x0A
        # On va afficher la valeur brute pour comprendre ce qui change
        return pct, status_raw
    except:
        return 0, 0

if __name__ == "__main__":
    pourcentage, etat = get_data()
    
    # Écriture dans le fichier pour PHP
    with open(FILE_PATH, "w") as f:
        f.write(f"{pourcentage}% - {etat}")

    # Pour vérifier dans le terminal
    print(f"Niveau: {pourcentage}% | Alimentation: {etat}")