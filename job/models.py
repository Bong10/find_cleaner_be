from django.db import models
from django.shortcuts import get_object_or_404
from users.models import Employer, Cleaner  # CHANGED (kept minimal imports)

class Payment(models.Model):
    # stub for future payment flow
    name = models.CharField(max_length=100)

class Job(models.Model):
    """
    Represents a cleaning task posted by employers
    """
    STATUS_CHOICES = [
        ("o", "Open"),
        ("p", "Pending"),
        ("t", "Taken"),
        ("ip", "In progress"),
        ("c", "Completed"),
    ]

    job_id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=100, default="My Job title ")
    description = models.TextField(default="No Description")
    employer = models.ForeignKey(Employer, on_delete=models.CASCADE)
    location = models.CharField(max_length=50)
    date = models.DateField()
    time = models.CharField(max_length=10)
    status = models.CharField(max_length=2, choices=STATUS_CHOICES, default="o")  # CHANGED (default)
    special_requirements = models.CharField(max_length=255, blank=True)  # CHANGED (added max_length + blank)

    # Pricing model: hourly  # NEW
    hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, default=0)  # NEW
    hours_required = models.PositiveSmallIntegerField(default=1)                   # NEW

    # Soft delete / archive  # NEW
    is_archived = models.BooleanField(default=False)                               # NEW
    archived_at = models.DateTimeField(null=True, blank=True)                      # NEW

    created_at = models.DateTimeField(auto_now_add=True)

    # M2M to services.Service (external app) via through  # CHANGED
    services = models.ManyToManyField(
        "services.Service", related_name="jobs", through="JobService"
    )
    shorlist = models.ManyToManyField(
        Cleaner, related_name="shorted_jobs", through="Shortlist"
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Job {self.job_id} posted by {self.employer_id}"

    @property
    def estimated_total(self):  # NEW
        try:
            return float(self.hourly_rate) * int(self.hours_required)
        except Exception:
            return 0.0

    def assignCleaner(self, cleaner_id: int):
        cleaner = Cleaner.objects.get(pk=cleaner_id)
        if cleaner:
            book = JobBooking.objects.create(
                job=self,  # CHANGED (was Job=self)
                cleaner=cleaner,
                status="cf",
            )
            if book:
                self.status = "t"
                self.save()
                return True
        return False

    def updateStatus(self, new_status: str):
        self.status = new_status
        self.save()

    @property
    def markAsComplete(self):
        if self.status != "c":
            self.status = "c"
            self.save()
            return True
        return False


class Shortlist(models.Model):
    cleaner = models.ForeignKey(Cleaner, on_delete=models.CASCADE)
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)  # NEW

    class Meta:
        unique_together = ("job", "cleaner")  # NEW


class JobService(models.Model):
    """
    Tracks services associated with specific jobs.
    """
    job_service_id = models.AutoField(primary_key=True)
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    service = models.ForeignKey("services.Service", on_delete=models.CASCADE)  # CHANGED

    @staticmethod
    def addServiceToJob(job_id: int, service_id: int):
        job = get_object_or_404(Job, pk=job_id)
        from services.models import Service  # NEW (lazy import)
        service = get_object_or_404(Service, pk=service_id)
        if JobService.objects.create(job=job, service=service):
            return True
        return False

    @staticmethod
    def removeServiceFromJob(job_service_id: int):
        if JobService.objects.get(pk=job_service_id).delete():
            return True
        return False


class JobApplication(models.Model):
    """
    Tracks applications submitted by cleaners for jobs.
    """
    STATUS_CHOICES = [
        ("p", "Pending"),
        ("a", "Accepted"),
        ("r", "Rejected"),
    ]
    application_id = models.AutoField(primary_key=True)
    cleaner = models.ForeignKey(Cleaner, on_delete=models.CASCADE)
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default="p")
    date_applied = models.DateField(auto_now_add=True)
    cover_letter = models.TextField(default="No cover letter")

    # --- Auditing fields for accept/reject ---  # NEW
    accepted_by = models.ForeignKey(Employer, null=True, blank=True, on_delete=models.SET_NULL, related_name="accepted_applications")  # NEW
    accepted_at = models.DateTimeField(null=True, blank=True)  # NEW
    rejected_by = models.ForeignKey(Employer, null=True, blank=True, on_delete=models.SET_NULL, related_name="rejected_applications")  # NEW
    rejected_at = models.DateTimeField(null=True, blank=True)  # NEW
    rejection_reason = models.CharField(max_length=255, blank=True)  # NEW

    class Meta:
        unique_together = ("job", "cleaner")

    @staticmethod
    def applyForJob(job_id: int, cleaner_id: int):
        job = Job.objects.get(pk=job_id)
        cleaner = Cleaner.objects.get(pk=cleaner_id)
        if JobApplication.objects.filter(job=job, cleaner=cleaner).exists():
            return False
        else:
            JobApplication.objects.create(job=job, cleaner=cleaner, status="p")
            return True

    @staticmethod
    def updateStatus(application_id: int, new_status: str):
        application = JobApplication.objects.get(pk=application_id)
        application.status = new_status
        application.save()


class JobBooking(models.Model):
    """
    Tracks confirmed bookings for jobs.
    """
    CHOICES = [
        ("cf", "Confirmed"),
        ("cp", "Completed"),
        ("p", "Pending"),
        ("r", "Rejected"),
    ]
    booking_id = models.AutoField(primary_key=True)
    job = models.ForeignKey(Job, on_delete=models.CASCADE)            # CHANGED (lowercase)
    cleaner = models.ForeignKey(Cleaner, on_delete=models.CASCADE)
    payment = models.ForeignKey("Payment", on_delete=models.CASCADE, null=True, blank=True)
    status = models.CharField(max_length=2, choices=CHOICES, default="p")

    cleaner_confirmed = models.BooleanField(default=False)              # NEW
    paid_at = models.DateTimeField(null=True, blank=True)               # NEW
    payment_reference = models.CharField(max_length=100, blank=True)    # NEW

    class Meta:
        unique_together = ("job", "cleaner")
        indexes = [models.Index(fields=["cleaner", "status"])]

    @staticmethod
    def confirmBooking(booking_id: int):
        book = get_object_or_404(JobBooking, pk=booking_id)
        if book is not None:
            book.status = "cf"
            book.save()
            return True
        else:
            return False

    @staticmethod
    def updateBookingStatus(booking_id: int, status: str):
        book = get_object_or_404(JobBooking, pk=booking_id)
        if book is not None:
            book.status = status
            book.save()
            return True
        return False


class CleanerService(models.Model):
    """
    Tracks services offered by cleaners.
    """
    cleaner_service_id = models.AutoField(primary_key=True)
    cleaner = models.ForeignKey(Cleaner, on_delete=models.CASCADE)
    service = models.ForeignKey("services.Service", on_delete=models.CASCADE)  # CHANGED

    @staticmethod
    def addServiceToCleaner(service_id: int, cleaner_id: int):
        from services.models import Service  # NEW (lazy import)
        service = get_object_or_404(Service, pk=service_id)
        cleaner = get_object_or_404(Cleaner, pk=cleaner_id)
        if CleanerService.objects.create(service=service, cleaner=cleaner):
            return True
        return False

    def removeServiceFromCleaner(cleaner_service_id: int):
        if CleanerService.objects.get(pk=cleaner_service_id).delete():
            return True
        return False


# # ---------------------------
# # Ratings (simple, optional)  # NEW
# # ---------------------------
# class CleanerReview(models.Model):  # NEW
#     cleaner = models.ForeignKey(Cleaner, on_delete=models.CASCADE, related_name="reviews")  # NEW
#     rating = models.PositiveSmallIntegerField()  # 1..5                                # NEW
#     created_at = models.DateTimeField(auto_now_add=True)                               # NEW

#     class Meta:
#         indexes = [
#             models.Index(fields=["cleaner", "created_at"]),  # NEW
#         ]

#     def __str__(self):
#         return f"Review({self.cleaner_id}, {self.rating})"  # NEW


# ---------------------------
# Generic Job Audit Log  # NEW
# ---------------------------
class JobActionLog(models.Model):  # NEW
    ACTIONS = [  # NEW
        ("job_create", "Job Created"),
        ("job_update", "Job Updated"),
        ("job_close", "Job Closed"),
        ("job_reopen", "Job Reopened"),
        ("app_accept", "Application Accepted"),
        ("app_reject", "Application Rejected"),
        ("service_attach", "Service Attached"),
        ("service_detach", "Service Detached"),
        ("shortlist_add", "Shortlist Added"),
        ("shortlist_remove", "Shortlist Removed"),
        ("booking_create", "Booking Created"),
        ("booking_status", "Booking Status Updated"),
    ]
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="audit_logs")  # NEW
    action = models.CharField(max_length=32, choices=ACTIONS)  # NEW
    actor_employer = models.ForeignKey(Employer, null=True, blank=True, on_delete=models.SET_NULL, related_name="job_action_logs")  # NEW
    actor_cleaner = models.ForeignKey(Cleaner, null=True, blank=True, on_delete=models.SET_NULL, related_name="job_action_logs")    # NEW
    message = models.TextField(blank=True)  # NEW
    created_at = models.DateTimeField(auto_now_add=True)  # NEW

    class Meta:
        ordering = ["-created_at"]  # NEW
        indexes = [models.Index(fields=["job", "created_at"])]  # NEW

    def __str__(self):
        who = self.actor_employer_id or self.actor_cleaner_id
        return f"{self.job_id} {self.action} by {who} @ {self.created_at}"  # NEW


# ---------------------------
# Ratings (two-way support base) — CLEANER REVIEW
# ---------------------------
# ---------------------------
# Ratings (two-way)
# ---------------------------

class CleanerReview(models.Model):
    """
    Employer → reviews Cleaner (one review per booking)
    - reviewer_employer: who reviewed (nullable for legacy rows)
    - booking: OneToOne ensures only one employer→cleaner review per booking
    """
    cleaner = models.ForeignKey(
        Cleaner,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    reviewer_employer = models.ForeignKey(
        Employer,
        on_delete=models.CASCADE,
        related_name="cleaner_reviews",
        null=True,
        blank=True,
    )
    booking = models.OneToOneField(
        "JobBooking",
        on_delete=models.CASCADE,
        related_name="cleaner_review",
        null=True,
        blank=True,
    )
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["cleaner", "created_at"]),
        ]

    def __str__(self):
        return f"CleanerReview(cleaner={self.cleaner_id}, rating={self.rating})"


class EmployerReview(models.Model):
    """
    Cleaner → reviews Employer (one review per booking)
    """
    employer = models.ForeignKey(
        Employer,
        on_delete=models.CASCADE,
        related_name="reviews_received",
    )
    reviewer_cleaner = models.ForeignKey(
        Cleaner,
        on_delete=models.CASCADE,
        related_name="employer_reviews",
    )
    booking = models.OneToOneField(
        "JobBooking",
        on_delete=models.CASCADE,
        related_name="employer_review",
    )
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["employer", "created_at"])]
