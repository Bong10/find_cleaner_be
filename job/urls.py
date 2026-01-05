from rest_framework.routers import DefaultRouter
from .views import (
    JobViewSet, JobApplicationViewSet, JobBookingViewSet,
    JobServiceViewSet, CleanerServiceViewSet, ShortlistViewset
)

router = DefaultRouter()
router.register(r'jobs', JobViewSet, basename='job')
router.register(r'job-applications', JobApplicationViewSet, basename='job-application')
router.register(r'job-bookings', JobBookingViewSet, basename='job-booking')
router.register(r'job-services', JobServiceViewSet, basename='job-service')        # uses Service from services app
router.register(r'cleaner-services', CleanerServiceViewSet, basename='cleaner-service')
router.register(r'shortlist', ShortlistViewset, basename='shortlist')

urlpatterns = router.urls
