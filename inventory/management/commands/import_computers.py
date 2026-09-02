import os
import re
import datetime
import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from inventory.models import (
    Department,
    Brand,
    ComputerModel,
    Computer,
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


def normalize_ram(val):
    cleaned = clean_text(val)
    if not cleaned:
        return None
    low = cleaned.lower()
    if '32' in low:
        return '32GB'
    if '16' in low:
        return '16GB'
    if '8' in low:
        return '8GB'
    if '4' in low:
        return '4GB'
    return None


def normalize_storage(val):
    cleaned = clean_text(val)
    if not cleaned:
        return None, None
    low = cleaned.lower()
    st_type = None
    if 'ssd' in low or 'nvme' in low or 'm.2' in low:
        st_type = 'SSD'
    elif 'hdd' in low or 'hard disk' in low:
        st_type = 'HDD'

    cap = None
    if '2 tb' in low or '2tb' in low or '2048' in low:
        cap = '2 TB'
    elif '1 tb' in low or '1tb' in low or '1024' in low or '1000' in low:
        cap = '1 TB'
    elif '512' in low or '500' in low:
        cap = '512 GB'
    elif '256' in low or '240' in low or '250' in low:
        cap = '256 GB'
    elif '128' in low or '120' in low:
        cap = '128 GB'

    return cap, st_type


def normalize_os(val):
    cleaned = clean_text(val)
    if not cleaned:
        return None
    low = cleaned.lower()
    if '11' in low:
        return 'WINDOWS_11'
    if '10' in low:
        return 'WINDOWS_10'
    if '7' in low:
        return 'WINDOWS_7'
    if 'mac' in low or 'apple' in low or 'osx' in low:
        return 'MACOS'
    return 'OTHER'


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


def resolve_computer_model(brand_obj, model_name, raw_processor='', cache=None):
    cleaned_model = clean_text(model_name) or 'Optiplex Desktop'
    if not brand_obj:
        brand_obj = resolve_brand('HP', cache)

    key = (brand_obj.id if brand_obj else None, cleaned_model.lower())
    if cache is not None and key in cache:
        return cache[key]

    low = (cleaned_model + ' ' + (raw_processor or '')).lower()
    if any(k in low for k in ['aio', 'all in one', 'all-in-one', 'proone', 'ideacentre']):
        comp_type = 'ALL_IN_ONE'
    elif any(k in low for k in ['laptop', 'notebook', 'thinkpad', 'latitude', 'elitebook', 'probook', 'vostro laptop', 'inspiron laptop']):
        comp_type = 'LAPTOP'
    elif any(k in low for k in ['server', 'poweredge', 'proliant']):
        comp_type = 'SERVER'
    elif any(k in low for k in ['mini', 'tiny', 'nuc', 'micro']):
        comp_type = 'MINI_PC'
    else:
        comp_type = 'DESKTOP'

    existing = ComputerModel.objects.filter(brand=brand_obj, name__iexact=cleaned_model).first()
    if not existing:
        existing = ComputerModel.objects.create(
            brand=brand_obj,
            name=cleaned_model,
            computer_type=comp_type
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


def import_computers_data(file_or_path):
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
            if s_clean in ('computers', 'computer', 'desktops', 'laptops', 'pcs'):
                sheet_target = s
                break
        if not sheet_target:
            for s in excel_file.sheet_names:
                s_clean = s.strip().lower()
                if ('comp' in s_clean or 'desktop' in s_clean or 'laptop' in s_clean) and 'print' not in s_clean:
                    sheet_target = s
                    break
        if not sheet_target:
            for s in excel_file.sheet_names:
                if 'print' not in s.strip().lower():
                    sheet_target = s
                    break
        if not sheet_target:
            sheet_target = excel_file.sheet_names[0]
        df = pd.read_excel(excel_file, sheet_name=sheet_target)

    # Standardize column headers
    col_map = {}
    for col in df.columns:
        c_clean = str(col).strip().lower()
        if 'host' in c_clean:
            col_map[col] = 'host_name'
        elif 'department' in c_clean or 'dept' in c_clean:
            col_map[col] = 'department'
        elif 'asset' in c_clean or 'ims' in c_clean:
            col_map[col] = 'ims_code'
        elif 'device' in c_clean:
            col_map[col] = 'device_type'
        elif 'serial' in c_clean:
            col_map[col] = 'serial_no'
        elif 'make' in c_clean or 'brand' in c_clean or 'manufacturer' in c_clean:
            col_map[col] = 'brand'
        elif 'model' in c_clean:
            col_map[col] = 'model'
        elif 'processor' in c_clean or 'cpu' in c_clean:
            col_map[col] = 'processor'
        elif 'ram' in c_clean or 'memory' in c_clean:
            col_map[col] = 'ram'
        elif 'storage capacity' in c_clean or 'capacity' in c_clean:
            col_map[col] = 'storage_capacity'
        elif 'storage type' in c_clean or 'storage_type' in c_clean:
            col_map[col] = 'storage_type'
        elif 'storage' in c_clean or 'disk' in c_clean or 'hdd' in c_clean or 'ssd' in c_clean:
            col_map[col] = 'storage'
        elif 'operating' in c_clean or c_clean == 'os' or ' os ' in f" {c_clean} " or 'os_' in c_clean:
            col_map[col] = 'os'
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
        elif 'antivirus' in c_clean:
            col_map[col] = 'antivirus'
        elif 'installed' in c_clean or ('app' in c_clean and 'apple' not in c_clean):
            col_map[col] = 'installed_applications'
        elif 'hardening date' in c_clean or 'lasthardening' in c_clean:
            col_map[col] = 'hotfix_date'
        elif 'hardening' in c_clean or 'security' in c_clean:
            col_map[col] = 'security_hardening'
        elif 'hotfix id' in c_clean or 'hotfix_id' in c_clean:
            col_map[col] = 'hotfix_id'
        elif 'hotfix date' in c_clean or 'hotfix_date' in c_clean:
            col_map[col] = 'hotfix_date'
        elif 'ip' in c_clean:
            col_map[col] = 'ip_address'
        elif 'status' in c_clean:
            col_map[col] = 'status'
        elif 'user' in c_clean or 'assigned' in c_clean:
            col_map[col] = 'user'
        elif 'performed' in c_clean or 'admin' in c_clean:
            col_map[col] = 'authorized_by'
        elif 'remarks' in c_clean:
            col_map[col] = 'remarks'

    df = df.rename(columns=col_map)

    created_count = 0
    updated_count = 0
    errors = []

    # Pre-cache database entities in memory for ultra-fast processing
    dept_cache = {d.name.upper(): d for d in Department.objects.all()}
    brand_cache = {b.name.lower(): b for b in Brand.objects.all()}
    model_cache = {(m.brand_id, m.name.lower()): m for m in ComputerModel.objects.all()}
    comp_serial_cache = {c.serial_no.lower(): c for c in Computer.objects.exclude(serial_no=None).exclude(serial_no='')}
    comp_host_cache = {c.host_name.lower(): c for c in Computer.objects.exclude(host_name=None).exclude(host_name='')}

    for idx, row in df.iterrows():
        row_num = idx + 2
        try:
            device_type_raw = get_row_val(row, 'device_type')
            ims_raw = get_row_val(row, 'ims_code')
            model_raw = get_row_val(row, 'model')

            # Strictly skip rows that are printer devices
            if is_printer_device(device_type_raw, ims_raw, model_raw) and not is_computer_device(device_type_raw, ims_raw, model_raw):
                continue

            with transaction.atomic():
                dept_val = get_row_val(row, 'department')
                dept_obj = resolve_department(dept_val, dept_cache)

                brand_val = get_row_val(row, 'brand')
                brand_obj = resolve_brand(brand_val, brand_cache)

                proc_val = clean_text(get_row_val(row, 'processor'))
                model_val = clean_text(get_row_val(row, 'model'))
                device_type_val = clean_text(get_row_val(row, 'device_type')) or 'DESKTOP'
                model_obj = resolve_computer_model(brand_obj, model_val, device_type_val, model_cache)

                raw_ram = get_row_val(row, 'ram')
                ram_val = normalize_ram(raw_ram)

                raw_storage_cap = get_row_val(row, 'storage_capacity')
                raw_storage_type = get_row_val(row, 'storage_type')
                raw_storage = get_row_val(row, 'storage')

                if raw_storage_cap:
                    storage_cap, st_from_cap = normalize_storage(raw_storage_cap)
                    storage_type = clean_text(raw_storage_type) or st_from_cap or 'SSD'
                else:
                    storage_cap, storage_type = normalize_storage(raw_storage)

                raw_os = get_row_val(row, 'os')
                os_val = normalize_os(raw_os)

                ip_val = parse_ip(get_row_val(row, 'ip_address'))
                host_val = clean_text(get_row_val(row, 'host_name'))
                serial_val = clean_text(get_row_val(row, 'serial_no'))
                ims_val = clean_text(get_row_val(row, 'ims_code'))
                status_val = normalize_status(get_row_val(row, 'status'))
                hotfix_id_val = clean_text(get_row_val(row, 'hotfix_id'))
                hotfix_date_val = parse_date(get_row_val(row, 'hotfix_date'))
                purchase_date_val = parse_date(get_row_val(row, 'purchase_date'))
                warranty_end_val = parse_date(get_row_val(row, 'warranty_end_date'))
                fiscal_year_val = clean_text(get_row_val(row, 'fiscal_year'))
                vendor_name_val = clean_text(get_row_val(row, 'vendor_name'))
                vendor_email_val = clean_text(get_row_val(row, 'vendor_email'))
                domain_val = clean_text(get_row_val(row, 'domain'))
                antivirus_val = clean_text(get_row_val(row, 'antivirus'))
                installed_apps_val = clean_text(get_row_val(row, 'installed_applications'))
                security_hardening_val = clean_text(get_row_val(row, 'security_hardening'))

                # Fast cache lookup for existing computer
                existing_comp = None
                if serial_val and serial_val.lower() in comp_serial_cache:
                    existing_comp = comp_serial_cache[serial_val.lower()]
                elif host_val and host_val.lower() in comp_host_cache:
                    existing_comp = comp_host_cache[host_val.lower()]

                if existing_comp:
                    existing_comp.department = dept_obj or existing_comp.department
                    existing_comp.model = model_obj or existing_comp.model
                    if ims_val:
                        existing_comp.ims_code = ims_val
                    if serial_val:
                        existing_comp.serial_no = serial_val
                    if proc_val:
                        existing_comp.processor = proc_val
                    if ram_val:
                        existing_comp.ram = ram_val
                    if storage_cap:
                        existing_comp.storage_capacity = storage_cap
                    if storage_type:
                        existing_comp.storage_type = storage_type
                    if os_val:
                        existing_comp.operating_system = os_val
                    if ip_val:
                        existing_comp.ip_address = ip_val
                    if host_val:
                        existing_comp.host_name = host_val
                    if hotfix_id_val:
                        existing_comp.hotfix_id = hotfix_id_val
                    if hotfix_date_val:
                        existing_comp.hotfix_date = hotfix_date_val
                    if purchase_date_val:
                        existing_comp.purchase_date = purchase_date_val
                    if warranty_end_val:
                        existing_comp.warranty_end_date = warranty_end_val
                    if fiscal_year_val:
                        existing_comp.fiscal_year = fiscal_year_val
                    if vendor_name_val:
                        existing_comp.vendor_name = vendor_name_val
                    if vendor_email_val:
                        existing_comp.vendor_email = vendor_email_val
                    if domain_val:
                        existing_comp.domain = domain_val
                    if antivirus_val:
                        existing_comp.antivirus = antivirus_val
                    if installed_apps_val:
                        existing_comp.installed_applications = installed_apps_val
                    if security_hardening_val:
                        existing_comp.security_hardening = security_hardening_val
                    existing_comp.status = status_val
                    existing_comp.save()
                    updated_count += 1
                else:
                    new_comp = Computer.objects.create(
                        department=dept_obj,
                        model=model_obj,
                        ims_code=ims_val,
                        serial_no=serial_val,
                        processor=proc_val,
                        ram=ram_val,
                        storage_capacity=storage_cap,
                        storage_type=storage_type,
                        operating_system=os_val,
                        ip_address=ip_val,
                        host_name=host_val,
                        hotfix_id=hotfix_id_val,
                        hotfix_date=hotfix_date_val,
                        purchase_date=purchase_date_val,
                        warranty_end_date=warranty_end_val,
                        fiscal_year=fiscal_year_val,
                        vendor_name=vendor_name_val,
                        vendor_email=vendor_email_val,
                        domain=domain_val,
                        antivirus=antivirus_val,
                        installed_applications=installed_apps_val,
                        security_hardening=security_hardening_val,
                        status=status_val,
                    )
                    if serial_val:
                        comp_serial_cache[serial_val.lower()] = new_comp
                    if host_val:
                        comp_host_cache[host_val.lower()] = new_comp
                    created_count += 1

        except Exception as row_err:
            errors.append(f"Row {row_num}: {str(row_err)}")

    return {
        'success': True,
        'message': f'Processed {created_count + updated_count} computers successfully.',
        'created_count': created_count,
        'updated_count': updated_count,
        'total_processed': created_count + updated_count,
        'errors': errors[:20],
    }


class Command(BaseCommand):
    help = "Import computers from an Excel (.xlsx) or CSV file into the database."

    def add_arguments(self, parser):
        parser.add_argument("file", type=str, help="Path to the .xlsx or .csv file")

    def handle(self, *args, **options):
        filepath = options["file"]
        if not os.path.exists(filepath):
            raise CommandError(f"File not found: {filepath}")

        try:
            res = import_computers_data(filepath)
            self.stdout.write(self.style.SUCCESS(
                f"Successfully processed {res.get('total_processed', 0)} computers: "
                f"{res.get('created_count', 0)} created, {res.get('updated_count', 0)} updated."
            ))
            if res.get("errors"):
                self.stdout.write(self.style.WARNING("Notices / Errors:"))
                for err in res["errors"]:
                    self.stdout.write(f" - {err}")
        except Exception as exc:
            raise CommandError(f"Import failed: {exc}") from exc