from django.contrib.auth import authenticate

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
    Department
)

from .serializers import (
    ComputerSerializer,
    ComputerModelSerializer,
    PrinterSerializer,
    PrinterModelSerializer,
    BrandSerializer,
    DepartmentSerializer
)


class LoginAPIView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        response.data['message'] = "Login successful"
        return response
    pass

class RefreshView(TokenRefreshView):
    pass

# Create your views here.
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