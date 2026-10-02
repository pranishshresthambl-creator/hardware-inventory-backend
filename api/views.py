from django.contrib.auth import authenticate
from django.utils import timezone
from django.db.models import Q, Case, When, Value, IntegerField

from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework import status, permissions, filters

# Simple JWT Autnetication  
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from django_filters.rest_framework import DjangoFilterBackend

from inventory.models import (
    Computer,
    ComputerModel,
    Printer,
    PrinterModel,
    Brand,
    Department,
    ComputerLog,
    DisposalRecord,
)

from rest_framework.decorators import action
from django.contrib.auth.models import User

from .serializers import (
    ComputerSerializer,
    ComputerModelSerializer,
    PrinterSerializer,
    PrinterModelSerializer,
    BrandSerializer,
    DepartmentSerializer,
    UserSerializer,
    ComputerLogSerializer,
    DisposalRecordSerializer,
)
from .filters import (
    ComputerFilter,
    PrinterFilter,
    ComputerLogFilter,
    BrandFilter,
    DepartmentFilter,
    ComputerModelFilter,
    PrinterModelFilter,
    UserFilter,
)


class LoginAPIView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            username = request.data.get('username')
            user = User.objects.filter(username=username).first()
            if user:
                user.last_login = timezone.now()
                user.save(update_fields=['last_login'])
                response.data['user'] = {
                    'id': user.id,
                    'username': user.username,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'email': user.email,
                    'is_staff': user.is_staff,
                    'is_superuser': user.is_superuser,
                    'role': 'Super Admin' if user.is_superuser else 'IT Support',
                }
            response.data['message'] = "Login successful"
        return response


class RefreshView(TokenRefreshView):
    pass


class UserPermission(permissions.BasePermission):
    """
    - Allows authenticated users (both Super Admin and IT Support) to LIST/RETRIEVE the user directory.
    - Allows users to update their own profile (or Super Admin to update any profile).
    - Restricts CREATE (POST) and DELETE (destroy / bulk_delete) strictly to Super Admin (is_superuser=True).
    """
    message = "Only Super Admin is authorized to create or delete user accounts."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        # Read-only actions (list, retrieve) are open to all authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True
        # Creation and bulk deletion require Super Admin
        if request.method == 'POST' or getattr(view, 'action', None) == 'bulk_delete':
            return bool(request.user.is_superuser)
        # Deleting a user requires Super Admin
        if request.method == 'DELETE':
            return bool(request.user.is_superuser)
        # For PUT / PATCH updates, let has_object_permission handle own vs other
        return True

    def has_object_permission(self, request, view, obj):
        # Read access allowed
        if request.method in permissions.SAFE_METHODS:
            return True
        # Delete only Super Admin
        if request.method == 'DELETE':
            return bool(request.user.is_superuser)
        # Super Admin can edit any user; IT Support can edit only their own profile
        return bool(request.user.is_superuser or request.user.id == obj.id)


class CanDeleteIfSuperUser(permissions.BasePermission):
    """
    Allows reading/creating/updating to staff (e.g. IT Support),
    but restricts DELETE (destroy) and bulk_delete actions strictly to Super Admin (is_superuser=True).
    """
    message = "Only Super Admin is authorized to delete records."

    def has_permission(self, request, view):
        if request.method == 'DELETE' or getattr(view, 'action', None) == 'bulk_delete':
            return bool(request.user and request.user.is_authenticated and request.user.is_superuser)
        return True


# Create your views here.
class UserViewSet(ModelViewSet):
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [UserPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = UserFilter
    search_fields = ['username', 'first_name', 'last_name', 'email']
    ordering_fields = ['date_joined', 'username', 'last_login', 'first_name']

    def perform_destroy(self, instance):
        if instance.is_superuser:
            remaining = User.objects.filter(is_superuser=True, is_active=True).exclude(pk=instance.pk).count()
            if remaining == 0:
                from rest_framework.exceptions import ValidationError
                raise ValidationError({"detail": "Cannot delete the last active Super Admin account."})
        instance.delete()

    @action(detail=False, methods=['post'])
    def bulk_delete(self, request):
        ids = request.data.get('ids', [])
        if ids:
            users_to_delete = User.objects.filter(id__in=ids)
            if users_to_delete.filter(is_superuser=True).exists():
                remaining = User.objects.filter(is_superuser=True, is_active=True).exclude(id__in=ids).count()
                if remaining == 0:
                    return Response(
                        {"error": "Cannot delete all active Super Admin accounts."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            count = users_to_delete.count()
            users_to_delete.delete()
            return Response({"message": f"Successfully deleted {count} users"}, status=status.HTTP_200_OK)
        return Response({"error": "No IDs provided"}, status=status.HTTP_400_BAD_REQUEST)

class DepartmentViewSet(ModelViewSet):
    queryset = Department.objects.filter(is_deleted=False).order_by('name')
    serializer_class = DepartmentSerializer
    permission_classes = [CanDeleteIfSuperUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = DepartmentFilter
    search_fields = ['name', 'status']
    ordering_fields = ['name', 'created_at', 'status']

class BrandViewSet(ModelViewSet):
    queryset = Brand.objects.filter(is_deleted=False).order_by('name')
    serializer_class = BrandSerializer
    permission_classes = [CanDeleteIfSuperUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = BrandFilter
    search_fields = ['name', 'status']
    ordering_fields = ['name', 'created_at', 'status']

class ComputerViewSet(ModelViewSet):
    queryset = Computer.objects.filter(is_deleted=False).select_related('department', 'model', 'model__brand')
    serializer_class = ComputerSerializer
    permission_classes = [CanDeleteIfSuperUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ComputerFilter
    search_fields = [
        'host_name',
        'ip_address',
        'serial_no',
        'ims_code',
        'processor',
        'ram',
        'storage_capacity',
        'storage_type',
        'operating_system',
        'department__name',
        'model__name',
        'model__brand__name',
        'model__computer_type',
        'vendor_name',
        'vendor_email',
        'domain',
        'antivirus',
        'fiscal_year',
        'status',
        'hotfix_id',
    ]
    ordering_fields = ['host_name', 'created_at', 'status', 'purchase_date', 'ip_address']

class ComputerModelViewSet(ModelViewSet):
    queryset = ComputerModel.objects.filter(is_deleted=False).select_related('brand').order_by('name')
    serializer_class = ComputerModelSerializer
    permission_classes = [CanDeleteIfSuperUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ComputerModelFilter
    search_fields = ['name', 'brand__name', 'computer_type', 'status']
    ordering_fields = ['name', 'brand__name', 'created_at', 'computer_type', 'status']

class PrinterViewSet(ModelViewSet):
    queryset = Printer.objects.filter(is_deleted=False).select_related('department', 'model', 'model__brand')
    serializer_class = PrinterSerializer
    permission_classes = [CanDeleteIfSuperUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = PrinterFilter
    search_fields = [
        'printer_name',
        'ip_address',
        'serial_no',
        'ims_code',
        'host_name',
        'printer_function',
        'department__name',
        'model__name',
        'model__brand__name',
        'vendor_name',
        'vendor_email',
        'domain',
        'fiscal_year',
        'status',
    ]
    ordering_fields = ['printer_name', 'created_at', 'status', 'purchase_date', 'ip_address']

class PrinterModelViewSet(ModelViewSet):
    queryset = PrinterModel.objects.filter(is_deleted=False).select_related('brand').order_by('name')
    serializer_class = PrinterModelSerializer
    permission_classes = [CanDeleteIfSuperUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = PrinterModelFilter
    search_fields = ['name', 'brand__name', 'printer_type', 'status']
    ordering_fields = ['name', 'brand__name', 'created_at', 'printer_type', 'status']

class ComputerLogViewSet(ModelViewSet):
    queryset = ComputerLog.objects.filter(is_deleted=False).select_related('computer', 'department', 'computer__model').order_by('-log_date', '-created_at')
    serializer_class = ComputerLogSerializer
    permission_classes = [CanDeleteIfSuperUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ComputerLogFilter
    search_fields = [
        'description',
        'authorized_by',
        'performer_role',
        'assigned_user',
        'action_source',
        'computer_ims',
        'computer__ims_code',
        'computer__host_name',
        'action_taken',
        'department__name',
        'log_type',
        'resolution_status',
    ]
    ordering_fields = ['log_date', 'created_at', 'log_type', 'resolution_status']

    @action(detail=False, methods=['get'])
    def stats(self, request):
        logs = self.get_queryset()
        total_logs = logs.count()
        critical_errors = logs.filter(log_type='ERROR').count()
        unresolved_issues = logs.filter(resolution_status='UNRESOLVED').count()
        maintenance_count = logs.filter(log_type='MAINTENANCE').count()
        update_count = logs.filter(log_type='UPDATE').count()
        assignment_count = logs.filter(log_type='ASSIGNMENT').count()

        # Dynamic uptime calculation
        uptime_pct = 99.8
        if total_logs > 0:
            uptime_pct = round(max(95.0, 100.0 - (critical_errors * 0.4)), 1)

        return Response({
            'total_logs': total_logs,
            'critical_errors': critical_errors,
            'unresolved_issues': unresolved_issues,
            'maintenance_count': maintenance_count,
            'update_count': update_count,
            'assignment_count': assignment_count,
            'uptime_goal': f"{uptime_pct}%",
            'uptime_percentage': uptime_pct,
        })

    @action(detail=False, methods=['post'])
    def bulk_delete(self, request):
        ids = request.data.get('ids', [])
        if ids:
            ComputerLog.objects.filter(id__in=ids).update(is_deleted=True, deleted_at=timezone.now())
            return Response({"message": f"Successfully deleted {len(ids)} logs"}, status=status.HTTP_200_OK)
        return Response({"error": "No IDs provided"}, status=status.HTTP_400_BAD_REQUEST)


class PublicDeviceLookupView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request):
        query = request.query_params.get('q', '').strip()
        limit_param = request.query_params.get('limit', '').strip()
        
        computers = Computer.objects.all().select_related(
            'model', 'department', 'model__brand'
        ).annotate(
            empty_host=Case(
                When(Q(host_name__isnull=True) | Q(host_name=''), then=Value(1)),
                default=Value(0),
                output_field=IntegerField()
            )
        ).order_by('empty_host', 'host_name', 'ims_code')

        if query:
            computers = computers.filter(
                Q(host_name__icontains=query) |
                Q(ims_code__icontains=query) |
                Q(serial_no__icontains=query) |
                Q(ip_address__icontains=query) |
                Q(model__name__icontains=query) |
                Q(model__brand__name__icontains=query) |
                Q(department__name__icontains=query)
            )
        
        if limit_param and limit_param.isdigit():
            computers = computers[:int(limit_param)]
        
        results = []
        for comp in computers:
            results.append({
                'id': comp.id,
                'device_type': 'Computer',
                'host_name': comp.host_name or '',
                'ims_code': comp.ims_code or '',
                'model_name': comp.model.name if comp.model else '',
                'brand_name': comp.model.brand.name if (comp.model and comp.model.brand) else '',
                'computer_type': comp.model.computer_type if comp.model else '',
                'department_id': comp.department.id if comp.department else None,
                'department_name': comp.department.name if comp.department else 'IT',
                'ip_address': comp.ip_address or '',
                'operating_system': comp.operating_system or '',
                'processor': comp.processor or '',
                'ram': comp.ram or '',
                'storage_capacity': comp.storage_capacity or '',
                'serial_no': comp.serial_no or '',
            })
        
        return Response(results, status=status.HTTP_200_OK)


class PublicIssueReportView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        data = request.data
        host_name = data.get('host_name', '').strip()
        computer_id = data.get('computer_id')
        ims_code = data.get('ims_code', '').strip()
        reporter_name = data.get('reporter_name', '').strip()
        reporter_phone = data.get('reporter_phone', '').strip()
        reporter_email = data.get('reporter_email', '').strip()
        department_id = data.get('department_id')
        issue_category = data.get('issue_category', 'ERROR').strip().upper()
        urgency = data.get('urgency', 'NORMAL').strip().upper()
        issue_description = data.get('description', '').strip()

        if not issue_description:
            return Response({'error': 'Issue description is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not reporter_name:
            return Response({'error': 'Reporter name is required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Match computer if computer_id or host_name provided
        computer = None
        if computer_id:
            computer = Computer.objects.filter(id=computer_id).first()
        elif host_name:
            computer = Computer.objects.filter(host_name__iexact=host_name).first()

        department = None
        if department_id:
            department = Department.objects.filter(id=department_id).first()
        elif computer and computer.department:
            department = computer.department

        device_ims = ims_code or (computer.ims_code if computer else '') or host_name or 'Unspecified Device'
        
        category_map = {
            'HARDWARE': 'MAINTENANCE',
            'SOFTWARE': 'ERROR',
            'NETWORK': 'ERROR',
            'SECURITY': 'SECURITY',
            'UPDATE': 'UPDATE',
            'MAINTENANCE': 'MAINTENANCE',
            'ERROR': 'ERROR',
            'OTHER': 'OTHER',
        }
        log_type = category_map.get(issue_category, 'ERROR')

        desc = issue_description
        contact_info = []
        if reporter_phone:
            contact_info.append(f"Phone: {reporter_phone}")
        if reporter_email:
            contact_info.append(f"Email: {reporter_email}")
        if contact_info:
            desc = f"{issue_description}\n(Contact: {', '.join(contact_info)})"

        log = ComputerLog.objects.create(
            computer=computer,
            computer_ims=device_ims,
            log_type=log_type,
            description=desc,
            authorized_by=f"{reporter_name} (User Report)",
            performer_role="Help Desk User Submission",
            assigned_user=reporter_name,
            department=department,
            ip_address=(computer.ip_address if computer else None),
            action_source="Help Portal",
            resolution_status="UNRESOLVED",
            action_taken="",
        )

        return Response({
            'message': 'Issue reported successfully. IT administrators have been notified.',
            'log_id': log.log_id,
            'id': log.id,
            'log_date': log.log_date,
            'resolution_status': log.resolution_status,
        }, status=status.HTTP_201_CREATED)


class DisposalRecordViewSet(ModelViewSet):
    """CRUD for hardware disposal records."""
    serializer_class = DisposalRecordSerializer
    permission_classes = [CanDeleteIfSuperUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['disposal_id', 'asset_name', 'asset_ims_code', 'asset_serial_no', 'approved_by', 'notes']
    filterset_fields = ['asset_type', 'disposal_method', 'disposal_reason', 'data_sanitized']
    ordering_fields = ['disposal_date', 'created_at', 'salvage_value']
    ordering = ['-disposal_date']

    def get_queryset(self):
        return DisposalRecord.objects.filter(is_deleted=False).select_related(
            'computer', 'printer', 'department',
            'computer__model', 'computer__model__brand', 'computer__department',
            'printer__model', 'printer__model__brand', 'printer__department',
        )