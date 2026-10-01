import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from accounts.models import User
from agencies.models import Agency
from travel.models import City

def seed():
    # Create superuser
    if not User.objects.filter(username="admin").exists():
        User.objects.create_superuser("admin", "admin@example.com", "admin123")
        print("Superuser created")
        
    # Create cities
    cities = ['Nkongsamba', 'Melong', 'Bafang', 'Yaoundé', 'Douala']
    for city_name in cities:
        City.objects.get_or_create(name=city_name, is_active=True)
    print("Cities created")

    # Create Agency
    user = User.objects.get(username="admin")
    Agency.objects.get_or_create(
        name="Test Agency", 
        owner=user, 
        email="test@example.com",
        phone="12345678"
    )
    print("Agency created")

if __name__ == '__main__':
    seed()
