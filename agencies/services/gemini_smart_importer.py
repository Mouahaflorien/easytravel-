import os
import json
import logging
from urllib import request as url_request
from django.conf import settings
from django.utils.dateparse import parse_date, parse_time
from django.utils import timezone
from django.db import transaction

from travel.models import Driver, Vehicle, City, Line, Departure
from agencies.models import Agency

logger = logging.getLogger(__name__)

class GeminiSmartImporter:
    """
    Analyse un texte brut (PDF, WhatsApp, Email) via Gemini et 
    crée automatiquement la structure de la base de données.
    """
    def __init__(self, agency):
        self.agency = agency
        self.gemini_api_key = getattr(settings, 'GEMINI_API_KEY', os.environ.get('GEMINI_API_KEY', '')).strip()
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={self.gemini_api_key}"

    def extract_and_import(self, raw_text):
        if not self.gemini_api_key:
            raise ValueError("Clé API Gemini introuvable.")

        prompt = f"""
        Tu es un système intelligent pour une compagnie de transport au Cameroun.
        Lis attentivement le texte brut suivant. Il contient un planning de voyages, des chauffeurs et des véhicules.
        Extrais toutes ces informations et renvoie-moi STRICTEMENT un objet JSON valide (aucun commentaire markdown, juste le JSON).
        
        Structure du JSON attendu :
        {{
            "drivers": [
                {{"first_name": "Jean", "last_name": "Dupont", "phone": "600000000"}}
            ],
            "vehicles": [
                {{"registration": "CE-1234-A", "type": "bus", "capacity": 70}}
            ],
            "cities": ["Douala", "Yaoundé"],
            "departures": [
                {{
                    "departure_city": "Douala",
                    "arrival_city": "Yaoundé",
                    "date": "2026-12-25",
                    "time": "14:00",
                    "vehicle_registration": "CE-1234-A",
                    "driver_phone": "600000000",
                    "price": 5000
                }}
            ]
        }}

        Instructions importantes :
        - Déduis correctement les villes (ex: DLA -> Douala, YDE -> Yaoundé).
        - Si la date n'est pas claire, essaie de déduire une date au format YYYY-MM-DD.
        - Si la capacité du bus n'est pas mentionnée, mets 70.
        - N'invente pas de chauffeurs s'il n'y en a pas, laisse la liste vide.

        TEXTE BRUT À ANALYSER :
        \"\"\"{raw_text}\"\"\"
        """

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "response_mime_type": "application/json"
            }
        }

        try:
            req = url_request.Request(self.api_url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
            with url_request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                
            response_text = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
            
            # Nettoyer d'éventuels backticks markdown
            if response_text.startswith("```json"):
                response_text = response_text.strip("```json").strip("```").strip()
            
            data = json.loads(response_text)
            return self._build_from_json(data)

        except Exception as e:
            logger.exception("Erreur IA Gemini Import : %s", e)
            raise ValueError(f"Impossible de comprendre le texte via l'IA : {str(e)}")

    @transaction.atomic
    def _build_from_json(self, data):
        stats = {'drivers': 0, 'vehicles': 0, 'cities': 0, 'lines': 0, 'departures': 0}
        
        # 1. Chauffeurs
        driver_map = {}
        for d in data.get('drivers', []):
            phone = str(d.get('phone', '')).strip()
            if phone:
                driver, created = Driver.objects.get_or_create(
                    agency=self.agency,
                    phone=phone,
                    defaults={'first_name': d.get('first_name', 'Inconnu'), 'last_name': d.get('last_name', '')}
                )
                driver_map[phone] = driver
                if created: stats['drivers'] += 1

        # 2. Véhicules
        vehicle_map = {}
        for v in data.get('vehicles', []):
            reg = str(v.get('registration', '')).strip()
            if reg:
                vehicle, created = Vehicle.objects.get_or_create(
                    agency=self.agency,
                    registration=reg,
                    defaults={'vehicle_type': v.get('type', 'bus'), 'capacity': int(v.get('capacity', 70))}
                )
                vehicle_map[reg] = vehicle
                if created: stats['vehicles'] += 1

        # 3. Villes
        city_map = {}
        for city_name in data.get('cities', []):
            city_name_clean = city_name.strip()
            if city_name_clean:
                city, created = City.objects.get_or_create(name__iexact=city_name_clean, defaults={'name': city_name_clean.title()})
                city_map[city_name_clean.lower()] = city
                if created: stats['cities'] += 1

        # 4. Lignes et Départs
        for dep in data.get('departures', []):
            start = str(dep.get('departure_city', '')).strip().lower()
            end = str(dep.get('arrival_city', '')).strip().lower()
            if start and end and start in city_map and end in city_map:
                line_name = f"{city_map[start].name} - {city_map[end].name}"
                line, l_created = Line.objects.get_or_create(
                    agency=self.agency,
                    departure_city=city_map[start],
                    arrival_city=city_map[end],
                    defaults={'name': line_name}
                )
                if l_created: stats['lines'] += 1
                
                v_reg = str(dep.get('vehicle_registration', '')).strip()
                d_phone = str(dep.get('driver_phone', '')).strip()
                vehicle = vehicle_map.get(v_reg)
                driver = driver_map.get(d_phone)
                
                date_val = parse_date(dep.get('date', '')) or timezone.now().date()
                time_val = parse_time(dep.get('time', '')) or timezone.now().time()
                
                Departure.objects.create(
                    agency=self.agency,
                    line=line,
                    date=date_val,
                    time=time_val,
                    vehicle=vehicle,
                    driver=driver,
                    status='scheduled',
                    available_capacity=vehicle.capacity if vehicle else 70
                )
                stats['departures'] += 1

        return stats
