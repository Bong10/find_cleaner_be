# Importation des bibliothèques nécessaires
from django.contrib import admin
from django.urls import path,include
from rest_framework.routers import DefaultRouter
from job.views import (
    JobViewSet,
    JobApplicationViewSet,
    JobBookingViewSet,
    JobServiceViewSet,
    CleanerServiceViewSet,
    ShortlistViewset,
    CleanerDiscoveryViewSet
)
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from chat.views import ChatViewSet,MessageViewSet,FlaggedChatViewSet
from users.custom_djoser_views import CustomUserViewSet


router = DefaultRouter()
router.register(r'jobs', JobViewSet, basename='job')
router.register(r'chats', ChatViewSet)
router.register(r'messages', MessageViewSet) 
router.register(r'flagged-chats', FlaggedChatViewSet, basename='flaggedchat')
router.register(r'job-applications', JobApplicationViewSet)
router.register(r'job-bookings', JobBookingViewSet)
router.register(r'job-services', JobServiceViewSet)
router.register(r'cleaner-services', CleanerServiceViewSet)
router.register(r'shortlist', ShortlistViewset)
router.register(r'cleaners-search', CleanerDiscoveryViewSet, basename='cleaner-search')  # NEW

# Custom Djoser routes with rate limiting
auth_router = DefaultRouter()
auth_router.register(r'users', CustomUserViewSet, basename='user')

urlpatterns = [
    path('admin/', admin.site.urls),
    # Custom Djoser endpoints with rate limiting (must come before djoser.urls)
    path('auth/', include(auth_router.urls)),
    # path('auth/', include('djoser.urls')),  # Commented out - using custom viewset instead
    # ✅ Cookie-based JWT endpoints (our custom ones) — DO NOT include djoser.urls.jwt
    path('auth/jwt/', include('users.jwt_urls')),
    
    # ✅ Admin dashboard and statistics endpoints
    path('api/admin/', include('users.admin_urls')),

    # Learning / Course Management System
    path('api/learning/', include('learning.urls')),

    # path('auth/', include('djoser.urls.jwt')),  # Inclure les URLs JWT pour obtenir le token
    
  

    path("api/", include(router.urls)), 
    path("api/services/", include("services.urls")),
    path('api/chatbot/', include('chatbot.urls')),
    path('api/', include('notifications.urls')),
    path('api/users/', include('users.urls')),
    
    # Direct role endpoint for frontend
    path('api/roles/', include('users.roles_urls')),
    
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    # path('api/apply-for-job/<int:job_id>/<int:cleaner_id>/', ApplyForJobView.as_view(), name='apply-for-job'),
    # path('api/employers/user/<int:user_id>/', EmployerDetailView.as_view(), name='employer-detail'),
    # path('api/cleaner/user/<int:user_id>/', CleanerDetailView.as_view(), name='cleaner-detail'),
    # path('api/jobs/my-jobs/<int:user_id>/', EmployerJobsView.as_view(), name='my-jobs'),
    # path('confirmation-account/<uid>/<token>', activate_user, name='activation'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
