from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    UserViewSet,
    ComputerViewSet,
    ComputerModelViewSet,
    PrinterViewSet,
    PrinterModelViewSet,
    BrandViewSet,
    DepartmentViewSet,
    ComputerLogViewSet,
    LoginAPIView,
    PublicDeviceLookupView,
    PublicIssueReportView,
    PublicAutoDetectDeviceView,
)
from .import_views import (
    BulkImportComputerView,
    BulkImportPrinterView,
)


router = DefaultRouter()


router.register(r'users', UserViewSet, basename='user')
router.register(r'computers', ComputerViewSet, basename='computer')
router.register(r'computer-models', ComputerModelViewSet, basename='computer-model')
router.register(r'printers', PrinterViewSet, basename='printer')
router.register(r'printer-models', PrinterModelViewSet, basename='printer-model')
router.register(r'brands', BrandViewSet, basename='brand')
router.register(r'departments', DepartmentViewSet, basename='department')
router.register(r'logs', ComputerLogViewSet, basename='log')

urlpatterns = [
    path('computers/import-excel/', BulkImportComputerView.as_view(), name='computer-import-excel'),
    path('printers/import-excel/', BulkImportPrinterView.as_view(), name='printer-import-excel'),
    path('', include(router.urls)),
    path('login/', LoginAPIView.as_view()),
    path('token/refresh/', TokenRefreshView.as_view()),
    path('public/devices/', PublicDeviceLookupView.as_view(), name='public-devices'),
    path('public/auto-detect-device/', PublicAutoDetectDeviceView.as_view(), name='public-auto-detect'),
    path('public/report-issue/', PublicIssueReportView.as_view(), name='public-report-issue'),
]