from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import ServiceViewSet, CategoryViewSet, ServiceZoneViewSet, EligibilityApplicationViewSet

router = DefaultRouter()
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"zones", ServiceZoneViewSet, basename="servicezone")
router.register(r"eligibility", EligibilityApplicationViewSet, basename="eligibility")
router.register(r"", ServiceViewSet, basename="service")

urlpatterns = router.urls
