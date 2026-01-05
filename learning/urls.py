from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CourseViewSet, EnrollmentViewSet

router = DefaultRouter()
router.register(r'courses', CourseViewSet)
router.register(r'my-learning', EnrollmentViewSet, basename='my-learning')

urlpatterns = [
    path('', include(router.urls)),
]
