import pandas as pd

from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_date

from inventory.models import (
    Department,
    Brand,
    Computer,
    ComputerModel,
    Printer,
    PrinterModel,
)

class Command(BaseCommand):
    help = 'Import printer data from Excel file'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str)

    def handle(self, *args, **kwargs):
        file_path = kwargs['file_path']

        try:
            raw = pd.read_excel(file_path, header=None)
            department_name = str(raw.iloc[1, 2]).strip().upper()
            df = pd.read_excel(file_path, header=2)         

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to read Excel file: {e}'))
            return

        department, _ = Department.objects.get_or_create(name=department_name)

        for index, row in df.iterrows():

            brand_name  = str(row.get('Brand',  '')).strip().upper()
            model_name  = str(row.get('Model',  '')).strip().upper()
            serial_no   = str(row.get('Device Serial No', '')).strip().upper()


            if not serial_no or serial_no.lower() == 'nan':
                continue

            brand, _ = Brand.objects.get_or_create(name=brand_name)

            purchase_date     = self.parse_excel_date(row.get('Purchase Date'))
            warranty_end_date = self.parse_excel_date(row.get('Warranty End Date'))

            printer_model, _ = PrinterModel.objects.get_or_create(
                brand=brand,
                name=model_name,
                defaults={
                    'printer_type': self.get_printer_type_choice(
                        str(row.get('Printer Type', '')).strip().upper()
                    )
                }
            )

            Printer.objects.update_or_create(
                serial_no=serial_no,
                defaults={
                    'ims_code':          str(row.get('IMS Code', '')).strip(),
                    'department':        department,
                    'printer_name':      model_name,
                    'model':             printer_model,
                    'ip_address':        self.clean_ip(row.get('Ip address ')),
                    'printer_function':  str(row.get('Printer Function', '')).strip(),
                    'purchase_date':     purchase_date,
                    'warranty_end_date': warranty_end_date,
                    'status':            self.get_status_choice(
                                             str(row.get('Status', '')).strip()
                                         ),
                }
            )

            self.stdout.write(
                self.style.SUCCESS(f'Imported Printer: {serial_no}')
            )

        self.stdout.write(
            self.style.SUCCESS('Inventory import completed successfully.')
        )

    def parse_excel_date(self, value):
        if pd.isna(value):
            return None
        try:
            return pd.to_datetime(value).date()
        except Exception:
            return None

    def clean_ip(self, value):
        if pd.isna(value):
            return None
        value = str(value).strip()
        if value == '' or value.upper() == 'NOT CONNECTED':
            return None
        return value

    def get_status_choice(self, status):
        mapping = {
            'IN USE':     'ACTIVE',
            'ACTIVE':     'ACTIVE',
            'NOT IN USE': 'INACTIVE',
            'INACTIVE':   'INACTIVE',
            'REPAIR':     'REPAIR',
            'DISPOSED':   'DISPOSED',
        }
        return mapping.get(status.upper(), 'ACTIVE')

    def get_printer_type_choice(self, printer_type):
        mapping = {
            'MONOCHROME':  'LASER',
            'COLOR LASER': 'COLOR_LASER',
            'INKJET':      'INKJET',
        }
        return mapping.get(printer_type.upper(), 'LASER')

    def get_os_choice(self, os_name):
        mapping = {
            'WINDOWS 10': 'WINDOWS_10',
            'WINDOWS 11': 'WINDOWS_11',
            'WINDOWS 7':  'WINDOWS_7',
            'UBUNTU':     'LINUX_UBUNTU',
            'MACOS':      'MACOS',
        }
        return mapping.get(os_name.upper(), 'OTHER')