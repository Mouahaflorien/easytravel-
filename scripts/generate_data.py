import csv
import random
from datetime import datetime, timedelta

def generate():
    types = ['VIP 50', 'Classique', 'Premium 30', 'MiniBus 20']
    lignes = [
        ('Ouest - Littoral', 'Douala-Bafang-Bafoussam-Dschang'),
        ('Centre - Littoral', 'Yaoundé-Edea-Douala'),
        ('Nord - Centre', 'Garoua-Ngaoundéré-Yaoundé'),
        ('Sud - Centre', 'Ebolowa-Mbalmayo-Yaoundé'),
        ('Littoral - Sud Ouest', 'Douala-Buea-Limbe')
    ]
    
    with open('data_large.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Matricule Bus', 'Type Bus', 'Capacité', 'Nom de la Ligne', 'Arrêts', 'Heure Depart', 'Date Depart'])
        
        base_date = datetime(2026, 10, 15)
        
        for i in range(1, 55):
            matricule = f"LT-{1000 + i}"
            v_type = random.choice(types)
            if '50' in v_type: cap = 50
            elif '30' in v_type: cap = 30
            elif '20' in v_type: cap = 20
            else: cap = 70
            
            ligne_nom, arrets = random.choice(lignes)
            heure = f"{random.randint(6, 20):02d}:{random.choice(['00', '30'])}"
            
            # Repartir sur 3 jours
            jour = base_date + timedelta(days=random.randint(0, 2))
            date_str = jour.strftime('%Y-%m-%d')
            
            writer.writerow([matricule, v_type, cap, ligne_nom, arrets, heure, date_str])
            
generate()
