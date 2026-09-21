from django.core.management.base import BaseCommand
from inventory.models import Computer, ComputerLog, DisposalRecord


class Command(BaseCommand):
    help = 'Remove all Computer records (and associated logs) from the database while keeping models, brands, and departments.'

    def handle(self, *args, **options):
        # Count existing records
        total_computers = Computer.objects.count()
        total_logs = ComputerLog.objects.count()

        if total_computers == 0:
            self.stdout.write(self.style.WARNING('No computers found in the database.'))
            return

        self.stdout.write(f'Found {total_computers} computers and {total_logs} computer logs.')

        # Delete computer logs first (if any)
        ComputerLog.objects.all().delete()

        # Delete all computers completely
        deleted_count, _ = Computer.objects.all().delete()

        self.stdout.write(self.style.SUCCESS(f'Successfully removed all {total_computers} computers from the database!'))
        self.stdout.write(self.style.SUCCESS('Brands, Departments, and Computer Models remain intact.'))
