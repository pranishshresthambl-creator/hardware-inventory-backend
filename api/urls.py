from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    ComputerViewSet,
    PrinterViewSet,
    BrandViewSet,
    DepartmentViewSet,
    LoginAPIView
)


router = DefaultRouter()


router.register(r'computers', ComputerViewSet, basename='computer')
router.register(r'printers', PrinterViewSet, basename='printer')
router.register(r'brands', BrandViewSet, basename='brand')
router.register(r'departments', DepartmentViewSet, basename='department')

urlpatterns = [
    path('', include(router.urls)),
    path('login/', LoginAPIView.as_view()),
    path('token/refresh/', TokenRefreshView.as_view()),
]