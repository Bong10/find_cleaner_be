"""
Separate URL configuration for roles endpoints.
"""
from django.urls import path
from users.views import RoleManagementView, RoleDetailView

urlpatterns = [
    path('', RoleManagementView.as_view(), name='roles-list'),
    path('<int:pk>/', RoleDetailView.as_view(), name='role-detail'),
]
