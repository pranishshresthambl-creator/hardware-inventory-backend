from django.db import models
from django.utils import timezone

# Create your models here.

class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, default='ACTIVE')
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        """
        Soft delete instead of hard delete
        """
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

class Department(BaseModel):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Brand(BaseModel):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class ComputerModel(BaseModel):
    COMPUTER_TYPE_CHOICES = [
        ('DESKTOP', 'Desktop'),
        ('LAPTOP', 'Laptop'),
        ('ALL_IN_ONE', 'All In One'),
        ('MINI_PC', 'Mini PC'),
        ('SERVER', 'Server'),
    ]

    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)
    name = models.CharField(max_length=150)
    computer_type = models.CharField(
        max_length=20,
        choices=COMPUTER_TYPE_CHOICES
    )

    def __str__(self):
        return f"{self.brand.name} - {self.name}"

class Computer(BaseModel):

    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('REPAIR', 'Under Repair'),
        ('DISPOSED', 'Disposed'),
    ]

    department = models.ForeignKey('Department', on_delete=models.SET_NULL, null=True)
    ims_code = models.CharField(max_length=50, null=True)
    model = models.ForeignKey(ComputerModel, on_delete=models.SET_NULL, null=True)
    serial_no = models.CharField(max_length=100, null=True)
    processor = models.CharField(max_length=100)

    RAM_CHOICES = [
        ('4GB', '4 GB'),
        ('8GB', '8 GB'),
        ('16GB', '16 GB'),
        ('32GB', '32 GB'),
    ]

    ram = models.CharField(max_length=10, choices=RAM_CHOICES)

    STORAGE_TYPE = [
        ('HDD', 'HDD'),
        ('SSD', 'SSD'),
    ]

    storage_type = models.CharField(max_length=10, choices=STORAGE_TYPE)

    STORAGE_CHOICES = [
        ('128 GB', '128 GB'),
        ('256 GB', '256 GB'),
        ('512 GB', '512 GB'),
        ('1 TB', '1 TB'),
        ('2 TB', '2 TB'),
    ]

    storage_capacity = models.CharField(max_length=10, choices=STORAGE_CHOICES)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    OPERATING_SYSTEM_CHOICES = [
        ('WINDOWS_10', 'Windows 10'),
        ('WINDOWS_11', 'Windows 11'),
        ('WINDOWS_7', 'Windows 7'),
        ('MACOS', 'macOS'),
        ('OTHER', 'Other'),
    ]

    operating_system = models.CharField(
        max_length=30,
        choices=OPERATING_SYSTEM_CHOICES
    )

    host_name = models.CharField(max_length=150, null=True, blank=True)
    hotfix_id = models.CharField(max_length=100, blank=True, null=True)
    hotfix_date = models.DateField(blank=True, null=True)

    purchase_date = models.DateField(null=True)
    warranty_end_date = models.DateField(null=True)
    
    fiscal_year = models.CharField(max_length=20, null=True, blank=True)
    vendor_name = models.CharField(max_length=200, null=True, blank=True)
    contact_person = models.CharField(max_length=100, null=True, blank=True)
    office_address = models.CharField(max_length=200, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    vendor_email = models.EmailField(null=True, blank=True)
    domain = models.CharField(max_length=150, null=True, blank=True)
    installed_applications = models.TextField(null=True, blank=True)
    antivirus = models.CharField(max_length=200, null=True, blank=True)
    security_hardening = models.TextField(null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')

    def __str__(self):
        return self.ims_code

class PrinterModel(BaseModel):

    PRINTER_TYPE_CHOICES = [
        ('LASER', 'Laser'),
        ('INKJET', 'Inkjet'),
        ('DOT_MATRIX', 'Dot Matrix'),
        ('THERMAL', 'Thermal'),
        ('OTHER', 'Other'),
    ]
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)
    name = models.CharField(max_length=150)
    printer_type = models.CharField(
        max_length=20,
        choices=PRINTER_TYPE_CHOICES
    )

    def __str__(self):
        return f"{self.brand.name} - {self.name}"

class Printer(BaseModel):

    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('REPAIR', 'Under Repair'),
        ('DISPOSED', 'Disposed'),
    ]

    department = models.ForeignKey('Department', on_delete=models.SET_NULL, null=True)
    ims_code = models.CharField(max_length=50, null=True)
    printer_name = models.CharField(max_length=100)
    model = models.ForeignKey(PrinterModel, on_delete=models.SET_NULL, null=True)
    serial_no = models.CharField(max_length=100, unique=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    printer_function = models.CharField(max_length=100, null=True, blank=True)
    purchase_date = models.DateField(null=True)
    warranty_end_date = models.DateField(null=True)
    
    fiscal_year = models.CharField(max_length=20, null=True, blank=True)
    vendor_name = models.CharField(max_length=200, null=True, blank=True)
    contact_person = models.CharField(max_length=100, null=True, blank=True)
    office_address = models.CharField(max_length=200, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    vendor_email = models.EmailField(null=True, blank=True)
    domain = models.CharField(max_length=150, null=True, blank=True)
    installed_applications = models.TextField(null=True, blank=True)
    antivirus = models.CharField(max_length=200, null=True, blank=True)
    security_hardening = models.TextField(null=True, blank=True)
    host_name = models.CharField(max_length=150, null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')

    def __str__(self):
        return self.ims_code

class Vendor(BaseModel):
    name = models.CharField(max_length=200)
    address = models.CharField(max_length=200, null=True, blank=True)
    contact_person = models.CharField(max_length=100, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)

    def __str__(self):
        return self.name

class ComputerLog(BaseModel):
    LOG_TYPE_CHOICES = [
        ('UPDATE', 'Update'),
        ('ERROR', 'Error'),
        ('MAINTENANCE', 'Maintenance'),
        ('ASSIGNMENT', 'Assignment'),
        ('SECURITY', 'Security'),
        ('OTHER', 'Other'),
    ]

    RESOLUTION_STATUS_CHOICES = [
        ('RESOLVED', 'Resolved'),
        ('UNRESOLVED', 'Unresolved'),
        ('IN_PROGRESS', 'In Progress'),
    ]

    log_id = models.CharField(max_length=50, blank=True, null=True)
    computer = models.ForeignKey(Computer, on_delete=models.CASCADE, null=True, blank=True, related_name='logs')
    computer_ims = models.CharField(max_length=100, null=True, blank=True)
    log_type = models.CharField(max_length=30, choices=LOG_TYPE_CHOICES, default='UPDATE')
    description = models.TextField()
    authorized_by = models.CharField(max_length=150, null=True, blank=True)
    performer_role = models.CharField(max_length=150, null=True, blank=True, default='Senior Systems Administrator')
    assigned_user = models.CharField(max_length=150, null=True, blank=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    action_source = models.CharField(max_length=100, null=True, blank=True, default='Team Viewer')
    start_time = models.CharField(max_length=50, null=True, blank=True)
    end_time = models.CharField(max_length=50, null=True, blank=True)
    log_date = models.DateTimeField(default=timezone.now)
    resolution_status = models.CharField(max_length=30, choices=RESOLUTION_STATUS_CHOICES, default='RESOLVED')
    action_taken = models.TextField(null=True, blank=True)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new and not self.log_id:
            year = self.log_date.year if self.log_date else timezone.now().year
            self.log_id = f"LOG-{year}-{8800 + self.id}"
            ComputerLog.objects.filter(pk=self.pk).update(log_id=self.log_id)

    def __str__(self):
        ims = self.computer_ims or (self.computer.ims_code if self.computer else 'General')
        return f"[{self.log_id or self.log_type}] {ims} - {self.description[:40]}"