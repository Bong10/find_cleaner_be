from django.contrib import admin
from .models import (
    Job, JobApplication, JobBooking, JobService, CleanerService, Shortlist,
    CleanerReview, JobActionLog, Payment
)

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ("job_id", "title", "employer", "status", "date", "time", "hourly_rate", "hours_required", "is_archived", "created_at")
    list_filter = ("status", "is_archived", "date", "employer")
    search_fields = ("title", "description", "location")

@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ("application_id", "job", "cleaner", "status", "date_applied", "accepted_by", "accepted_at", "rejected_by", "rejected_at")
    list_filter = ("status", "date_applied")
    search_fields = ("job__title", "cleaner__user__name")

@admin.register(JobBooking)
class JobBookingAdmin(admin.ModelAdmin):
    list_display = ("booking_id", "job", "cleaner", "status")
    list_filter = ("status",)

@admin.register(JobService)
class JobServiceAdmin(admin.ModelAdmin):
    list_display = ("job_service_id", "job", "service")

@admin.register(CleanerService)
class CleanerServiceAdmin(admin.ModelAdmin):
    list_display = ("cleaner_service_id", "cleaner", "service")

@admin.register(Shortlist)
class ShortlistAdmin(admin.ModelAdmin):
    list_display = ("id", "job", "cleaner", "created_at")
    list_filter = ("created_at",)

@admin.register(CleanerReview)
class CleanerReviewAdmin(admin.ModelAdmin):
    list_display = ("id", "cleaner", "rating", "created_at")
    list_filter = ("rating",)

@admin.register(JobActionLog)
class JobActionLogAdmin(admin.ModelAdmin):
    list_display = ("id", "job", "action", "actor_employer", "actor_cleaner", "created_at")
    list_filter = ("action", "created_at")
    search_fields = ("job__title", "message")

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
