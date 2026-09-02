import socket
from django.contrib.auth import authenticate
from django.utils import timezone
from django.db.models import Q

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
                }
            response.data['message'] = "Login successful"
        return response


class RefreshView(TokenRefreshView):
    pass

# Create your views here.
class UserViewSet(ModelViewSet):
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer

    @action(detail=False, methods=['post'])
    def bulk_delete(self, request):
        ids = request.data.get('ids', [])
        if ids:
            User.objects.filter(id__in=ids).delete()
            return Response({"message": f"Successfully deleted {len(ids)} users"}, status=status.HTTP_200_OK)
        return Response({"error": "No IDs provided"}, status=status.HTTP_400_BAD_REQUEST)

class DepartmentViewSet(ModelViewSet):
    queryset = Department.objects.filter(is_deleted=False)
    serializer_class = DepartmentSerializer

class BrandViewSet(ModelViewSet):
    queryset = Brand.objects.filter(is_deleted=False)
    serializer_class = BrandSerializer

class ComputerViewSet(ModelViewSet):
    queryset = Computer.objects.filter(is_deleted=False)
    serializer_class = ComputerSerializer

class ComputerModelViewSet(ModelViewSet):
    queryset = ComputerModel.objects.filter(is_deleted=False)
    serializer_class = ComputerModelSerializer

class PrinterViewSet(ModelViewSet):
    queryset = Printer.objects.filter(is_deleted=False)
    serializer_class = PrinterSerializer

class PrinterModelViewSet(ModelViewSet):
    queryset = PrinterModel.objects.filter(is_deleted=False)
    serializer_class = PrinterModelSerializer

class ComputerLogViewSet(ModelViewSet):
    queryset = ComputerLog.objects.filter(is_deleted=False).order_by('-log_date', '-created_at')
    serializer_class = ComputerLogSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['log_type', 'department', 'computer', 'resolution_status']
    search_fields = [
        'description',
        'authorized_by',
        'computer_ims',
        'computer__ims_code',
        'computer__host_name',
        'action_taken',
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


def is_docker_or_virtual_ip(ip):
    """
    Check whether an IP is a Docker bridge gateway (e.g. 172.29.0.1, 172.17.0.1),
    virtual machine NAT, APIPA, or loopback address.
    """
    if not ip:
        return True
    ip = str(ip).strip()
    if ip in ('127.0.0.1', '::1', 'localhost') or ip.startswith('10.0.2.') or ip.startswith('169.254.'):
        return True

    parts = ip.split('.')
    if len(parts) == 4:
        # Docker standard bridge network range 172.16.0.0/12
        if parts[0] == '172':
            try:
                second = int(parts[1])
                if 16 <= second <= 31:
                    return True
            except ValueError:
                pass
    return False


def get_client_ip(request):
    """
    Extract client IP checking reverse proxy / forwarding headers first,
    falling back to REMOTE_ADDR.
    """
    for header in [
        'HTTP_X_FORWARDED_FOR',
        'HTTP_X_REAL_IP',
        'HTTP_CF_CONNECTING_IP',
        'HTTP_CLIENT_IP',
        'HTTP_X_CLIENT_IP',
        'HTTP_X_FORWARDED',
        'HTTP_FORWARDED_FOR',
        'HTTP_FORWARDED',
    ]:
        val = request.META.get(header)
        if val:
            ip = val.split(',')[0].strip()
            if ip and ip not in ('unknown', '127.0.0.1', '::1'):
                return ip
    return request.META.get('REMOTE_ADDR') or '127.0.0.1'


class PublicAutoDetectDeviceView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request):
        override_hostname = request.query_params.get('hostname', '').strip()
        override_ip = request.query_params.get('ip', '').strip()
        client_ip = override_ip or get_client_ip(request)
        is_virtual = is_docker_or_virtual_ip(client_ip)

        # ── 1. Resolve Hostname (via parameter, header, or Reverse DNS lookup from IP) ──
        dns_hostname = None
        if client_ip and not is_virtual:
            try:
                dns_hostname, _, _ = socket.gethostbyaddr(client_ip)
            except Exception:
                dns_hostname = None

        target_hostname = override_hostname or dns_hostname

        computer = None
        matched_via = None

        # ── 2. Primary Match: Workstation Hostname ──
        if target_hostname:
            short_host = target_hostname.split('.')[0].strip()
            computer = Computer.objects.filter(
                Q(host_name__iexact=target_hostname) | 
                Q(host_name__iexact=short_host) | 
                Q(host_name__icontains=short_host),
                is_deleted=False
            ).select_related('model', 'department', 'model__brand').first()
            if computer:
                matched_via = 'hostname'

        # ── 3. Secondary Match: Workstation IP Address (Fallback / Dual Detection) ──
        if not computer and client_ip and not is_virtual:
            computer = Computer.objects.filter(
                ip_address=client_ip,
                is_deleted=False
            ).select_related('model', 'department', 'model__brand').first()
            if computer:
                matched_via = 'ip'

        if computer:
            device_data = {
                'id': computer.id,
                'device_type': 'Computer',
                'host_name': computer.host_name or '',
                'ims_code': computer.ims_code or '',
                'model_name': computer.model.name if computer.model else '',
                'brand_name': computer.model.brand.name if (computer.model and computer.model.brand) else '',
                'computer_type': computer.model.computer_type if computer.model else '',
                'department_id': computer.department.id if computer.department else None,
                'department_name': computer.department.name if computer.department else 'IT',
                'ip_address': computer.ip_address or client_ip,
                'operating_system': computer.operating_system or '',
                'processor': computer.processor or '',
                'ram': computer.ram or '',
                'storage_capacity': computer.storage_capacity or '',
                'serial_no': computer.serial_no or '',
            }
            
            detect_msg = (
                f"Device successfully auto-detected from Hostname '{computer.host_name or target_hostname}'."
                if matched_via == 'hostname' else
                f"Device successfully auto-detected from IP Address {client_ip}."
            )

            return Response({
                'matched': True,
                'matched_via': matched_via,
                'client_ip': client_ip,
                'detected_hostname': target_hostname or computer.host_name,
                'dns_hostname': dns_hostname,
                'is_virtual_ip': is_virtual,
                'device': device_data,
                'message': detect_msg
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'matched': False,
                'matched_via': None,
                'client_ip': client_ip,
                'detected_hostname': target_hostname,
                'dns_hostname': dns_hostname,
                'is_virtual_ip': is_virtual,
                'device': None,
                'message': (
                    f"Virtual / Docker gateway IP ({client_ip}) detected. Please provide your physical Ethernet IP or Hostname."
                    if is_virtual else
                    f"Detected connection (IP: {client_ip}{', Host: ' + target_hostname if target_hostname else ''}), but no matching workstation record was found in the inventory database."
                )
            }, status=status.HTTP_200_OK)


class PublicDeviceLookupView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request):
        query = request.query_params.get('q', '').strip()
        
        computers = Computer.objects.filter(is_deleted=False)
        if query:
            computers = computers.filter(
                Q(host_name__icontains=query) |
                Q(ims_code__icontains=query) |
                Q(serial_no__icontains=query) |
                Q(ip_address__icontains=query)
            )
        
        results = []
        for comp in computers.select_related('model', 'department', 'model__brand')[:60]:
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
            computer = Computer.objects.filter(id=computer_id, is_deleted=False).first()
        elif host_name:
            computer = Computer.objects.filter(host_name__iexact=host_name, is_deleted=False).first()

        department = None
        if department_id:
            department = Department.objects.filter(id=department_id, is_deleted=False).first()
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