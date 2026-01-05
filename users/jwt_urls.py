# users/jwt_urls.py
from django.urls import path
from .views_jwt import CookieTokenObtainPairView, CookieTokenRefreshView, CookieLogoutView
from .views_admin_jwt import AdminTokenObtainPairView

urlpatterns = [
    path('create/',  CookieTokenObtainPairView.as_view(),  name='jwt-create'),
    path('refresh/', CookieTokenRefreshView.as_view(),     name='jwt-refresh'),
    path('logout/',  CookieLogoutView.as_view(),           name='jwt-logout'),
    path('admin/create/', AdminTokenObtainPairView.as_view(), name='admin-jwt-create'),
]
