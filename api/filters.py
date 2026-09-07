import django_filters
from django.db.models import Q
from inventory.models import (
    Computer,
    Printer,
    ComputerLog,
    Brand,
    Department,
    ComputerModel,
    PrinterModel,
)
from django.contrib.auth.models import User


class ComputerFilter(django_filters.FilterSet):
    department = django_filters.CharFilter(method='filter_department')
    brand = django_filters.CharFilter(method='filter_brand')
    model = django_filters.CharFilter(method='filter_model')
    status = django_filters.CharFilter(field_name='status', lookup_expr='iexact')
    ram = django_filters.CharFilter(field_name='ram', lookup_expr='iexact')
    storage_type = django_filters.CharFilter(field_name='storage_type', lookup_expr='iexact')
    operating_system = django_filters.CharFilter(method='filter_os')
    processor = django_filters.CharFilter(field_name='processor', lookup_expr='icontains')

    class Meta:
        model = Computer
        fields = [
            'department',
            'brand',
            'model',
            'status',
            'ram',
            'storage_type',
            'operating_system',
            'processor',
        ]

    def filter_department(self, queryset, name, value):
        if not value:
            return queryset
        val_str = str(value).strip()
        if val_str.isdigit():
            return queryset.filter(Q(department_id=int(val_str)) | Q(department__name__iexact=val_str))
        return queryset.filter(department__name__icontains=val_str)

    def filter_brand(self, queryset, name, value):
        if not value:
            return queryset
        val_str = str(value).strip()
        if val_str.isdigit():
            return queryset.filter(Q(model__brand_id=int(val_str)) | Q(model__brand__name__iexact=val_str))
        return queryset.filter(model__brand__name__icontains=val_str)

    def filter_model(self, queryset, name, value):
        if not value:
            return queryset
        val_str = str(value).strip()
        if val_str.isdigit():
            return queryset.filter(Q(model_id=int(val_str)) | Q(model__name__iexact=val_str))
        return queryset.filter(model__name__icontains=val_str)

    def filter_os(self, queryset, name, value):
        if not value:
            return queryset
        val_str = str(value).strip()
        return queryset.filter(
            Q(operating_system__iexact=val_str) |
            Q(operating_system__icontains=val_str.replace(' ', '_')) |
            Q(operating_system__icontains=val_str)
        )


class PrinterFilter(django_filters.FilterSet):
    department = django_filters.CharFilter(method='filter_department')
    brand = django_filters.CharFilter(method='filter_brand')
    model = django_filters.CharFilter(method='filter_model')
    status = django_filters.CharFilter(field_name='status', lookup_expr='iexact')
    printer_function = django_filters.CharFilter(field_name='printer_function', lookup_expr='icontains')

    class Meta:
        model = Printer
        fields = [
            'department',
            'brand',
            'model',
            'status',
            'printer_function',
        ]

    def filter_department(self, queryset, name, value):
        if not value:
            return queryset
        val_str = str(value).strip()
        if val_str.isdigit():
            return queryset.filter(Q(department_id=int(val_str)) | Q(department__name__iexact=val_str))
        return queryset.filter(department__name__icontains=val_str)

    def filter_brand(self, queryset, name, value):
        if not value:
            return queryset
        val_str = str(value).strip()
        if val_str.isdigit():
            return queryset.filter(Q(model__brand_id=int(val_str)) | Q(model__brand__name__iexact=val_str))
        return queryset.filter(model__brand__name__icontains=val_str)

    def filter_model(self, queryset, name, value):
        if not value:
            return queryset
        val_str = str(value).strip()
        if val_str.isdigit():
            return queryset.filter(Q(model_id=int(val_str)) | Q(model__name__iexact=val_str))
        return queryset.filter(model__name__icontains=val_str)


class ComputerLogFilter(django_filters.FilterSet):
    department = django_filters.CharFilter(method='filter_department')
    log_type = django_filters.CharFilter(field_name='log_type', lookup_expr='iexact')
    resolution_status = django_filters.CharFilter(field_name='resolution_status', lookup_expr='iexact')
    computer = django_filters.CharFilter(method='filter_computer')
    tab = django_filters.CharFilter(method='filter_tab')

    class Meta:
        model = ComputerLog
        fields = [
            'department',
            'log_type',
            'resolution_status',
            'computer',
            'tab',
        ]

    def filter_department(self, queryset, name, value):
        if not value:
            return queryset
        val_str = str(value).strip()
        if val_str.isdigit():
            return queryset.filter(Q(department_id=int(val_str)) | Q(department__name__iexact=val_str))
        return queryset.filter(department__name__icontains=val_str)

    def filter_computer(self, queryset, name, value):
        if not value:
            return queryset
        val_str = str(value).strip()
        if val_str.isdigit():
            return queryset.filter(Q(computer_id=int(val_str)) | Q(computer__ims_code__iexact=val_str))
        return queryset.filter(
            Q(computer__ims_code__icontains=val_str) |
            Q(computer_ims__icontains=val_str) |
            Q(computer__host_name__icontains=val_str)
        )

    def filter_tab(self, queryset, name, value):
        if not value:
            return queryset
        val_upper = str(value).strip().upper()
        if val_upper == 'USER_REPORTS':
            return queryset.filter(
                Q(action_source='Help Portal') |
                Q(performer_role='Help Desk User Submission')
            )
        elif val_upper in ('UNRESOLVED', 'IN_PROGRESS', 'RESOLVED'):
            return queryset.filter(resolution_status=val_upper)
        return queryset


class BrandFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name='status', lookup_expr='iexact')

    class Meta:
        model = Brand
        fields = ['status']


class DepartmentFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name='status', lookup_expr='iexact')

    class Meta:
        model = Department
        fields = ['status']


class ComputerModelFilter(django_filters.FilterSet):
    brand = django_filters.CharFilter(method='filter_brand')
    computer_type = django_filters.CharFilter(field_name='computer_type', lookup_expr='iexact')
    status = django_filters.CharFilter(field_name='status', lookup_expr='iexact')

    class Meta:
        model = ComputerModel
        fields = ['brand', 'computer_type', 'status']

    def filter_brand(self, queryset, name, value):
        if not value:
            return queryset
        val_str = str(value).strip()
        if val_str.isdigit():
            return queryset.filter(Q(brand_id=int(val_str)) | Q(brand__name__iexact=val_str))
        return queryset.filter(brand__name__icontains=val_str)


class PrinterModelFilter(django_filters.FilterSet):
    brand = django_filters.CharFilter(method='filter_brand')
    printer_type = django_filters.CharFilter(field_name='printer_type', lookup_expr='iexact')
    status = django_filters.CharFilter(field_name='status', lookup_expr='iexact')

    class Meta:
        model = PrinterModel
        fields = ['brand', 'printer_type', 'status']

    def filter_brand(self, queryset, name, value):
        if not value:
            return queryset
        val_str = str(value).strip()
        if val_str.isdigit():
            return queryset.filter(Q(brand_id=int(val_str)) | Q(brand__name__iexact=val_str))
        return queryset.filter(brand__name__icontains=val_str)


class UserFilter(django_filters.FilterSet):
    role = django_filters.CharFilter(method='filter_role')
    is_active = django_filters.BooleanFilter(field_name='is_active')

    class Meta:
        model = User
        fields = ['role', 'is_active']

    def filter_role(self, queryset, name, value):
        if not value:
            return queryset
        val_lower = str(value).strip().lower()
        if 'super' in val_lower:
            return queryset.filter(is_superuser=True)
        elif 'admin' in val_lower:
            return queryset.filter(is_staff=True, is_superuser=False)
        elif 'user' in val_lower:
            return queryset.filter(is_staff=False, is_superuser=False)
        return queryset
