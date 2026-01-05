from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ChatbotViewSet

router = DefaultRouter()
router.register(r'bot', ChatbotViewSet, basename='bot')

urlpatterns = [
    path('', include(router.urls)),
]
