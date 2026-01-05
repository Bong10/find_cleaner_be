from datetime import datetime
from django.db.models import Q, Exists, OuterRef, Count, Subquery, Avg, Value
from django.db.models.functions import Coalesce
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db import IntegrityError, transaction
from rest_framework.exceptions import ValidationError
from rest_framework import permissions
from users.serializers import EmployerDetailSerializer

from chat.models import Chat 
from notifications.utils import create_notification
from notifications.tasks import send_notification
from notifications import events
from django.contrib.contenttypes.models import ContentType

from .models import (
    Job, JobApplication, Shortlist, JobBooking, JobService, CleanerService,
    CleanerReview, JobActionLog, Payment, EmployerReview,  # add Payment (and EmployerReview if not already here)
)

from .serializers import (
    JobCreateUpdateSerializer, JobListSerializer, JobDetailSerializer,
    JobApplicationCreateSerializer, JobApplicationListSerializer,
    ShortlistCreateSerializer, ShortlistListSerializer, JobBookingSerializer,
    JobServiceSerializer, CleanerServiceSerializer, JobMetricsSerializer,
    CleanerDiscoverySerializer, JobActionLogSerializer,  # NEW
)
from .permissions import IsJobOwnerOrReadOnly
from users.models import Employer, Cleaner, User
from services.models import Service
from .models import EmployerReview  # NEW




# ---------------------------
# Helpers (availability)
# ---------------------------

def _parse_minutes(time_str: str) -> int:
    try:
        t = datetime.strptime(time_str, "%H:%M")
        return t.hour * 60 + t.minute
    except Exception:
        return -1


def _overlaps(start_a: int, dur_a: int, start_b: int, dur_b: int) -> bool:
    end_a = start_a + dur_a
    end_b = start_b + dur_b
    return not (end_a <= start_b or end_b <= start_a)


def _has_conflict(cleaner: Cleaner, date_obj, start_time_str: str, hours_required: int) -> bool:
    start_m = _parse_minutes(start_time_str)
    if start_m < 0:
        return False
    dur_m = int(hours_required) * 60
    bookings = JobBooking.objects.select_related("job").filter(
        cleaner=cleaner,
        job__date=date_obj,
        status__in=["cf", "cp"],
    )
    for b in bookings:
        bm = _parse_minutes(b.job.time)
        if bm >= 0 and _overlaps(start_m, dur_m, bm, int(b.job.hours_required) * 60):
            return True
    return False


def get_employer_for_user(user):
    if hasattr(user, "employer"):
        return user.employer
    raise PermissionError("Only employers can perform this action.")


def _log(job: Job, action: str, *, employer: Employer | None = None, cleaner: Cleaner | None = None, message: str = ""):  # NEW
    JobActionLog.objects.create(  # NEW
        job=job, action=action, actor_employer=employer, actor_cleaner=cleaner, message=message
    )


# ---------------------------
# Jobs
# ---------------------------

class JobViewSet(viewsets.ModelViewSet):
    queryset = Job.objects.all().select_related("employer").prefetch_related("services")
    # permission_classes = [IsAuthenticated, IsJobOwnerOrReadOnly]
    lookup_field = "job_id"

    def get_permissions(self):
        # Public (no login) can view jobs
        if self.action in ["list", "retrieve", "employer"]:
            return [permissions.AllowAny()]
        # Logged-in users required for create/update/delete
        return [permissions.IsAuthenticated()]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = {
        "status": ["exact", "in"],
        "date": ["exact", "gte", "lte"],
        "services": ["exact"],
        "is_archived": ["exact"],
    }
    search_fields = ["title", "description", "location"]
    ordering_fields = ["created_at", "date", "hourly_rate"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return JobCreateUpdateSerializer
        if self.action == "list":
            return JobListSerializer
        return JobDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset().filter(is_archived=False)
        user = self.request.user

        mine = self.request.query_params.get("mine")
        if mine == "true" and hasattr(user, "employer"):
            return qs.filter(employer_id=user.employer.id)
        if self.action == "list":
            return qs.filter(status="o")
        return qs

    def perform_create(self, serializer):
        employer = get_employer_for_user(self.request.user)
        job = serializer.save(employer=employer, status="o")
        _log(job, "job_create", employer=employer, message="Job created")  # NEW

    def perform_update(self, serializer):
        instance = self.get_object()
        if instance.status in ("t", "ip", "c"):
            raise PermissionError("You can only edit jobs that are open/pending.")
        job = serializer.save()
        _log(job, "job_update", employer=getattr(self.request.user, "employer", None), message="Job updated")  # NEW

    def destroy(self, request, *args, **kwargs):
        job = self.get_object()
        if job.is_archived:
            return Response({"detail": "Already archived."}, status=200)
        from django.utils.timezone import now
        job.is_archived = True
        job.archived_at = now()
        job.save(update_fields=["is_archived", "archived_at"])
        _log(job, "job_update", employer=getattr(request.user, "employer", None), message="Job archived")  # NEW
        return Response(status=204)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsJobOwnerOrReadOnly])
    def close(self, request, job_id=None):
        job = self.get_object()
        job.status = "c"
        job.save(update_fields=["status"])
        _log(job, "job_close", employer=request.user.employer, message="Job closed")  # NEW
        return Response({"detail": "Job closed.", "status": job.status})

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsJobOwnerOrReadOnly])
    def reopen(self, request, job_id=None):
        job = self.get_object()
        if JobApplication.objects.filter(job_id=job.job_id, status="a").exists():
            return Response({"detail": "Cannot reopen a job with an accepted application."}, status=400)
        job.status = "o"
        job.save(update_fields=["status"])
        _log(job, "job_reopen", employer=request.user.employer, message="Job reopened")  # NEW
        return Response({"detail": "Job reopened.", "status": job.status})

    # ---------- Employer job metrics ----------
    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated], url_path="metrics")
    def metrics(self, request):
        if not hasattr(request.user, "employer"):
            return Response({"detail": "Only employers can view metrics."}, status=403)

        employer_id = request.user.employer.id

        latest_booking_status = Subquery(
            JobBooking.objects.filter(job=OuterRef("pk"))
            .order_by("-booking_id")
            .values("status")[:1]
        )

        qs = (
            Job.objects.filter(employer_id=employer_id, is_archived=False)
            .annotate(
                applicants_total=Count("jobapplication", distinct=True),
                applicants_pending=Count(
                    "jobapplication", filter=Q(jobapplication__status="p"), distinct=True
                ),
                applicants_accepted=Count(
                    "jobapplication", filter=Q(jobapplication__status="a"), distinct=True
                ),
                has_booking=Exists(JobBooking.objects.filter(job_id=OuterRef("pk"))),
                latest_booking_status=latest_booking_status,
            )
            .order_by("-created_at")
        )

        page = self.paginate_queryset(qs)
        serializer = JobMetricsSerializer(page or qs, many=True)
        return self.get_paginated_response(serializer.data) if page is not None else Response(serializer.data)

    # ---------- Job audit feed ----------
    @action(detail=True, methods=["get"], permission_classes=[IsAuthenticated], url_path="audit")  # NEW
    def audit(self, request, job_id=None):  # NEW
        job = self.get_object()
        logs = job.audit_logs.all()
        page = self.paginate_queryset(logs)
        ser = JobActionLogSerializer(page or logs, many=True)
        return self.get_paginated_response(ser.data) if page is not None else Response(ser.data)

    @action(detail=True, methods=["get"], url_path="employer")
    def employer(self, request, job_id=None):
        job = self.get_object()
        ser = EmployerDetailSerializer(job.employer)
        return Response(ser.data)


# ---------------------------
# Applications (with conflict check + audit)
# ---------------------------

class JobApplicationViewSet(
    viewsets.GenericViewSet, mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin
):
    queryset = JobApplication.objects.all().select_related("job", "cleaner")
    permission_classes = [IsAuthenticated]
    lookup_field = "application_id"

    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = {"job": ["exact"], "status": ["exact", "in"], "date_applied": ["gte", "lte"]}
    ordering_fields = ["date_applied"]
    ordering = ["-date_applied"]

    def get_serializer_class(self):
        return JobApplicationCreateSerializer if self.action == "create" else JobApplicationListSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if hasattr(user, "employer"):
            return qs.filter(job__employer_id=user.employer.id)
        elif hasattr(user, "cleaner"):
            return qs.filter(cleaner_id=user.cleaner.id)
        return qs.none()

    def perform_create(self, serializer):
        try:
            with transaction.atomic():
                application = serializer.save()
                # Notification for employer
                create_notification(
                    recipient=application.job.employer.user,
                    actor=application.cleaner.user,
                    verb='applied for your job',
                    target=application.job
                )
        except IntegrityError:
            raise ValidationError({"non_field_errors": ["You have already applied to this job."]})

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def accept(self, request, application_id=None):
        app = self.get_object()
        user = request.user
        if not hasattr(user, "employer") or app.job.employer_id != user.employer.id:
            return Response({"detail": "Only the job owner can accept applications."}, status=403)
        if app.status != "p":
            return Response({"detail": "Only pending applications can be accepted."}, status=400)

        if _has_conflict(app.cleaner, app.job.date, app.job.time, app.job.hours_required):
            return Response({"detail": "Cleaner has a conflicting booking at that time."}, status=409)

        from django.utils.timezone import now  # NEW
        app.status = "a"
        app.accepted_by = user.employer          # NEW
        app.accepted_at = now()                  # NEW
        app.rejected_by = None                   # NEW
        app.rejected_at = None                   # NEW
        app.rejection_reason = ""                # NEW
        app.save(update_fields=["status", "accepted_by", "accepted_at", "rejected_by", "rejected_at", "rejection_reason"])

        # In-app notification for cleaner
        create_notification(
            recipient=app.cleaner.user,
            actor=app.job.employer.user,
            verb='accepted your application for',
            target=app.job
        )
        
        # Multi-channel notification to cleaner
        send_notification.delay(
            event_type=events.APPLICATION_ACCEPTED,
            user_id=app.cleaner.user.id,
            context={
                'cleaner_name': app.cleaner.user.get_full_name() or app.cleaner.user.username,
                'employer_name': app.job.employer.user.get_full_name() or app.job.employer.user.username,
                'job_title': app.job.title,
                'job_id': app.job.job_id,
                'application_id': app.application_id,
            }
        )

        job = app.job
        if job.status == "o":
            job.status = "t"
            job.save(update_fields=["status"])
        booking, _ = JobBooking.objects.get_or_create(job=job, cleaner=app.cleaner, defaults={"status": "cf"})
        _log(job, "app_accept", employer=user.employer, message=f"Accepted application {app.application_id}")  # NEW
        _log(job, "booking_create", employer=user.employer, message=f"Booking {booking.booking_id} created/ensured")  # NEW
        return Response({"detail": "Application accepted."})

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def reject(self, request, application_id=None):
        app = self.get_object()
        user = request.user
        if not hasattr(user, "employer") or app.job.employer_id != user.employer.id:
            return Response({"detail": "Only the job owner can reject applications."}, status=403)
        if app.status != "p":
            return Response({"detail": "Only pending applications can be rejected."}, status=400)

        reason = request.data.get("reason", "")  # NEW
        from django.utils.timezone import now    # NEW
        app.status = "r"
        app.rejected_by = user.employer          # NEW
        app.rejected_at = now()                  # NEW
        app.rejection_reason = reason[:255] if reason else ""  # NEW
        app.accepted_by = None                   # NEW
        app.accepted_at = None                   # NEW
        app.save(update_fields=["status", "rejected_by", "rejected_at", "rejection_reason", "accepted_by", "accepted_at"])
        
        # In-app notification for cleaner
        create_notification(
            recipient=app.cleaner.user,
            actor=app.job.employer.user,
            verb='rejected your application for',
            target=app.job,
            description=f"Reason: {app.rejection_reason}" if app.rejection_reason else None
        )
        
        # Multi-channel notification to cleaner
        send_notification.delay(
            event_type=events.APPLICATION_REJECTED,
            user_id=app.cleaner.user.id,
            context={
                'cleaner_name': app.cleaner.user.get_full_name() or app.cleaner.user.username,
                'employer_name': app.job.employer.user.get_full_name() or app.job.employer.user.username,
                'job_title': app.job.title,
                'job_id': app.job.job_id,
                'application_id': app.application_id,
                'rejection_reason': app.rejection_reason or 'No reason provided',
            }
        )

        _log(app.job, "app_reject", employer=user.employer, message=f"Rejected application {app.application_id}. Reason: {app.rejection_reason}")  # NEW
        return Response({"detail": "Application rejected."})


# ---------------------------
# Shortlist (uses default id) + audit
# ---------------------------

class ShortlistViewset(
    viewsets.GenericViewSet, mixins.CreateModelMixin, mixins.DestroyModelMixin, mixins.ListModelMixin
):
    queryset = Shortlist.objects.all().select_related("job", "cleaner")
    permission_classes = [IsAuthenticated]
    lookup_field = "id"

    def get_serializer_class(self):
        return ShortlistCreateSerializer if self.action == "create" else ShortlistListSerializer

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, "employer"):
            return self.queryset.filter(job__employer_id=user.employer.id)
        if hasattr(user, "cleaner"):  # <-- add this branch
            return self.queryset.filter(cleaner_id=user.cleaner.id)
        return self.queryset.none()


    def perform_create(self, serializer):  # NEW
        sl = serializer.save()
        # In-app notification for cleaner
        create_notification(
            recipient=sl.cleaner.user,
            actor=sl.job.employer.user,
            verb='shortlisted you for the job',
            target=sl.job
        )
        # Multi-channel notification
        send_notification.delay(
            event_type=events.SHORTLIST_ADDED,
            user_id=sl.cleaner.user.id,
            context={
                'cleaner_name': sl.cleaner.user.get_full_name() or sl.cleaner.user.username,
                'employer_name': sl.job.employer.user.get_full_name() or sl.job.employer.user.username,
                'job_title': sl.job.title,
                'job_id': sl.job.job_id,
            }
        )
        _log(sl.job, "shortlist_add", employer=getattr(self.request.user, "employer", None),
             message=f"Shortlisted cleaner {sl.cleaner_id}")  # NEW

    def destroy(self, request, *args, **kwargs):  # NEW
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        job = instance.job
        resp = super().destroy(request, *args, **kwargs)
        _log(job, "shortlist_remove", employer=getattr(request.user, "employer", None),
             message=f"Removed cleaner {instance.cleaner_id} from shortlist")  # NEW
        return resp


# ---------------------------
# Bookings
# ---------------------------

class JobBookingViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = JobBooking.objects.all().select_related("job", "cleaner")
    serializer_class = JobBookingSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "booking_id"

    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = {"job": ["exact"], "status": ["exact", "in"]}
    ordering_fields = ["booking_id"]

    def get_queryset(self):
        qs = super().get_queryset()
        u = self.request.user
        
        # Admins see all bookings
        if u.is_staff:
            return qs
        
        # Cleaners see their own bookings
        if hasattr(u, "cleaner"):
            return qs.filter(cleaner_id=u.cleaner.id)
        
        # Employers see bookings for their jobs
        if hasattr(u, "employer"):
            return qs.filter(job__employer_id=u.employer.id)
        
        # Other users see nothing
        return qs.none()

    # 1) Employer books cleaner -> job becomes taken, booking pending (status="p")
    @action(detail=False, methods=["post"], permission_classes=[permissions.IsAuthenticated], url_path="book")
    def book(self, request):
        job_id = request.data.get("job")
        cleaner_id = request.data.get("cleaner")
        if not job_id or not cleaner_id:
            raise ValidationError({"detail": "job and cleaner are required."})

        # Only the job owner can book
        try:
            job = Job.objects.get(pk=job_id, is_archived=False)
        except Job.DoesNotExist:
            return Response({"detail": "job not found"}, status=404)
        if not hasattr(request.user, "employer") or job.employer_id != request.user.employer.id:
            return Response({"detail": "Only the job owner can book a cleaner."}, status=403)

        # Block closed jobs
        if job.status == "c":
            return Response({"detail": "Job is closed."}, status=400)

        try:
            cleaner = Cleaner.objects.get(pk=cleaner_id)
        except Cleaner.DoesNotExist:
            return Response({"detail": "cleaner not found"}, status=404)

        booking, created = JobBooking.objects.get_or_create(
            job=job, cleaner=cleaner, defaults={"status": "p"}   # status "p" (pending)
        )

        # ensure/reuse global chat for employer<->cleaner
        chat, _ = Chat.objects.get_or_create(employer=job.employer, cleaner=cleaner)
        chat.activate_for_booking(booking)

        # Mark job taken if it was open
        if job.status == "o":
            job.status = "t"
            job.save(update_fields=["status"])
            _log(job, "booking_status", employer=request.user.employer,
                 message=f"Job marked taken after booking (booking {booking.booking_id})")

        # Notify cleaner on first creation
        if created:
            # In-app notification for cleaner
            create_notification(
                recipient=cleaner.user,
                actor=job.employer.user,
                verb='requested to book you for',
                target=job
            )
            # Multi-channel notification
            send_notification.delay(
                event_type=events.BOOKING_CREATED,
                user_id=cleaner.user.id,
                context={
                    'cleaner_name': cleaner.user.get_full_name() or cleaner.user.username,
                    'employer_name': job.employer.user.get_full_name() or job.employer.user.username,
                    'job_title': job.title,
                    'job_id': job.job_id,
                    'booking_id': booking.booking_id,
                }
            )
            _log(job, "booking_create", employer=request.user.employer,
                 message=f"Booking {booking.booking_id} created (pending)")
            return Response({"detail": "Booking created; awaiting cleaner confirmation.", "booking_id": booking.booking_id, "status": booking.status}, status=201)

        # Already booked
        return Response(
            {"detail": "This cleaner is already booked for this job.", "booking_id": booking.booking_id, "status": booking.status},
            status=409
        )

    # 2) Cleaner confirms -> still status "p" but we record confirmation flag; next step is employer pays.
    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated], url_path="confirm")
    def confirm_by_cleaner(self, request, booking_id=None):
        b = self.get_object()
        u = request.user
        if not hasattr(u, "cleaner") or u.cleaner.id != b.cleaner_id:
            return Response({"detail": "Only the booked cleaner can confirm."}, status=403)
        if b.status not in ["p", "r"]:
            return Response({"detail": f"Cannot confirm from status '{b.status}'."}, status=400)
        if b.status == "r":
            return Response({"detail": "This booking was rejected."}, status=400)

        if b.cleaner_confirmed:
            return Response({"detail": "Already confirmed by cleaner."}, status=200)

        b.cleaner_confirmed = True
        b.save(update_fields=["cleaner_confirmed"])

        # In-app notification for employer
        create_notification(
            recipient=b.job.employer.user,
            actor=u,
            verb='confirmed your booking for',
            target=b.job
        )

        # Multi-channel notification to employer
        send_notification.delay(
            event_type=events.BOOKING_CONFIRMED,
            user_id=b.job.employer.user.id,
            context={
                'employer_name': b.job.employer.user.get_full_name() or b.job.employer.user.username,
                'cleaner_name': u.get_full_name() or u.username,
                'job_title': b.job.title,
                'job_id': b.job.job_id,
                'booking_id': b.booking_id,
            }
        )
        _log(b.job, "booking_status", cleaner=u.cleaner,
             message=f"Cleaner confirmed booking {b.booking_id}; awaiting payment")
        return Response({"detail": "Confirmed by cleaner. Awaiting employer payment.", "status": b.status})

    # 3) Employer pays -> booking becomes "cf" (confirmed)
    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated], url_path="pay")
    def pay(self, request, booking_id=None):
        b = self.get_object()
        u = request.user
        if not hasattr(u, "employer") or u.employer.id != b.job.employer_id:
            return Response({"detail": "Only the job owner can pay."}, status=403)
        if b.status != "p":
            return Response({"detail": f"Cannot pay from status '{b.status}'."}, status=400)
        if not b.cleaner_confirmed:
            return Response({"detail": "Cleaner has not confirmed yet."}, status=400)

        # Create or attach a Payment; for now, just store a reference nicely
        ref = (request.data.get("payment_reference") or "").strip()
        if not ref:
            ref = f"MANUAL-{b.booking_id}"

        # Optional: create a Payment row (you already have a stub Payment model)
        if not b.payment_id:
            pay = Payment.objects.create(name=ref)
            b.payment = pay

        from django.utils.timezone import now
        b.payment_reference = ref
        b.paid_at = now()
        b.status = "cf"  # confirmed
        b.save(update_fields=["payment", "payment_reference", "paid_at", "status"])

        # In-app notification for cleaner
        create_notification(
            recipient=b.cleaner.user,
            actor=b.job.employer.user,
            verb='payment was confirmed for',
            target=b.job
        )

        # Multi-channel notification to cleaner
        send_notification.delay(
            event_type=events.PAYMENT_RECEIVED,
            user_id=b.cleaner.user.id,
            context={
                'cleaner_name': b.cleaner.user.get_full_name() or b.cleaner.user.username,
                'employer_name': b.job.employer.user.get_full_name() or b.job.employer.user.username,
                'job_title': b.job.title,
                'job_id': b.job.job_id,
                'booking_id': b.booking_id,
                'amount': str(b.payment),
            }
        )
        _log(b.job, "booking_status", employer=u.employer,
             message=f"Booking {b.booking_id} paid -> status cf")
        return Response({"detail": "Payment recorded. Booking confirmed.", "status": b.status})

    # 4) Employer completes -> booking "cp", job "c"
    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated], url_path="complete")
    def complete(self, request, booking_id=None):
        b = self.get_object()
        u = request.user
        if not hasattr(u, "employer") or u.employer.id != b.job.employer_id:
            return Response({"detail": "Only the job owner can complete the job."}, status=403)
        if b.status not in ["cf"]:   # allow only after confirmation/payment
            return Response({"detail": f"Cannot complete from status '{b.status}'."}, status=400)

        b.status = "cp"
        b.save(update_fields=["status"])

        job = b.job
        if job.status != "c":
            job.status = "c"
            job.save(update_fields=["status"])

        # archive chat only if no other bookings remain active for this pair
        has_other_active = JobBooking.objects.filter(
            job__employer=job.employer,
            cleaner=b.cleaner,
            status__in=["p", "cf"]
        ).exists()

        chat = Chat.objects.filter(employer=job.employer, cleaner=b.cleaner).first()
        if chat and not has_other_active:
            chat.archive(reason="All bookings completed/closed")

        # Multi-channel notification to cleaner
        send_notification.delay(
            event_type=events.BOOKING_COMPLETED,
            user_id=b.cleaner.user.id,
            context={
                'cleaner_name': b.cleaner.user.get_full_name() or b.cleaner.user.username,
                'employer_name': job.employer.user.get_full_name() or job.employer.user.username,
                'job_title': job.title,
                'job_id': job.job_id,
                'booking_id': b.booking_id,
            }
        )
        _log(job, "booking_status", employer=u.employer,
             message=f"Booking {b.booking_id} -> cp; job -> c")
        return Response({"detail": "Booking completed. Job closed.", "booking_status": b.status, "job_status": job.status})

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated], url_path="review-cleaner")
    def review_cleaner(self, request, booking_id=None):
        b = self.get_object()
        u = request.user

        # Must be job owner
        if not hasattr(u, "employer") or u.employer.id != b.job.employer_id:
            return Response({"detail": "Only the job owner can review the cleaner."}, status=403)

        # Only after completion
        if b.status != "cp":
            return Response({"detail": "You can review only after the booking is completed."}, status=400)

        # One review per booking
        if hasattr(b, "cleaner_review"):
            return Response({"detail": "You have already reviewed this cleaner for this booking."}, status=400)

        try:
            rating = int(request.data.get("rating", 0))
        except (TypeError, ValueError):
            rating = 0
        comment = (request.data.get("comment") or "").strip()

        if rating < 1 or rating > 5:
            return Response({"detail": "Rating must be between 1 and 5."}, status=400)

        cr = CleanerReview.objects.create(
            cleaner=b.cleaner,
            reviewer_employer=u.employer,
            booking=b,
            rating=rating,
            comment=comment,
        )

        # In-app notification for cleaner
        create_notification(
            recipient=b.cleaner.user,
            actor=u.employer.user,
            verb='left a review for your work on',
            target=b.job,
            description=f'Rating: {rating}/5'
        )

        # Multi-channel notification to cleaner
        send_notification.delay(
            event_type=events.NEW_REVIEW,
            user_id=b.cleaner.user.id,
            context={
                'recipient_name': b.cleaner.user.get_full_name() or b.cleaner.user.username,
                'reviewer_name': u.employer.user.get_full_name() or u.employer.user.username,
                'job_title': b.job.title,
                'job_id': b.job.job_id,
                'booking_id': b.booking_id,
                'rating': rating,
                'comment': comment or 'No comment provided',
            }
        )

        _log(b.job, "booking_status", employer=u.employer,
            message=f"Employer reviewed cleaner (rating {rating}) for booking {b.booking_id}")
        return Response({"detail": "Review submitted.", "rating": cr.rating}, status=201)


    # CLEANER → reviews EMPLOYER
    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated], url_path="review-employer")
    def review_employer(self, request, booking_id=None):
        b = self.get_object()
        u = request.user

        # Must be assigned cleaner
        if not hasattr(u, "cleaner") or u.cleaner.id != b.cleaner_id:
            return Response({"detail": "Only the assigned cleaner can review the employer."}, status=403)

        # Only after completion
        if b.status != "cp":
            return Response({"detail": "You can review only after the booking is completed."}, status=400)

        # One review per booking
        if hasattr(b, "employer_review"):
            return Response({"detail": "You have already reviewed this employer for this booking."}, status=400)

        try:
            rating = int(request.data.get("rating", 0))
        except (TypeError, ValueError):
            rating = 0
        comment = (request.data.get("comment") or "").strip()

        if rating < 1 or rating > 5:
            return Response({"detail": "Rating must be between 1 and 5."}, status=400)

        er = EmployerReview.objects.create(
            employer=b.job.employer,
            reviewer_cleaner=u.cleaner,
            booking=b,
            rating=rating,
            comment=comment,
        )

        # In-app notification for employer
        create_notification(
            recipient=b.job.employer.user,
            actor=u.cleaner.user,
            verb='left a review for you on',
            target=b.job,
            description=f'Rating: {rating}/5'
        )

        # Multi-channel notification to employer
        send_notification.delay(
            event_type=events.NEW_REVIEW,
            user_id=b.job.employer.user.id,
            context={
                'recipient_name': b.job.employer.user.get_full_name() or b.job.employer.user.username,
                'reviewer_name': u.cleaner.user.get_full_name() or u.cleaner.user.username,
                'job_title': b.job.title,
                'job_id': b.job.job_id,
                'booking_id': b.booking_id,
                'rating': rating,
                'comment': comment or 'No comment provided',
            }
        )

        _log(b.job, "booking_status", cleaner=u.cleaner,
            message=f"Cleaner reviewed employer (rating {rating}) for booking {b.booking_id}")
        return Response({"detail": "Review submitted.", "rating": er.rating}, status=201)

# ---------------------------
# JobService attach/detach (with service minimums) + audit
# ---------------------------

class JobServiceViewSet(
    viewsets.GenericViewSet, mixins.CreateModelMixin, mixins.DestroyModelMixin, mixins.ListModelMixin
):
    """
    Employer attaches services to a job.
    Body: { "job": <job_id>, "service": <service_id> }
    """
    queryset = JobService.objects.all().select_related("job", "service")
    serializer_class = JobServiceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, "employer"):
            return self.queryset.filter(job__employer_id=user.employer.id)
        return self.queryset.none()

    def create(self, request, *args, **kwargs):
        job_id = request.data.get("job")
        service_id = request.data.get("service")
        if not job_id or not service_id:
            return Response({"detail": "job and service are required"}, status=400)

        try:
            job = Job.objects.get(pk=job_id)
        except Job.DoesNotExist:
            return Response({"detail": "job not found"}, status=404)
        if not hasattr(request.user, "employer") or job.employer_id != request.user.employer.id:
            return Response({"detail": "Only job owner can attach services."}, status=403)

        try:
            svc = Service.objects.get(pk=service_id, active=True)
        except Service.DoesNotExist:
            return Response({"detail": "service not found or inactive"}, status=404)

        if job.hourly_rate < svc.min_hourly_rate:
            return Response(
                {"detail": f"Job hourly_rate ({job.hourly_rate}) is below service minimum ({svc.min_hourly_rate}). "
                           f"Increase the job's hourly_rate first."},
                status=400,
            )
        if job.hours_required < svc.min_hours_required:
            return Response(
                {"detail": f"Job hours_required ({job.hours_required}) is below service minimum ({svc.min_hours_required}). "
                           f"Increase the job's hours_required first."},
                status=400,
            )

        resp = super().create(request, *args, **kwargs)
        _log(job, "service_attach", employer=request.user.employer, message=f"Attached service {service_id}")  # NEW
        return resp

    def destroy(self, request, *args, **kwargs):  # NEW
        instance: JobService = self.get_object()
        if not hasattr(request.user, "employer") or instance.job.employer_id != request.user.employer.id:
            return Response({"detail": "Only job owner can detach services."}, status=403)
        job = instance.job
        service_id = instance.service_id
        resp = super().destroy(request, *args, **kwargs)
        _log(job, "service_detach", employer=request.user.employer, message=f"Detached service {service_id}")  # NEW
        return resp


# ---------------------------
# Cleaner advertises services
# ---------------------------

class CleanerServiceViewSet(
    viewsets.GenericViewSet, mixins.CreateModelMixin, mixins.DestroyModelMixin, mixins.ListModelMixin
):
    """
    Cleaner advertises which services they provide.
    Body: { "service": <service_id> } ; cleaner inferred from token
    """
    queryset = CleanerService.objects.all().select_related("cleaner", "service")
    serializer_class = CleanerServiceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, "cleaner"):
            return self.queryset.filter(cleaner_id=user.cleaner.id)
        return self.queryset.none()

    def create(self, request, *args, **kwargs):
        if not hasattr(request.user, "cleaner"):
            return Response({"detail": "Only cleaners can add services."}, status=403)
        data = request.data.copy()
        data["cleaner"] = request.user.cleaner.id
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=201)


# ---------------------------
# Cleaner discovery (employer-only)
# ---------------------------

class CleanerDiscoveryViewSet(viewsets.GenericViewSet, mixins.ListModelMixin):
    """
    GET /api/cleaners-search/?service=ID&location=yaounde&min_rating=4&date=2025-09-02&time=09:00&hours=3&only_available=true
    """
    permission_classes = [IsAuthenticated]
    serializer_class = CleanerDiscoverySerializer

    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["user__name", "user__address"]
    ordering_fields = ["id", "rating_avg"]
    ordering = ["id"]

    def get_queryset(self):
        user = self.request.user
        if not hasattr(user, "employer"):
            return Cleaner.objects.none()

        qs = Cleaner.objects.select_related("user").prefetch_related(
            "cleanerservice_set__service"
        )
        qs = qs.annotate(
            rating_avg=Coalesce(Avg("reviews__rating"), Value(0.0))
        )

        service_id = self.request.query_params.get("service")
        if service_id:
            qs = qs.filter(cleanerservice__service_id=service_id)

        location = self.request.query_params.get("location")
        if location:
            qs = qs.filter(user__address__icontains=location)

        min_rating = self.request.query_params.get("min_rating")
        if min_rating:
            try:
                mr = float(min_rating)
                qs = qs.filter(rating_avg__gte=mr)
            except ValueError:
                pass

        date_str = self.request.query_params.get("date")
        time_str = self.request.query_params.get("time")
        hours = self.request.query_params.get("hours")
        only_avail = self.request.query_params.get("only_available")

        self._availability_ctx = None
        if date_str and time_str and hours:
            try:
                from datetime import date as _d
                y, m, d = [int(p) for p in date_str.split("-")]
                date_obj = _d(y, m, d)
                hrs = int(hours)
                self._availability_ctx = (date_obj, time_str, hrs)
            except Exception:
                self._availability_ctx = None

        self._only_available = (only_avail == "true")
        return qs

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        ctx = getattr(self, "_availability_ctx", None)
        only_available = getattr(self, "_only_available", False)
        if ctx:
            date_obj, time_str, hrs = ctx
            result = []
            for c in queryset:
                available = not _has_conflict(c, date_obj, time_str, hrs)
                setattr(c, "_is_available", available)
                services = [cs.service for cs in getattr(c, "cleanerservice_set").all()]
                setattr(c, "_services_cache", services)
                if only_available and not available:
                    continue
                result.append(c)
            queryset = result
        else:
            for c in queryset:
                services = [cs.service for cs in getattr(c, "cleanerservice_set").all()]
                setattr(c, "_services_cache", services)

        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page or queryset, many=True, context={"request": request})
        return self.get_paginated_response(serializer.data) if page is not None else Response(serializer.data)
