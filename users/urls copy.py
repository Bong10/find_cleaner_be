from django.urls import path
from .views import (
    CleanerRegistrationView,
    EmployerRegistrationView,
    AdminRegistrationView,
    RoleManagementView,
    ActivateUserView,
    # get_csrf_token,
)

urlpatterns = [
    # path('csrf/', get_csrf_token, name='get_csrf_token'),
    path('register/cleaner/', CleanerRegistrationView.as_view(), name='register_cleaner'),
    path('register/employer/', EmployerRegistrationView.as_view(), name='register_employer'),
    path('register/admin/', AdminRegistrationView.as_view(), name='register_admin'),
    path('activate/<str:uidb64>/<str:token>/', ActivateUserView.as_view(), name='activate-user'),  # ← updated
    path('roles/', RoleManagementView.as_view(), name='role_management'),
]
