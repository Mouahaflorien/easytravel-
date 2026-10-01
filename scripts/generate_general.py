import csv
import random
from datetime import datetime, timedelta

def generate():
    # 32 Buses
    buses = [f"GEN-{str(i).zfill(3)}" for i in range(1, 33)]
    
    # Types of buses
    bus_types = {}
    for b in buses:
        bus_types[b] = random.choice(['VIP 50', 'Classique 70', 'Premium 30'])
        
    # Fleet assignment: 16 for Yaounde line, 16 for Bafoussam line
    y_buses = buses[:16] # 8 start in DLA, 8 start in YDE
    b_buses = buses[16:] # 8 start in DLA, 8 start in BAF
    
    # Track bus state: (next_available_time, current_location)
    # Start at 05:00 on Sept 22, 2026 (Today)
    start_time = datetime(2026, 9, 22, 5, 0)
    
    bus_state = {}
    for i, b in enumerate(y_buses):
        loc = 'Douala' if i < 8 else 'Yaoundé'
        bus_state[b] = {'time': start_time, 'loc': loc, 'line_group': 'Y'}
        
    for i, b in enumerate(b_buses):
        loc = 'Douala' if i < 8 else 'Bafoussam'
        bus_state[b] = {'time': start_time, 'loc': loc, 'line_group': 'B'}
        
    departures = []
    
    # Generate schedule until Oct 20, 2026
    end_time = datetime(2026, 10, 20, 21, 0)
    
    # Line configs
    # Travel times: DLA-YDE = 4h, DLA-BAF = 5h
    routes = {
        'Douala-Yaoundé': {'stops': 'Douala-Edea-Yaoundé', 'duration': timedelta(hours=4), 'dest': 'Yaoundé'},
        'Yaoundé-Douala': {'stops': 'Yaoundé-Edea-Douala', 'duration': timedelta(hours=4), 'dest': 'Douala'},
        'Douala-Bafoussam': {'stops': 'Douala-Bafang-Bafoussam', 'duration': timedelta(hours=5), 'dest': 'Bafoussam'},
        'Bafoussam-Douala': {'stops': 'Bafoussam-Bafang-Douala', 'duration': timedelta(hours=5), 'dest': 'Douala'},
    }
    
    current_time = start_time
    
    # We want a departure every 15 mins for Douala-Yaoundé (both ways)
    # And maybe every 30 mins for Douala-Bafoussam
    
    while current_time < end_time:
        # Only operate between 05:00 and 21:00
        if 5 <= current_time.hour <= 20:
            
            # --- Douala <-> Yaoundé --- (Every 15 mins)
            if current_time.minute in [0, 15, 30, 45]:
                # Try to launch from Douala to Yaounde
                available_dla_y = [b for b in y_buses if bus_state[b]['loc'] == 'Douala' and bus_state[b]['time'] <= current_time]
                if available_dla_y:
                    bus = available_dla_y[0]
                    departures.append((bus, 'Douala - Yaoundé', routes['Douala-Yaoundé']['stops'], current_time))
                    # Bus arrives + 4h, rests for 30 mins
                    bus_state[bus]['loc'] = 'Yaoundé'
                    bus_state[bus]['time'] = current_time + routes['Douala-Yaoundé']['duration'] + timedelta(minutes=30)
                
                # Try to launch from Yaounde to Douala
                available_yde_d = [b for b in y_buses if bus_state[b]['loc'] == 'Yaoundé' and bus_state[b]['time'] <= current_time]
                if available_yde_d:
                    bus = available_yde_d[0]
                    departures.append((bus, 'Yaoundé - Douala', routes['Yaoundé-Douala']['stops'], current_time))
                    bus_state[bus]['loc'] = 'Douala'
                    bus_state[bus]['time'] = current_time + routes['Yaoundé-Douala']['duration'] + timedelta(minutes=30)
            
            # --- Douala <-> Bafoussam --- (Every 30 mins)
            if current_time.minute in [0, 30]:
                # From Douala
                available_dla_b = [b for b in b_buses if bus_state[b]['loc'] == 'Douala' and bus_state[b]['time'] <= current_time]
                if available_dla_b:
                    bus = available_dla_b[0]
                    departures.append((bus, 'Douala - Ouest', routes['Douala-Bafoussam']['stops'], current_time))
                    bus_state[bus]['loc'] = 'Bafoussam'
                    bus_state[bus]['time'] = current_time + routes['Douala-Bafoussam']['duration'] + timedelta(minutes=30)
                    
                # From Bafoussam
                available_baf_d = [b for b in b_buses if bus_state[b]['loc'] == 'Bafoussam' and bus_state[b]['time'] <= current_time]
                if available_baf_d:
                    bus = available_baf_d[0]
                    departures.append((bus, 'Ouest - Douala', routes['Bafoussam-Douala']['stops'], current_time))
                    bus_state[bus]['loc'] = 'Douala'
                    bus_state[bus]['time'] = current_time + routes['Bafoussam-Douala']['duration'] + timedelta(minutes=30)

        current_time += timedelta(minutes=15)
        
        # If it's 21:00, jump to next day 05:00
        if current_time.hour == 21:
            current_time = (current_time + timedelta(days=1)).replace(hour=5, minute=0)
            
            
    with open('data_agence_general_1_mois.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Matricule Bus', 'Type Bus', 'Capacité', 'Nom de la Ligne', 'Arrêts', 'Heure Depart', 'Date Depart'])
        
        for dep in departures:
            bus, ligne_nom, arrets, dt = dep
            v_type = bus_types[bus]
            if '50' in v_type: cap = 50
            elif '30' in v_type: cap = 30
            else: cap = 70
            
            heure = dt.strftime('%H:%M')
            date_str = dt.strftime('%Y-%m-%d')
            
            writer.writerow([bus, v_type, cap, ligne_nom, arrets, heure, date_str])

    print(f"Generated {len(departures)} departures for Agence General in data_agence_general_1_mois.csv")

if __name__ == '__main__':
    generate()
