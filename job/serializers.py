from rest_framework import serializers
from django.utils import timezone

from .models import (
    Job, JobApplication, JobBooking, JobService, CleanerService, Shortlist,
    JobActionLog,  # NEW
)
from services.models import Service
from users.models import Cleaner

# ---------------------------
# Services (references new app)
# ---------------------------

class ServiceMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ["id", "name", "min_hourly_rate", "min_hours_required"]


class JobServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobService
        fields = ["job_service_id", "job", "service"]


class CleanerServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CleanerService
        fields = ["cleaner_service_id", "cleaner", "service"]


# ---------------------------
# Job
# ---------------------------

class JobCreateUpdateSerializer(serializers.ModelSerializer):
    services = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Service.objects.filter(active=True)
    )

    class Meta:
        model = Job
        fields = [
            "job_id",
            "title",
            "description",
            "location",
            "date",
            "time",
            "status",
            "special_requirements",
            "hourly_rate",
            "hours_required",
            "services",
        ]
        read_only_fields = ["job_id", "status"]

    def validate(self, attrs):
        if "date" in attrs and attrs["date"] < timezone.localdate():
            raise serializers.ValidationError({"date": "Date cannot be in the past."})

        hours = attrs.get("hours_required")
        if hours is not None and not (1 <= int(hours) <= 16):
            raise serializers.ValidationError({"hours_required": "Must be between 1 and 16 hours."})

        rate = attrs.get("hourly_rate")
        if rate is not None and rate < 0:
            raise serializers.ValidationError({"hourly_rate": "Must be ≥ 0."})

        services = attrs.get("services") or []
        if services:
            max_min_rate = max(s.min_hourly_rate for s in services)
            max_min_hours = max(s.min_hours_required for s in services)
            if rate is not None and rate < max_min_rate:
                raise serializers.ValidationError(
                    {"hourly_rate": f"Must be ≥ service minimum {max_min_rate}."}
                )
            if hours is not None and hours < max_min_hours:
                raise serializers.ValidationError(
                    {"hours_required": f"Must be ≥ service minimum {max_min_hours}."}
                )
        return attrs

    def create(self, validated_data):
        services = validated_data.pop("services", [])
        job = super().create(validated_data)
        if services:
            job.services.set(services)
        return job

    def update(self, instance, validated_data):
        services = validated_data.pop("services", None)
        job = super().update(instance, validated_data)
        if services is not None:
            job.services.set(services)
        return job


class JobListSerializer(serializers.ModelSerializer):
    employer_name = serializers.CharField(source="employer.user.name", read_only=True)
    estimated_total = serializers.SerializerMethodField()
    service_names = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = [
            "job_id",
            "title",
            "location",
            "status",
            "date",
            "time",
            "hourly_rate",
            "hours_required",
            "estimated_total",
            "service_names",
            "created_at",
            "employer_name",
        ]

    def get_estimated_total(self, obj):
        return obj.estimated_total

    def get_service_names(self, obj):
        return [s.name for s in obj.services.all()]


class JobDetailSerializer(serializers.ModelSerializer):
    employer_name = serializers.CharField(source="employer.user.name", read_only=True)
    services = ServiceMiniSerializer(many=True, read_only=True)
    estimated_total = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = [
            "job_id",
            "title",
            "description",
            "location",
            "date",
            "time",
            "status",
            "special_requirements",
            "hourly_rate",
            "hours_required",
            "estimated_total",
            "services",
            "created_at",
            "employer_name",
            "is_archived",
        ]

    def get_estimated_total(self, obj):
        return obj.estimated_total


# ---------------------------
# Employer Job Metrics
# ---------------------------

class JobMetricsSerializer(serializers.ModelSerializer):
    applicants_total = serializers.IntegerField(read_only=True)
    applicants_pending = serializers.IntegerField(read_only=True)
    applicants_accepted = serializers.IntegerField(read_only=True)
    has_booking = serializers.BooleanField(read_only=True)
    latest_booking_status = serializers.CharField(read_only=True, allow_null=True)
    estimated_total = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = [
            "job_id",
            "title",
            "status",
            "date",
            "time",
            "hourly_rate",
            "hours_required",
            "estimated_total",
            "applicants_total",
            "applicants_pending",
            "applicants_accepted",
            "has_booking",
            "latest_booking_status",
            "created_at",
        ]

    def get_estimated_total(self, obj):
        return obj.estimated_total


# ---------------------------
# Cleaner discovery
# ---------------------------

class CleanerDiscoverySerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="user.name", read_only=True)
    address = serializers.CharField(source="user.address", allow_null=True, read_only=True)
    rating_avg = serializers.FloatField(read_only=True)
    services = serializers.SerializerMethodField()
    is_available = serializers.SerializerMethodField()

    class Meta:
        model = Cleaner
        fields = ["id", "name", "address", "rating_avg", "services", "is_available"]

    def get_services(self, obj):
        services = getattr(obj, "_services_cache", None)
        if services is None:
            services = Service.objects.filter(cleanerservice__cleaner=obj, active=True)
        return ServiceMiniSerializer(services, many=True).data

    def get_is_available(self, obj):
        return bool(getattr(obj, "_is_available", True))


# ---------------------------
# Applications (with audit fields)
# ---------------------------

class JobApplicationCreateSerializer(serializers.ModelSerializer):
    """
    Cleaner applies to a job. Cleaner injected from request.user.
    """
    class Meta:
        model = JobApplication
        fields = ["application_id", "job", "cleaner", "cover_letter", "status", "date_applied"]
        read_only_fields = ["application_id", "cleaner", "status", "date_applied"]

    def validate(self, attrs):
        request = self.context.get("request")
        if not request or not hasattr(request.user, "cleaner"):
            raise serializers.ValidationError({"detail": "Only cleaners can apply to a job."})

        cleaner = request.user.cleaner
        job = attrs.get("job")
        if job is None:
            raise serializers.ValidationError({"job": "This field is required."})

        if JobApplication.objects.filter(job=job, cleaner=cleaner).exists():
            raise serializers.ValidationError({"non_field_errors": ["You have already applied to this job."]})

        attrs["cleaner"] = cleaner
        attrs["status"] = "p"
        return attrs

    def create(self, validated_data):
        return super().create(validated_data)


class JobApplicationListSerializer(serializers.ModelSerializer):
    job_title = serializers.CharField(source="job.title", read_only=True)
    cleaner_name = serializers.CharField(source="cleaner.user.name", read_only=True)

    class Meta:
        model = JobApplication
        fields = [
            "application_id",
            "job",
            "job_title",
            "cleaner",
            "cleaner_name",
            "cover_letter",
            "status",
            "date_applied",
            "accepted_at",        # NEW
            "rejected_at",        # NEW
            "rejection_reason",   # NEW
        ]


# ---------------------------
# Shortlist  (uses id)
# ---------------------------

class ShortlistCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shortlist
        fields = ["id", "job", "cleaner"]
        read_only_fields = ["id"]


class ShortlistListSerializer(serializers.ModelSerializer):
    job_title = serializers.CharField(source="job.title", read_only=True)
    cleaner_name = serializers.CharField(source="cleaner.user.name", read_only=True)

    class Meta:
        model = Shortlist
        fields = [
            "id",
            "job",
            "job_title",
            "cleaner",
            "cleaner_name",
            "created_at",
        ]


# ---------------------------
# Booking
# ---------------------------

class JobBookingSerializer(serializers.ModelSerializer):
    job_title = serializers.CharField(source="job.title", read_only=True)
    cleaner_name = serializers.CharField(source="cleaner.user.name", read_only=True)
    # optional niceties:
    employer_name = serializers.CharField(source="job.employer.user.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    booking_amount = serializers.SerializerMethodField()

    class Meta:
        model = JobBooking
        fields = [
            "booking_id",
            "job",
            "job_title",
            "employer_name",          # optional, handy in UIs
            "cleaner",
            "cleaner_name",
            "payment",
            "payment_reference",      # NEW
            "paid_at",                # NEW
            "cleaner_confirmed",      # NEW
            "status",
            "status_display",         # optional, human label for status
            "booking_amount",         # NEW - calculated from job
        ]
        read_only_fields = ["booking_id", "status_display", "paid_at", "booking_amount"]

    def get_booking_amount(self, obj):
        """Calculate booking amount from job's hourly_rate * hours_required"""
        try:
            return float(obj.job.hourly_rate) * int(obj.job.hours_required)
        except (AttributeError, TypeError, ValueError):
            return 0.0


# ---------------------------
# Audit Log serializer  # NEW
# ---------------------------

class JobActionLogSerializer(serializers.ModelSerializer):  # NEW
    actor = serializers.SerializerMethodField()  # NEW

    class Meta:
        model = JobActionLog
        fields = ["id", "action", "message", "created_at", "actor"]  # NEW

    def get_actor(self, obj):  # NEW
        if obj.actor_employer:
            return {"type": "employer", "id": obj.actor_employer_id, "name": getattr(obj.actor_employer.user, "name", None)}
        if obj.actor_cleaner:
            return {"type": "cleaner", "id": obj.actor_cleaner_id, "name": getattr(obj.actor_cleaner.user, "name", None)}
        return None


