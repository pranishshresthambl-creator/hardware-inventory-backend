import os
import re
import datetime
import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from inventory.models import (
    Department,
    Brand,
    PrinterModel,
    Printer,
)

IP_REGEX = re.compile(r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$')

BRAND_CANONICAL_MAP = {
    'hp': 'HP',
    'hp inc': 'HP',
    'hp inc.': 'HP',
    'dell': 'Dell Inc',
    'dell inc': 'Dell Inc',
    'dell inc.': 'Dell Inc',
    'dell technologies': 'Dell Inc',
    'lenovo': 'Lenovo',
    'lenovo inc': 'Lenovo',
    'canon': 'Canon',
    'brother': 'Brother',
    'sharp': 'Sharp',
    'acer': 'Acer',
    'asus': 'ASUS',
    'msi': 'MSI',
    'apple': 'Apple',
    'benq': 'BenQ',
    'epson': 'Epson',
    'kyocera': 'Kyocera',
    'kyolera': 'Kyocera',
    'ricoh': 'Ricoh',
    'tsc': 'TSC',
    'pantum': 'Pantum',
    'fujitsu': 'Fujitsu',
    'xerox': 'Xerox',
}


def clean_text(val):
    if val is None or pd.isna(val):
        return None
    s = str(val).strip()
    if s.lower() in ('', 'nan', 'none', 'null', 'na', 'n/a', '-', '—', 'not mentioned', 'default string'):
        return None
    return s


def parse_ip(val):
    cleaned = clean_text(val)
    if not cleaned:
        return None
    cleaned = cleaned.replace(' ', '')
    if IP_REGEX.match(cleaned):
        return cleaned
    return None


def parse_date(val):
    if val is None or pd.isna(val):
        return None
    if isinstance(val, (datetime.date, datetime.datetime)):
        return val.date() if isinstance(val, datetime.datetime) else val
    s = str(val).strip()
    if not s or s.lower() in ('nan', 'none', 'null', 'n/a', '-'):
        return None
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y/%m/%d', '%d-%m-%Y', '%Y.%m.%d'):
        try:
            return datetime.datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    try:
        dt = pd.to_datetime(val)
        if pd.notna(dt):
            return dt.date()
    except Exception:
        pass
    return None


def normalize_status(val):
    cleaned = clean_text(val)
    if not cleaned:
        return None
    low = cleaned.lower()
    if any(k in low for k in ['not in use', 'not usable', 'not used', 'unused', 'unusable', 'offline', 'inactive']):
        return 'INACTIVE'
    if any(k in low for k in ['repair', 'maintenance']):
        return 'REPAIR'
    if any(k in low for k in ['disposed', 'scrap', 'damaged beyond']):
        return 'DISPOSED'
    if any(k in low for k in ['in use', 'in-use', 'ok', 'active', 'in ues']):
        return 'ACTIVE'
    return None


def resolve_department(name, cache=None):
    cleaned = clean_text(name)
    if not cleaned:
        return None
    norm = cleaned.upper()
    if cache is not None and norm in cache:
        return cache[norm]
    dept, _ = Department.objects.get_or_create(name=norm)
    if cache is not None:
        cache[norm] = dept
    return dept


def resolve_brand(name, cache=None):
    cleaned = clean_text(name)
    if not cleaned:
        return None
    canonical = BRAND_CANONICAL_MAP.get(cleaned.lower(), cleaned.title())
    key = canonical.lower()
    if cache is not None and key in cache:
        return cache[key]
    brand, _ = Brand.objects.get_or_create(name=canonical)
    if cache is not None:
        cache[key] = brand
    return brand


def resolve_printer_model(brand_obj, model_name, raw_type='', cache=None):
    cleaned_model = clean_text(model_name) or 'LaserJet Multifunction'
    if not brand_obj:
        brand_obj = resolve_brand('HP', cache)

    key = (brand_obj.id if brand_obj else None, cleaned_model.lower())
    if cache is not None and key in cache:
        return cache[key]

    low = (cleaned_model + ' ' + (raw_type or '')).lower()
    if any(k in low for k in ['ink', 'inkjet', 'deskjet', 'pixma']):
        pr_type = 'INKJET'
    elif any(k in low for k in ['thermal', 'pos', 'barcode']):
        pr_type = 'THERMAL'
    elif any(k in low for k in ['dot', 'matrix', 'passbook']):
        pr_type = 'DOT_MATRIX'
    else:
        pr_type = 'LASER'

    existing = PrinterModel.objects.filter(brand=brand_obj, name__iexact=cleaned_model).first()
    if not existing:
        existing = PrinterModel.objects.create(
            brand=brand_obj,
            name=cleaned_model,
            printer_type=pr_type
        )
    if cache is not None:
        cache[key] = existing
    return existing


def is_printer_device(device_val, ims_val, model_val):
    d = (str(device_val or '')).strip().lower()
    ims = (str(ims_val or '')).strip().lower()
    m = (str(model_val or '')).strip().lower()
    if any(k in d for k in ['printer', 'scanner', 'fax', 'copier', 'plotter', 'laserjet', 'deskjet', 'inkjet', 'mfp', 'thermal', 'passbook']):
        return True
    if any(k in ims for k in ['prn', 'prt', 'printer']):
        return True
    if any(k in m for k in ['laserjet', 'deskjet', 'pixma', 'imageclass', 'ecotank', 'mfp', 'workcentre', 'phaser']):
        return True
    return False


def is_computer_device(device_val, ims_val, model_val):
    d = (str(device_val or '')).strip().lower()
    ims = (str(ims_val or '')).strip().lower()
    m = (str(model_val or '')).strip().lower()
    if any(k in d for k in ['desktop', 'laptop', 'all in one', 'aio', 'mini pc', 'server', 'workstation', 'macbook', 'imac', 'thinkpad', 'optiplex', 'latitude', 'elitebook', 'probook', 'computer']):
        return True
    if any(k in ims for k in ['comp', 'laptop', 'desktop', 'srv', 'pc']):
        return True
    if any(k in m for k in ['optiplex', 'latitude', 'thinkpad', 'thinkcentre', 'probook', 'elitebook', 'inspiron', 'vostro', 'macbook']):
        return True
    return False


def get_row_val(row, key):
    val = row.get(key)
    if val is None:
        return None
    if isinstance(val, pd.Series):
        non_na = val.dropna()
        if not non_na.empty:
            return non_na.iloc[0]
        return None
    if isinstance(val, (list, tuple)):
        return val[0] if len(val) > 0 else None
    return val


def import_printers_data(file_or_path):
    """
    Core function used by BOTH Web Browser upload views and CLI Management Commands.
    """
    if hasattr(file_or_path, 'name'):
        filename = file_or_path.name.lower()
    else:
        filename = str(file_or_path).lower()

    if filename.endswith('.csv'):
        df = pd.read_csv(file_or_path)
    else:
        excel_file = pd.ExcelFile(file_or_path)
        sheet_target = None
        for s in excel_file.sheet_names:
            s_clean = s.strip().lower()
            if s_clean in ('printers', 'printer'):
                sheet_target = s
                break
        if not sheet_target:
            for s in excel_file.sheet_names:
                s_clean = s.strip().lower()
                if 'print' in s_clean:
                    sheet_target = s
                    break
        if not sheet_target:
            for s in excel_file.sheet_names:
                s_clean = s.strip().lower()
                if 'comp' not in s_clean and 'desktop' not in s_clean and 'laptop' not in s_clean:
                    sheet_target = s
                    break
        if not sheet_target:
            sheet_target = excel_file.sheet_names[0]
        df = pd.read_excel(excel_file, sheet_name=sheet_target)

    col_map = {}
    for col in df.columns:
        c_clean = str(col).strip().lower()
        if 'department' in c_clean or 'dept' in c_clean:
            col_map[col] = 'department'
        elif 'ims' in c_clean:
            col_map[col] = 'ims_code'
        elif 'serial' in c_clean:
            col_map[col] = 'serial_no'
        elif 'device' in c_clean:
            col_map[col] = 'device'
        elif 'brand' in c_clean or 'make' in c_clean or 'manufacturer' in c_clean:
            col_map[col] = 'brand'
        elif 'model' in c_clean:
            col_map[col] = 'model'
        elif 'type' in c_clean:
            col_map[col] = 'printer_type'
        elif 'function' in c_clean:
            col_map[col] = 'printer_function'
        elif 'fiscal' in c_clean or 'year' in c_clean:
            col_map[col] = 'fiscal_year'
        elif 'purchase' in c_clean:
            col_map[col] = 'purchase_date'
        elif 'warranty' in c_clean:
            col_map[col] = 'warranty_end_date'
        elif 'vendor email' in c_clean or 'vendor_email' in c_clean:
            col_map[col] = 'vendor_email'
        elif 'vendor' in c_clean:
            col_map[col] = 'vendor_name'
        elif 'domain' in c_clean:
            col_map[col] = 'domain'
        elif 'host' in c_clean:
            col_map[col] = 'host_name'
        elif 'ip' in c_clean:
            col_map[col] = 'ip_address'
        elif 'status' in c_clean:
            col_map[col] = 'status'

    df = df.rename(columns=col_map)

    created_count = 0
    updated_count = 0
    errors = []

    # Pre-cache database entities in memory for ultra-fast processing
    dept_cache = {d.name.upper(): d for d in Department.objects.all()}
    brand_cache = {b.name.lower(): b for b in Brand.objects.all()}
    printer_model_cache = {(m.brand_id, m.name.lower()): m for m in PrinterModel.objects.all()}
    prt_serial_cache = {p.serial_no.lower(): p for p in Printer.objects.exclude(serial_no=None).exclude(serial_no='')}

    for idx, row in df.iterrows():
        row_num = idx + 2
        try:
            device_type_raw = get_row_val(row, 'device') or get_row_val(row, 'device_type')
            ims_raw = get_row_val(row, 'ims_code')
            model_raw = get_row_val(row, 'model')

            # Strictly skip rows that are computer devices
            if is_computer_device(device_type_raw, ims_raw, model_raw) and not is_printer_device(device_type_raw, ims_raw, model_raw):
                continue

            with transaction.atomic():
                dept_val = get_row_val(row, 'department')
                dept_obj = resolve_department(dept_val, dept_cache)

                brand_val = get_row_val(row, 'brand')
                brand_obj = resolve_brand(brand_val, brand_cache)

                model_val = clean_text(get_row_val(row, 'model'))
                raw_type = clean_text(get_row_val(row, 'printer_type')) or ''
                model_obj = resolve_printer_model(brand_obj, model_val, raw_type, printer_model_cache)

                raw_device = clean_text(get_row_val(row, 'device'))
                if raw_device and raw_device.lower() not in ('printer', 'printers', 'device', 'default', 'n/a'):
                    device_name = raw_device
                else:
                    device_name = (model_obj.name if model_obj else model_val) or raw_device or 'Printer'

                ip_val = parse_ip(get_row_val(row, 'ip_address'))
                function_val = clean_text(get_row_val(row, 'printer_function'))
                status_val = normalize_status(get_row_val(row, 'status'))
                purchase_date_val = parse_date(get_row_val(row, 'purchase_date'))
                warranty_end_val = parse_date(get_row_val(row, 'warranty_end_date'))
                fiscal_year_val = clean_text(get_row_val(row, 'fiscal_year'))
                vendor_name_val = clean_text(get_row_val(row, 'vendor_name'))
                vendor_email_val = clean_text(get_row_val(row, 'vendor_email'))
                domain_val = clean_text(get_row_val(row, 'domain'))
                host_val = clean_text(get_row_val(row, 'host_name'))
                ims_val = clean_text(get_row_val(row, 'ims_code'))
                serial_val = clean_text(get_row_val(row, 'serial_no'))

                # Fast cache lookup for existing printer
                existing_prt = None
                if serial_val and serial_val.lower() in prt_serial_cache:
                    existing_prt = prt_serial_cache[serial_val.lower()]

                if existing_prt:
                    existing_prt.department = dept_obj or existing_prt.department
                    existing_prt.model = model_obj or existing_prt.model
                    if device_name and device_name.lower() != 'printer':
                        existing_prt.printer_name = device_name
                    elif not existing_prt.printer_name or existing_prt.printer_name.lower() == 'printer':
                        existing_prt.printer_name = (model_obj.name if model_obj else model_val) or device_name
                    if ims_val:
                        existing_prt.ims_code = ims_val
                    if ip_val:
                        existing_prt.ip_address = ip_val
                    if function_val:
                        existing_prt.printer_function = function_val
                    if purchase_date_val:
                        existing_prt.purchase_date = purchase_date_val
                    if warranty_end_val:
                        existing_prt.warranty_end_date = warranty_end_val
                    if fiscal_year_val:
                        existing_prt.fiscal_year = fiscal_year_val
                    if vendor_name_val:
                        existing_prt.vendor_name = vendor_name_val
                    if vendor_email_val:
                        existing_prt.vendor_email = vendor_email_val
                    if domain_val:
                        existing_prt.domain = domain_val
                    if host_val:
                        existing_prt.host_name = host_val
                    existing_prt.status = status_val
                    existing_prt.save()
                    updated_count += 1
                else:
                    new_prt = Printer.objects.create(
                        department=dept_obj,
                        model=model_obj,
                        printer_name=device_name,
                        ims_code=ims_val,
                        serial_no=serial_val,
                        ip_address=ip_val,
                        printer_function=function_val,
                        purchase_date=purchase_date_val,
                        warranty_end_date=warranty_end_val,
                        fiscal_year=fiscal_year_val,
                        vendor_name=vendor_name_val,
                        vendor_email=vendor_email_val,
                        domain=domain_val,
                        host_name=host_val,
                        status=status_val,
                    )
                    if serial_val:
                        prt_serial_cache[serial_val.lower()] = new_prt
                    created_count += 1

        except Exception as row_err:
            errors.append(f"Row {row_num}: {str(row_err)}")

    return {
        'success': True,
        'message': f'Processed {created_count + updated_count} printers successfully.',
        'created_count': created_count,
        'updated_count': updated_count,
        'total_processed': created_count + updated_count,
        'errors': errors[:20],
    }


class Command(BaseCommand):
    help = "Import printers from an Excel (.xlsx) or CSV file into the database."

    def add_arguments(self, parser):
        parser.add_argument("file_path", type=str, help="Path to the .xlsx or .csv file")

    def handle(self, *args, **options):
        filepath = options["file_path"]
        if not os.path.exists(filepath):
            raise CommandError(f"File not found: {filepath}")

        try:
            res = import_printers_data(filepath)
            self.stdout.write(self.style.SUCCESS(
                f"Successfully processed {res.get('total_processed', 0)} printers: "
                f"{res.get('created_count', 0)} created, {res.get('updated_count', 0)} updated."
            ))
            if res.get("errors"):
                self.stdout.write(self.style.WARNING("Notices / Errors:"))
                for err in res["errors"]:
                    self.stdout.write(f" - {err}")
        except Exception as exc:
            raise CommandError(f"Import failed: {exc}") from exc