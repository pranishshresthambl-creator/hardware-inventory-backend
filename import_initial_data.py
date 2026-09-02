import os
import sys
import datetime
import re
import pandas as pd
import openpyxl

backend_dir = os.path.abspath(os.path.dirname(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hardware_inventory_management.settings')
import django
django.setup()

from inventory.models import Department, Brand, ComputerModel, Computer, PrinterModel, Printer
from api.import_views import (
    clean_text,
    parse_ip,
    parse_date,
    normalize_status,
    normalize_ram,
    normalize_storage,
    normalize_os,
    resolve_department,
    resolve_brand,
    resolve_computer_model,
    resolve_printer_model,
)

EXCEL_SOURCE = "/Users/binayakprajapati/Desktop/Binayak NRB/Initial Report one Final.xlsx"
EXCEL_FIXED_OUTPUT = "/Users/binayakprajapati/Desktop/Binayak NRB/Initial Report one Final.xlsx"
DESKTOP_FIXED_OUTPUT = "/Users/binayakprajapati/Desktop/Initial Report one Final.xlsx"

def import_computers():
    print("\n==========================================")
    print(">>> STARTING COMPUTER DATA IMPORT...")
    print("==========================================")
    df_comp = pd.read_excel(EXCEL_SOURCE, sheet_name='Computer')
    print(f"Total rows in Excel 'Computer' sheet: {len(df_comp)}")

    created = 0
    updated = 0
    cleaned_rows = []

    for idx, row in df_comp.iterrows():
        dept_raw = row.get('Department')
        dept_obj = resolve_department(dept_raw)

        brand_raw = row.get('Make/ Manufacturer')
        brand_obj = resolve_brand(brand_raw)

        model_raw = clean_text(row.get('Model'))
        proc_raw = clean_text(row.get('Processor Type and Speed'))
        model_obj = resolve_computer_model(brand_obj, model_raw, proc_raw)

        ram_val = normalize_ram(row.get('RAM'))
        storage_cap, storage_type = normalize_storage(row.get('Storage Capacity'))
        os_val = normalize_os(row.get('Operating System'))
        ip_val = parse_ip(row.get('IP Address'))
        host_val = clean_text(row.get('Host Name'))
        serial_val = clean_text(row.get('Serial Number'))
        ims_val = clean_text(row.get('Asset ID'))
        status_val = normalize_status(row.get('Device Status'))
        hotfix_id_val = clean_text(row.get('HotFix ID'))
        hotfix_date_val = parse_date(row.get('HotFix Date'))
        user_val = clean_text(row.get('User'))
        performed_by = clean_text(row.get('Performed by'))

        # Prepare cleaned row dictionary for fixed Excel export
        cleaned_rows.append({
            'Department': dept_obj.name if dept_obj else None,
            'Asset ID': ims_val,
            'Serial Number': serial_val,
            'Brand': brand_obj.name if brand_obj else None,
            'Model': model_obj.name if model_obj else model_raw,
            'Device Type': model_obj.computer_type if model_obj else 'DESKTOP',
            'Processor': proc_raw,
            'RAM': ram_val,
            'Storage Capacity': storage_cap,
            'Storage Type': storage_type,
            'Operating System': os_val,
            'IP Address': ip_val,
            'Host Name': host_val,
            'Device Status': status_val,
            'Assigned User': user_val,
            'HotFix ID': hotfix_id_val,
            'HotFix Date': str(hotfix_date_val) if hotfix_date_val else None,
            'Performed By': performed_by,
        })

        # Match existing by serial_no or host_name
        existing = None
        if serial_val:
            existing = Computer.objects.filter(serial_no=serial_val).first()
        if not existing and host_val:
            existing = Computer.objects.filter(host_name=host_val).first()

        if existing:
            existing.department = dept_obj or existing.department
            existing.model = model_obj or existing.model
            if ims_val:
                existing.ims_code = ims_val
            if serial_val:
                existing.serial_no = serial_val
            if proc_raw:
                existing.processor = proc_raw
            if ram_val:
                existing.ram = ram_val
            if storage_cap:
                existing.storage_capacity = storage_cap
            if storage_type:
                existing.storage_type = storage_type
            if os_val:
                existing.operating_system = os_val
            if ip_val:
                existing.ip_address = ip_val
            if host_val:
                existing.host_name = host_val
            if hotfix_id_val:
                existing.hotfix_id = hotfix_id_val
            if hotfix_date_val:
                existing.hotfix_date = hotfix_date_val
            existing.status = status_val
            existing.save()
            updated += 1
        else:
            Computer.objects.create(
                department=dept_obj,
                model=model_obj,
                ims_code=ims_val,
                serial_no=serial_val,
                processor=proc_raw or 'N/A',
                ram=ram_val,
                storage_capacity=storage_cap,
                storage_type=storage_type,
                operating_system=os_val,
                ip_address=ip_val,
                host_name=host_val,
                hotfix_id=hotfix_id_val,
                hotfix_date=hotfix_date_val,
                status=status_val,
            )
            created += 1

    print(f"✓ COMPUTERS IMPORT COMPLETE: {created} created, {updated} updated, Total in DB: {Computer.objects.count()}")
    return pd.DataFrame(cleaned_rows)


def import_printers():
    print("\n==========================================")
    print(">>> STARTING PRINTER DATA IMPORT...")
    print("==========================================")
    df_print = pd.read_excel(EXCEL_SOURCE, sheet_name='Printer')
    print(f"Total rows in Excel 'Printer' sheet: {len(df_print)}")

    created = 0
    updated = 0
    cleaned_rows = []

    for idx, row in df_print.iterrows():
        dept_raw = row.get('Department')
        dept_obj = resolve_department(dept_raw)

        brand_raw = row.get('Brand')
        brand_obj = resolve_brand(brand_raw)

        model_raw = clean_text(row.get('Model'))
        type_raw = clean_text(row.get('Printer Type'))
        raw_device = clean_text(row.get('Device'))
        if raw_device and raw_device.lower() not in ('printer', 'printers', 'device', 'default', 'n/a'):
            device_raw = raw_device
        else:
            device_raw = (model_obj.name if model_obj else model_raw) or raw_device or 'Printer'
        ims_val = clean_text(row.get('IMS Code'))
        serial_val = clean_text(row.get('Device Serial No'))
        ip_val = parse_ip(row.get('Ip address '))
        func_val = clean_text(row.get('Printer Function'))
        status_val = normalize_status(row.get('Status'))

        cleaned_rows.append({
            'Department': dept_obj.name if dept_obj else None,
            'IMS Code': ims_val,
            'Device Name': device_raw,
            'Brand': brand_obj.name if brand_obj else None,
            'Model': model_obj.name if model_obj else model_raw,
            'Printer Type': model_obj.printer_type if model_obj else 'LASER',
            'Printer Function': func_val,
            'IP Address': ip_val,
            'Serial Number': serial_val,
            'Status': status_val,
        })

        existing = None
        if serial_val:
            existing = Printer.objects.filter(serial_no=serial_val).first()

        if existing:
            existing.department = dept_obj or existing.department
            existing.model = model_obj or existing.model
            existing.printer_name = device_raw
            if ims_val:
                existing.ims_code = ims_val
            if ip_val:
                existing.ip_address = ip_val
            if func_val:
                existing.printer_function = func_val
            existing.status = status_val
            existing.save()
            updated += 1
        else:
            Printer.objects.create(
                department=dept_obj,
                model=model_obj,
                printer_name=device_raw,
                ims_code=ims_val,
                serial_no=serial_val,
                ip_address=ip_val,
                printer_function=func_val,
                status=status_val,
            )
            created += 1

    print(f"✓ PRINTERS IMPORT COMPLETE: {created} created, {updated} updated, Total in DB: {Printer.objects.count()}")
    return pd.DataFrame(cleaned_rows)


if __name__ == '__main__':
    df_clean_comp = import_computers()
    df_clean_print = import_printers()

    print("\n==========================================")
    print(">>> EXPORTING CLEANED EXCEL FILES...")
    print("==========================================")
    with pd.ExcelWriter(EXCEL_FIXED_OUTPUT, engine='openpyxl') as writer:
        df_clean_comp.to_excel(writer, sheet_name='Computer', index=False)
        df_clean_print.to_excel(writer, sheet_name='Printer', index=False)
    print(f"✓ Saved cleaned Excel to: {EXCEL_FIXED_OUTPUT}")

    try:
        with pd.ExcelWriter(DESKTOP_FIXED_OUTPUT, engine='openpyxl') as writer:
            df_clean_comp.to_excel(writer, sheet_name='Computer', index=False)
            df_clean_print.to_excel(writer, sheet_name='Printer', index=False)
        print(f"✓ Saved cleaned Excel to Desktop: {DESKTOP_FIXED_OUTPUT}")
    except Exception as e:
        print("Note on saving to Desktop:", e)

    print("\n================ ALL TASKS FINISHED ================\n")
