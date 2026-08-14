import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hardware_inventory_management.settings')
django.setup()

from inventory.models import Vendor

vendors = [
    {"name": "Tech Solutions Pvt. Ltd.", "address": "Kathmandu", "contact_person": "Ram Sharma", "phone": "9801234567", "email": "sales@techsolutions.com.np"},
    {"name": "Digital Systems Nepal", "address": "Lalitpur", "contact_person": "Sita Thapa", "phone": "9807654321", "email": "contact@digitalsystems.np"},
    {"name": "Himalayan IT Services", "address": "Bhaktapur", "contact_person": "Hari Prasad", "phone": "9812345678", "email": "info@himalayanit.com"},
    {"name": "InfoTech Traders", "address": "Pokhara", "contact_person": "Gita Devi", "phone": "9845678901", "email": "support@infotech.com.np"},
    {"name": "Nepal Computer House", "address": "Biratnagar", "contact_person": "Suresh KC", "phone": "9867890123", "email": "sales@nch.com.np"},
]

for v in vendors:
    Vendor.objects.get_or_create(name=v["name"], defaults=v)

print("Vendors seeded successfully.")
