import csv
import random
from datetime import datetime, timedelta

def generate():
    # Large Fleet: 50 Buses for FINEX
    buses = [f"FNX-{str(i).zfill(3)}" for i in range(1, 51)]
    
    # Types of buses (FINEX usually has premium buses)
    bus_types = {}
    for b in buses:
        bus_types[b] = random.choice(['VIP 50', 'VIP 70'])
        
    # Fleet assignment: 25 start in Douala, 25 start in Yaounde
    d_buses = buses[:25]
    y_buses = buses[25:]
    
    # Track bus state: (next_available_time, current_location)
    # Start at 05:00 on Sept 22, 2026 (Today)
    start_time = datetime(2026, 9, 22, 5, 0)
    
    bus_state = {}
    for b in d_buses:
        bus_state[b] = {'time': start_time, 'loc': 'Douala'}
        
    for b in y_buses:
        bus_state[b] = {'time': start_time, 'loc': 'Yaoundé'}
        
    departures = []
    
    # Generate schedule until Oct 20, 2026
    end_time = datetime(2026, 10, 20, 21, 0)
    
    # Travel times: DLA-YDE = 4h
    route_dla_yde = 'Douala-Edea-Yaoundé'
    route_yde_dla = 'Yaoundé-Edea-Douala'
    duration = timedelta(hours=4)
    
    current_time = start_time
    
    # Departure every 20 mins
    
    while current_time < end_time:
        # Only operate between 05:00 and 21:00
        if 5 <= current_time.hour <= 20:
            
            if current_time.minute in [0, 20, 40]:
                # Try to launch from Douala to Yaounde
                available_dla = [b for b in buses if bus_state[b]['loc'] == 'Douala' and bus_state[b]['time'] <= current_time]
                if available_dla:
                    bus = available_dla[0]
                    departures.append((bus, 'Axe Lourd (Douala-Yaoundé)', route_dla_yde, current_time))
                    bus_state[bus]['loc'] = 'Yaoundé'
                    bus_state[bus]['time'] = current_time + duration + timedelta(minutes=30)
                
                # Try to launch from Yaounde to Douala
                available_yde = [b for b in buses if bus_state[b]['loc'] == 'Yaoundé' and bus_state[b]['time'] <= current_time]
                if available_yde:
                    bus = available_yde[0]
                    departures.append((bus, 'Axe Lourd (Yaoundé-Douala)', route_yde_dla, current_time))
                    bus_state[bus]['loc'] = 'Douala'
                    bus_state[bus]['time'] = current_time + duration + timedelta(minutes=30)
                    
        current_time += timedelta(minutes=20)
        
        # If it's past 21:00, jump to next day 05:00
        if current_time.hour >= 21:
            current_time = (current_time + timedelta(days=1)).replace(hour=5, minute=0)
            
            
    with open('data_agence_finex.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Matricule Bus', 'Type Bus', 'Capacité', 'Nom de la Ligne', 'Arrêts', 'Heure Depart', 'Date Depart'])
        
        for dep in departures:
            bus, ligne_nom, arrets, dt = dep
            v_type = bus_types[bus]
            cap = 50 if '50' in v_type else 70
            
            heure = dt.strftime('%H:%M')
            date_str = dt.strftime('%Y-%m-%d')
            
            writer.writerow([bus, v_type, cap, ligne_nom, arrets, heure, date_str])

    print(f"Generated {len(departures)} departures for FINEX in data_agence_finex.csv")

if __name__ == '__main__':
    generate()
