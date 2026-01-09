from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from email.mime.base import MIMEBase
from email import encoders
import os
from .models import Employer, Cleaner, Role, User, Admin, PasswordResetAttempt, PasswordHistory, LoginAttempt, CleanerReference
# Register your models here.
admin.site.register(Role)
admin.site.register(Employer)
admin.site.register(Admin)
#admin.site.register(Cleaner)  # Using custom admin below
#admin.site.register(User)


def get_display_name(user):
    """
    Get a friendly display name for a user.
    Priority: user.name > parsed email > generic fallback
    """
    # First try user.name
    if hasattr(user, 'name') and user.name and user.name.strip():
        return user.name.strip()
    
    # Fallback to parsing email
    if user.email:
        email_username = user.email.split('@')[0]
        
        # If has separators (dots, underscores), split and capitalize
        if '.' in email_username or '_' in email_username:
            name = email_username.replace('.', ' ').replace('_', ' ').title()
            # Remove any trailing numbers
            import re
            name = re.sub(r'\d+$', '', name).strip()
            if name:
                return name
        
        # If no separators, check if it looks name-like
        # If it has numbers mixed in or is too long, use generic greeting
        import re
        if re.search(r'\d', email_username) or len(email_username) > 15:
            return "there"  # Results in "Hello there,"
        
        # Simple username without numbers - capitalize it
        return email_username.title()
    
    return "there"


def send_verification_email(cleaner, approved=True, reason=None):
    """
    Send verification status email to cleaner.
    
    Args:
        cleaner: Cleaner instance
        approved: True if approved, False if rejected/on hold
        reason: Rejection/hold reason (optional)
    """
    user = cleaner.user
    display_name = get_display_name(user)
    
    # Select template and subject based on approval status
    if approved:
        template_path = os.path.join(settings.BASE_DIR, 'users', 'templates', 'verification_approved_email.html')
        subject = '✅ Your Find Cleaner Account Has Been Verified!'
        context = {
            'name': display_name,
            'login_url': f"{getattr(settings, 'FRONTEND_ORIGIN', 'http://localhost:3000')}/login",
            'frontend_url': getattr(settings, 'FRONTEND_ORIGIN', 'http://localhost:3000'),
            'support_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'support@digitalwebsolutions.co.uk'),
        }
    else:
        template_path = os.path.join(settings.BASE_DIR, 'users', 'templates', 'verification_rejected_email.html')
        subject = '⚠️ Action Required: Find Cleaner Account Verification Update'
        context = {
            'name': display_name,
            'reason': reason or 'Additional information or documents are required for verification.',
            'profile_url': f"{getattr(settings, 'FRONTEND_ORIGIN', 'http://localhost:3000')}/profile/edit",
            'frontend_url': getattr(settings, 'FRONTEND_ORIGIN', 'http://localhost:3000'),
            'support_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'support@digitalwebsolutions.co.uk'),
        }
    
    html_content = render_to_string(template_path, context)
    text_content = f'Hello {display_name}, your Find Cleaner account verification status has been updated.'
    
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@example.com"),
        to=[user.email],
    )
    email.attach_alternative(html_content, "text/html")
    
    # Attach inline logo
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'logo.png')
    if os.path.exists(logo_path):
        with open(logo_path, 'rb') as f:
            logo = MIMEBase('image', 'png')
            logo.set_payload(f.read())
            encoders.encode_base64(logo)
            logo.add_header('Content-ID', '<logo>')
            logo.add_header('Content-Disposition', 'inline', filename='logo.png')
            email.attach(logo)
    
    email.send()

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display=['id','email','name']


class CleanerReferenceInline(admin.TabularInline):
    """Inline display of cleaner references for background checks."""
    model = CleanerReference
    extra = 0
    fields = ['reference_type', 'name', 'relationship', 'email', 'phone', 'verified', 'created_at']
    readonly_fields = ['created_at']
    can_delete = True


@admin.register(Cleaner)
class CleanerAdmin(admin.ModelAdmin):
    """
    ADMIN VERIFICATION WORKFLOW: Review and approve cleaner accounts.
    Verify documents, check references, and approve/reject applications.
    """
    list_display = [
        'id', 
        'get_email', 
        'get_name', 
        'clean_level', 
        'get_verification_badge',
        'average_rating',
        'total_reviews',
        'user'
    ]
    list_filter = [
        'is_verified_by_admin',
        'clean_level',
        'user__is_active'
    ]
    search_fields = [
        'user__email',
        'user__name',
        'city',
        'postcode',
        'dbs_certificate_number'
    ]
    readonly_fields = [
        'user',
        'verified_at',
        'get_id_front_link',
        'get_id_back_link',
        'get_cv_link',
        'average_rating',
        'total_reviews'
    ]
    
    fieldsets = (
        ('User Account', {
            'fields': ('user',)
        }),
        ('Personal Information', {
            'fields': (
                'date_of_birth',
                'clean_level',
                'years_of_experience',
                'dbs_check'
            )
        }),
        ('Address Details', {
            'fields': (
                'address_line1',
                'address_line2',
                'city',
                'county',
                'postcode',
                'country'
            )
        }),
        ('Service Preferences', {
            'fields': (
                'minimum_hours',
                'availability',
                'service_areas'
            )
        }),
        ('Verification Documents', {
            'fields': (
                'get_id_front_link',
                'id_verified',
                'get_id_back_link',
                'get_cv_link',
                'dbs_certificate_number',
                'dbs_verified',
                'references_verified',
                'insurance_details',
                'portfolio'
            )
        }),
        ('Admin Verification', {
            'fields': (
                'is_verified_by_admin',
                'verified_by',
                'verified_at'
            ),
            'classes': ('collapse',)
        }),
        ('Reviews & Ratings', {
            'fields': (
                'average_rating',
                'total_reviews'
            )
        })
    )
    
    actions = ['approve_cleaners', 'reject_cleaners']
    
    def approve_cleaners(self, request, queryset):
        """Bulk action: Approve selected cleaners and send emails."""
        from django.utils import timezone
        approved_count = 0
        email_count = 0
        
        for cleaner in queryset.filter(is_verified_by_admin=False):
            cleaner.is_verified_by_admin = True
            # Safely get admin profile (avoid crash if user has no Admin)
            try:
                cleaner.verified_by = request.user.admin
            except Exception:
                cleaner.verified_by = Admin.objects.filter(user=request.user).first()
            cleaner.verified_at = timezone.now()
            cleaner.save()
            approved_count += 1
            
            try:
                send_verification_email(cleaner, approved=True)
                email_count += 1
            except Exception:
                pass
        
        self.message_user(
            request,
            f"✓ {approved_count} cleaner(s) approved. {email_count} email(s) sent successfully.",
            level='success'
        )
    approve_cleaners.short_description = "✓ Approve selected cleaners"
    
    def reject_cleaners(self, request, queryset):
        """Bulk action: Reject/unverify selected cleaners and send emails."""
        rejected_count = 0
        email_count = 0
        
        for cleaner in queryset.filter(is_verified_by_admin=True):
            cleaner.is_verified_by_admin = False
            cleaner.verified_by = None
            cleaner.verified_at = None
            cleaner.save()
            rejected_count += 1
            
            try:
                send_verification_email(cleaner, approved=False)
                email_count += 1
            except Exception:
                pass
        
        self.message_user(
            request,
            f"⚠ {rejected_count} cleaner(s) unverified. {email_count} email(s) sent successfully.",
            level='warning'
        )
    reject_cleaners.short_description = "✗ Unverify selected cleaners"
    
    inlines = [CleanerReferenceInline]
    
    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'Email'
    get_email.admin_order_field = 'user__email'
    
    def get_name(self, obj):
        return obj.user.name or '-'
    get_name.short_description = 'Name'
    get_name.admin_order_field = 'user__name'
    
    def get_verification_badge(self, obj):
        """Visual badge showing verification status."""
        if obj.is_verified_by_admin:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">✓ VERIFIED</span>'
            )
        return format_html(
            '<span style="background-color: #ffc107; color: black; padding: 3px 10px; border-radius: 3px; font-weight: bold;">⏳ PENDING</span>'
        )
    get_verification_badge.short_description = 'Verification Status'
    
    def get_id_front_link(self, obj):
        """Clickable link to view ID front document."""
        if obj.id_document_front:
            return format_html(
                '<a href="{}" target="_blank">📄 View ID Front</a>',
                obj.id_document_front.url
            )
        return '-'
    get_id_front_link.short_description = 'ID Document (Front)'
    
    def get_id_back_link(self, obj):
        """Clickable link to view ID back document."""
        if obj.id_document_back:
            return format_html(
                '<a href="{}" target="_blank">📄 View ID Back</a>',
                obj.id_document_back.url
            )
        return '-'
    get_id_back_link.short_description = 'ID Document (Back)'
    
    def get_cv_link(self, obj):
        """Clickable link to view CV/resume."""
        if obj.cv:
            return format_html(
                '<a href="{}" target="_blank">📄 View CV</a>',
                obj.cv.url
            )
        return '-'
    get_cv_link.short_description = 'CV/Resume'
    
    def save_model(self, request, obj, form, change):
        """
        Auto-verify account when all document verifications are approved.
        Sends email notification when verification status changes.
        """
        send_email = False
        approved = False
        was_verified = obj.is_verified_by_admin if change else False
        
        # Auto-approve account if all verifications are approved
        verification_fields_changed = any(
            field in form.changed_data 
            for field in ['id_verified', 'dbs_verified', 'references_verified']
        )
        
        if verification_fields_changed or not change:
            all_approved = (
                obj.id_verified == 'approved' and 
                obj.references_verified == 'approved'
            )
            
            if all_approved and not obj.is_verified_by_admin:
                # Auto-verify the account
                obj.is_verified_by_admin = True
                if not obj.verified_by:
                    # Safely get admin profile (avoid crash if user has no Admin)
                    try:
                        obj.verified_by = request.user.admin
                    except Exception:
                        obj.verified_by = Admin.objects.filter(user=request.user).first()
                from django.utils import timezone
                obj.verified_at = timezone.now()
                send_email = True
                approved = True
            elif not all_approved and obj.is_verified_by_admin and change:
                # Unverify if any verification is no longer approved
                obj.is_verified_by_admin = False
                obj.verified_by = None
                obj.verified_at = None
                if was_verified:
                    send_email = True
                    approved = False
        
        # Handle manual is_verified_by_admin changes (if admin unchecks it manually)
        if change and 'is_verified_by_admin' in form.changed_data:
            if not obj.is_verified_by_admin:
                # Admin manually unverified
                obj.verified_by = None
                obj.verified_at = None
                send_email = True
                approved = False
        
        super().save_model(request, obj, form, change)
        
        # Send email after saving
        if send_email:
            try:
                send_verification_email(obj, approved=approved)
                if approved:
                    self.message_user(request, f"✓ Cleaner verified and approval email sent to {obj.user.email}", level='success')
                else:
                    self.message_user(request, f"⚠ Verification removed and notification email sent to {obj.user.email}", level='warning')
            except Exception as e:
                self.message_user(request, f"✓ Status updated but email failed: {str(e)}", level='warning')


@admin.register(PasswordResetAttempt)
class PasswordResetAttemptAdmin(admin.ModelAdmin):
    list_display = ['email', 'ip_address', 'attempted_at']
    list_filter = ['attempted_at']
    search_fields = ['email', 'ip_address']
    readonly_fields = ['email', 'ip_address', 'attempted_at']
    ordering = ['-attempted_at']
    
    def has_add_permission(self, request):
        # Don't allow manual creation through admin
        return False


@admin.register(PasswordHistory)
class PasswordHistoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__email']
    readonly_fields = ['user', 'password_hash', 'created_at']
    ordering = ['-created_at']
    
    def has_add_permission(self, request):
        # Don't allow manual creation through admin
        return False


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    """
    SECURITY MONITORING: Track all login attempts for intrusion detection.
    Monitor failed login patterns, brute force attacks, and suspicious IP addresses.
    """
    list_display = ['email', 'success', 'ip_address', 'attempted_at', 'get_status_badge']
    list_filter = ['success', 'attempted_at']
    search_fields = ['email', 'ip_address']
    readonly_fields = ['email', 'ip_address', 'attempted_at', 'success']
    ordering = ['-attempted_at']
    date_hierarchy = 'attempted_at'
    
    def get_status_badge(self, obj):
        """Display visual badge for success/failure."""
        if obj.success:
            return '✅ Success'
        return '❌ Failed'
    get_status_badge.short_description = 'Status'
    
    def has_add_permission(self, request):
        # Don't allow manual creation through admin
        return False
    
    def get_queryset(self, request):
        """Show recent attempts first (last 30 days by default)."""
        qs = super().get_queryset(request)
        # Optionally filter to recent attempts for performance
        # from django.utils import timezone
        # from datetime import timedelta
        # cutoff = timezone.now() - timedelta(days=30)
        # return qs.filter(attempted_at__gte=cutoff)
        return qs
