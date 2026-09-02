from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0018_alter_computer_status_alter_printer_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='computer',
            name='processor',
            field=models.CharField(blank=True, max_length=150, null=True),
        ),
        migrations.AlterField(
            model_name='computer',
            name='ram',
            field=models.CharField(blank=True, choices=[('4GB', '4 GB'), ('8GB', '8 GB'), ('16GB', '16 GB'), ('32GB', '32 GB')], max_length=20, null=True),
        ),
        migrations.AlterField(
            model_name='computer',
            name='storage_type',
            field=models.CharField(blank=True, choices=[('HDD', 'HDD'), ('SSD', 'SSD')], max_length=20, null=True),
        ),
        migrations.AlterField(
            model_name='computer',
            name='storage_capacity',
            field=models.CharField(blank=True, choices=[('128 GB', '128 GB'), ('256 GB', '256 GB'), ('512 GB', '512 GB'), ('1 TB', '1 TB'), ('2 TB', '2 TB')], max_length=30, null=True),
        ),
        migrations.AlterField(
            model_name='computer',
            name='operating_system',
            field=models.CharField(blank=True, choices=[('WINDOWS_10', 'Windows 10'), ('WINDOWS_11', 'Windows 11'), ('WINDOWS_7', 'Windows 7'), ('MACOS', 'macOS'), ('OTHER', 'Other')], max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='computer',
            name='status',
            field=models.CharField(blank=True, choices=[('ACTIVE', 'Active'), ('INACTIVE', 'Inactive'), ('REPAIR', 'Under Repair'), ('DISPOSED', 'Disposed')], default='ACTIVE', max_length=20, null=True),
        ),
    ]
