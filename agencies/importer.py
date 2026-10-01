import csv
import io
from datetime import timedelta
from django.utils.dateparse import parse_time, parse_date
from travel.models import Vehicle, Line, LineStop, City, Departure

def import_agency_data(agency, file_obj):
    decoded_file = file_obj.read().decode('utf-8-sig') # Handle BOM if saved from Excel
    io_string = io.StringIO(decoded_file)
    
    # Try to sniff dialect, fallback to comma
    try:
        dialect = csv.Sniffer().sniff(io_string.read(1024), delimiters=";,")
        io_string.seek(0)
    except:
        io_string.seek(0)
        dialect = csv.excel
        
    reader = csv.DictReader(io_string, dialect=dialect)
    
    # Clean headers (strip spaces, lowercase, remove accents)
    def clean_header(h):
        if not h: return ""
        return h.strip().lower().replace('é', 'e').replace('è', 'e').replace('ê', 'e')

    raw_headers = reader.fieldnames
    if not raw_headers:
        raise ValueError("Le fichier CSV est vide ou mal formaté.")
        
    headers = {clean_header(h): h for h in raw_headers}
    
    # Helper to find column loosely
    def get_val(row, *possible_names):
        for name in possible_names:
            for k, original_k in headers.items():
                if name in k:
                    return row[original_k]
        return None

    for row in reader:
        # 1. Vehicle
        matricule = get_val(row, 'matricule', 'plaque')
        v_type = get_val(row, 'type')
        cap = get_val(row, 'capacite', 'places')
        
        vehicle = None
        if matricule:
            try:
                cap_int = int(cap) if cap else 50
            except:
                cap_int = 50
                
            vehicle, _ = Vehicle.objects.get_or_create(
                agency=agency,
                registration=matricule.strip(),
                defaults={'vehicle_type': v_type or 'Bus Standard', 'capacity': cap_int}
            )
            
        # 2. Line & Stops
        line_name = get_val(row, 'ligne', 'trajet')
        arrets_str = get_val(row, 'arret', 'villes', 'chemin')
        
        line = None
        if line_name and arrets_str:
            line, _ = Line.objects.get_or_create(agency=agency, name=line_name.strip())
            
            arrets = [a.strip() for a in arrets_str.split('-') if a.strip()]
            for i, city_name in enumerate(arrets):
                city = City.objects.filter(name__iexact=city_name).first()
                if not city:
                    city = City.objects.create(name=city_name.title(), is_active=True)
                
                # Mock logic for price and duration (could be improved if we had a distance matrix)
                # For simplicity: +2500 FCFA and +2h per stop
                LineStop.objects.get_or_create(
                    line=line,
                    stop_order=i+1,
                    defaults={
                        'city': city,
                        'price_from_start': i * 2500,
                        'duration_from_start': timedelta(hours=i*2)
                    }
                )
                
        # 3. Departure
        heure = get_val(row, 'heure')
        date_str = get_val(row, 'date')
        
        if line and date_str and heure:
            # Simple parsing (expects HH:MM and YYYY-MM-DD)
            parsed_time = parse_time(heure.strip())
            # Handle DD/MM/YYYY format
            if '/' in date_str:
                parts = date_str.strip().split('/')
                if len(parts) == 3:
                    date_str = f"{parts[2]}-{parts[1]}-{parts[0]}"
            parsed_date = parse_date(date_str.strip())
            
            if parsed_time and parsed_date:
                Departure.objects.get_or_create(
                    agency=agency,
                    line=line,
                    date=parsed_date,
                    time=parsed_time,
                    defaults={
                        'vehicle': vehicle,
                        'available_capacity': vehicle.capacity if vehicle else 50,
                        'status': 'scheduled'
                    }
                )
