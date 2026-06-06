import smbus
import time

bus = smbus.SMBus(1)
ADDRESS = 0x2D 

def get_battery_voltage():
    try:
        # Lecture de la tension brute (registre 0x09 pour ce modèle)
        data = bus.read_word_data(ADDRESS, 0x09)
        # La valeur est en mV (ex: 4100 = 4.1V)
        return data
    except:
        return 0

def voltage_to_percent(voltage):
    # Approximation Li-ion : 3.2V (0%) à 4.2V (100%)
    if voltage < 3200: return 0
    if voltage > 4200: return 100
    return int((voltage - 3200) / 10)

voltage = get_battery_voltage()
percent = voltage_to_percent(voltage)

# on écrit la valeur pour que le PHP puisse la lire:
with open("/home/thomas/hechicero/scripts/batterie.txt", "w") as f:
    f.write(str(percent))

print(f"Tension : {voltage}mV, Niveau : {percent}%")