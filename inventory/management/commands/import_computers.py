import re
from datetime import date, datetime

import pandas as pd
from django.core.management.base import BaseCommand, CommandError

from inventory.models import Brand, Computer, ComputerModel, Department


RAM_MAP = {
    "4": "4GB", "4gb": "4GB", "4 gb": "4GB",
    "8": "8GB", "8gb": "8GB", "8 gb": "8GB",
    "16": "16GB", "16gb": "16GB", "16 gb": "16GB",
    "32": "32GB", "32gb": "32GB", "32 gb": "32GB",
}

STORAGE_MAP = {
    "128": "128 GB", "128gb": "128 GB", "128 gb": "128 GB",
    "256": "256 GB", "256gb": "256 GB", "256 gb": "256 GB",
    "512": "512 GB", "512gb": "512 GB", "512 gb": "512 GB",
    "1024": "1 TB", "1tb": "1 TB", "1 tb": "1 TB",
    "2048": "2 TB", "2tb": "2 TB", "2 tb": "2 TB",
    "1000": "1 TB",
}

OS_MAP = {
    "windows 10": "WINDOWS_10",
    "windows 11": "WINDOWS_11",
    "windows 7": "WINDOWS_7",
    "macos": "MACOS",
    "mac os": "MACOS",
}

STATUS_MAP = {
    "in use": "ACTIVE",
    "active": "ACTIVE",
    "inactive": "INACTIVE",
    "disposed": "DISPOSED",
    "repair": "REPAIR",
    "under repair": "REPAIR",
}

STORAGE_TYPE_KEYWORDS = {
    "ssd": "SSD",
    "nvme": "SSD",
    "hdd": "HDD",
    "hard disk": "HDD",
}

COMPUTER_TYPE_KEYWORDS = {
    "laptop": "LAPTOP",
    "notebook": "LAPTOP",
    "aio": "ALL_IN_ONE",
    "all in one": "ALL_IN_ONE",
    "all-in-one": "ALL_IN_ONE",
    "mini": "MINI_PC",
    "server": "SERVER",
}


def normalise_ram(value):
    return RAM_MAP.get(str(value).strip().lower(), "8GB")


def normalise_storage_capacity(value):
    cleaned = str(value).strip().lower().replace(",", "")
    key = re.sub(r"\s*gb$|\s*tb$", "", cleaned).strip()
    if cleaned.endswith("tb"):
        key = cleaned
    return STORAGE_MAP.get(cleaned, STORAGE_MAP.get(key, "512 GB"))


def normalise_os(value):
    raw = str(value).strip().lower()
    for keyword, code in OS_MAP.items():
        if keyword in raw:
            return code
    return "OTHER"


def normalise_status(value):
    return STATUS_MAP.get(str(value).strip().lower(), "ACTIVE")


def infer_storage_type(processor="", model_name=""):
    combined = (processor + " " + model_name).lower()
    for kw, st in STORAGE_TYPE_KEYWORDS.items():
        if kw in combined:
            return st
    return "HDD"  # default


def infer_computer_type(model_name=""):
    name = model_name.lower()
    for kw, ct in COMPUTER_TYPE_KEYWORDS.items():
        if kw in name:
            return ct
    return "DESKTOP" 


def parse_date(value):
    if pd.isna(value) or value == "" or value is None:
        return None
    if isinstance(value, (date, datetime)):
        return value if isinstance(value, date) else value.date()
    try:
        return datetime.strptime(str(value).strip(), "%Y-%m-%d").date()
    except ValueError:
        pass
    try:
        return datetime.strptime(str(value).strip(), "%d/%m/%Y").date()
    except ValueError:
        return None


def safe_str(value, fallback=""):
    if pd.isna(value) or value is None:
        return fallback
    return str(value).strip()


# ── Management command ───────────────────────────────────────────────────────

class Command(BaseCommand):
    help = "Import computers from an Excel file into the database."

    def add_arguments(self, parser):
        parser.add_argument("file", type=str, help="Path to the .xlsx file")
        parser.add_argument(
            "--sheet",
            type=str,
            default="Sheet1",
            help="Sheet name to read (default: Sheet1)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse and validate rows without writing to the database",
        )
        parser.add_argument(
            "--default-purchase-date",
            type=str,
            default=None,
            help="Fallback purchase date (YYYY-MM-DD) when the column is absent",
        )
        parser.add_argument(
            "--default-warranty-end-date",
            type=str,
            default=None,
            help="Fallback warranty end date (YYYY-MM-DD) when the column is absent",
        )


    COL = {
        "department":     ["Department"],
        "ims_code":       ["Asset ID", "IMS Code", "IMS_Code"],
        "serial_no":      ["Serial Number", "Serial No"],
        "brand":          ["Make/ Manufacturer", "Make/Manufacturer", "Brand", "Manufacturer"],
        "model":          ["Model"],
        "processor":      ["Processor Type and Speed", "Processor"],
        "ram":            ["RAM"],
        "storage_type":   ["Storage Type"],
        "storage_cap":    ["Storage Capacity", "Storage"],
        "ip_address":     ["IP Address"],
        "os":             ["Operating System", "OS"],
        "host_name":      ["Host Name", "Hostname"],
        "device_name":    ["Device Name"],
        "hotfix_id":      ["HotFix ID", "Hotfix ID"],
        "hotfix_date":    ["HotFix Date", "Hotfix Date"],
        "purchase_date":  ["Purchase Date"],
        "warranty_end":   ["Warranty End Date", "Warranty End"],
        "status":         ["Device Status", "Status"],
    }

    def _find_col(self, columns, key):
        """Return the first matching column name for a given alias group."""
        for alias in self.COL[key]:
            if alias in columns:
                return alias
        return None

    def handle(self, *args, **options):
        filepath = options["file"]
        sheet = options["sheet"]
        dry_run = options["dry_run"]


        try:
            df = pd.read_excel(filepath, sheet_name=sheet, dtype=str)
        except Exception as exc:
            raise CommandError(f"Cannot read file: {exc}") from exc

        df = df.where(pd.notna(df), None)
        columns = df.columns.tolist()

        col = {key: self._find_col(columns, key) for key in self.COL}

        created = skipped = updated = 0

        for idx, row in df.iterrows():
            row_num = idx + 2  

            def get(key, fallback=""):
                c = col[key]
                return safe_str(row[c], fallback) if c else fallback

            ims_code = get("ims_code")
            serial_no = get("serial_no")

            if not ims_code and not serial_no:
                self.stdout.write(
                    self.style.WARNING(f"Row {row_num}: no IMS code or serial number — skipped")
                )
                skipped += 1
                continue

            # ── Related objects ──────────────────────────────────────────────

            dept_name = get("department", "Unknown").strip().upper()
            brand_name = get("brand", "Unknown").strip().upper()
            model_name = get("model", "Unknown").strip().upper()
            processor = get("processor").strip().upper()
            computer_type = infer_computer_type(model_name)

            if not dry_run:
                department, _ = Department.objects.get_or_create(name=dept_name)
                brand, _ = Brand.objects.get_or_create(name=brand_name)
                computer_model, _ = ComputerModel.objects.get_or_create(
                    brand=brand,
                    name=model_name,
                    defaults={"computer_type": computer_type},
                )

            # ── Field normalisation ──────────────────────────────────────────

            ram = normalise_ram(get("ram", "8GB"))

            storage_type_raw = get("storage_type")
            storage_type = (
                normalise_storage_type_raw(storage_type_raw)
                if storage_type_raw
                else infer_storage_type(processor, model_name)
            )

            storage_capacity = normalise_storage_capacity(get("storage_cap", "512 GB"))
            operating_system = normalise_os(get("os", ""))
            status = normalise_status(get("status", "active"))
            ip_address = get("ip_address") or None
            host_name = get("host_name") or None
            hotfix_id = get("hotfix_id") or None
            hotfix_date = parse_date(row[col["hotfix_date"]]) if col["hotfix_date"] else None

            fields = {
                "model": None if dry_run else computer_model,
                "department": None if dry_run else department,
                "processor": processor,
                "ram": ram,
                "storage_type": storage_type,
                "storage_capacity": storage_capacity,
                "ip_address": ip_address,
                "operating_system": operating_system,
                "host_name": host_name,
                "hotfix_id": hotfix_id,
                "hotfix_date": hotfix_date,
                "status": status,
            }

            if dry_run:
                self.stdout.write(
                    f"Row {row_num} [DRY RUN]: ims_code={ims_code} serial={serial_no} "
                    f"brand={brand_name} model={model_name} dept={dept_name} "
                    f"ram={ram} storage={storage_capacity} os={operating_system} status={status}"
                )
                created += 1
                continue

            # ── Create or update ─────────────────────────────────────────────

            lookup = {}
            if ims_code:
                lookup["ims_code"] = ims_code
            elif serial_no:
                lookup["serial_no"] = serial_no

            try:
                obj, was_created = Computer.objects.update_or_create(
                    **lookup,
                    defaults={**fields, "serial_no": serial_no, **lookup},
                )
                if was_created:
                    created += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"Row {row_num}: Created Computer {obj.ims_code}")
                    )
                else:
                    updated += 1
                    self.stdout.write(
                        f"Row {row_num}: Updated Computer {obj.ims_code}"
                    )
            except Exception as exc:
                skipped += 1
                self.stdout.write(
                    self.style.ERROR(f"Row {row_num}: Error — {exc}")
                )

        label = "[DRY RUN] " if dry_run else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"\n{label}Done — created: {created}, updated: {updated}, skipped: {skipped}"
            )
        )


def normalise_storage_type_raw(value):
    val = str(value).strip().lower()
    for kw, st in STORAGE_TYPE_KEYWORDS.items():
        if kw in val:
            return st
    return "HDD"