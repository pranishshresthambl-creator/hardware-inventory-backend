from django.contrib import admin
from .models import Brand, Computer, ComputerModel, Department, Printer, PrinterModel


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    search_fields = ['name']


@admin.register(Computer)
class ComputerAdmin(admin.ModelAdmin):
    list_display = ['id', 'department', 'model__brand']
    list_filter = ['department', 'model__brand']
    # search_fields = ['name']


@admin.register(ComputerModel)
class ComputerModelAdmin(admin.ModelAdmin):
    list_display = ['id', 'brand', 'name']
    list_filter = ['brand']
    search_fields = ['name']

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    list_filter = ['name']
    search_fields = ['name']

@admin.register(Printer)
class PrinterAdmin(admin.ModelAdmin):
    list_display = ['id', 'printer_name']
    list_filter = ['printer_name']
    search_fields = ['printer_name']

@admin.register(PrinterModel)
class PrinterModelAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    list_filter = ['name']
    search_fields = ['name']