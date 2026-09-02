import os
from django.core.management.base import BaseCommand, CommandError
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIRequestFactory
from api.import_views import BulkImportPrinterView


class Command(BaseCommand):
    help = "Import printers from an Excel (.xlsx) or CSV file into the database."

    def add_arguments(self, parser):
        parser.add_argument("file_path", type=str, help="Path to the .xlsx or .csv file")

    def handle(self, *args, **options):
        filepath = options["file_path"]
        if not os.path.exists(filepath):
            raise CommandError(f"File not found: {filepath}")

        try:
            with open(filepath, "rb") as f:
                content = f.read()

            filename = os.path.basename(filepath)
            uploaded_file = SimpleUploadedFile(
                filename,
                content,
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                if filename.endswith(".xlsx")
                else "text/csv",
            )

            factory = APIRequestFactory()
            request = factory.post("/api/printers/import-excel/", {"file": uploaded_file}, format="multipart")
            view = BulkImportPrinterView.as_view()
            response = view(request)

            if response.status_code == 200:
                data = response.data
                self.stdout.write(self.style.SUCCESS(
                    f"Successfully processed {data.get('total_processed', 0)} printers: "
                    f"{data.get('created_count', 0)} created, {data.get('updated_count', 0)} updated."
                ))
                if data.get("errors"):
                    self.stdout.write(self.style.WARNING("Notices / Errors:"))
                    for err in data["errors"]:
                        self.stdout.write(f" - {err}")
            else:
                self.stdout.write(self.style.ERROR(f"Import failed: {response.data}"))

        except Exception as exc:
            raise CommandError(f"Import failed: {exc}") from exc