from django.db import models
from django.utils import timezone
from django.conf import settings
import random
from datetime import timedelta
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from phonenumber_field.modelfields import PhoneNumberField
from django.contrib.auth.hashers import make_password

# Gestionnaire pour le modèle User
class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("L'utilisateur doit avoir une adresse email")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)  
        return self.create_user(email, password, **extra_fields)

# Modèle User principal
class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)

    # CHANGED: make non-auth fields optional so they are NOT required at registration
    phone_number = PhoneNumberField(region='CM', unique=True, null=True, blank=True)  # was required
    name = models.CharField(max_length=30, null=True, blank=True)                     # was required
    address = models.CharField(max_length=30, null=True, blank=True)                  # was required
    gender = models.CharField(max_length=10, null=True, blank=True)
    profile_picture = models.ImageField(upload_to='profiles/', null=True, blank=True)

    # ADD THIS LINE
    profile_completed = models.BooleanField(default=False)

    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    role = models.ForeignKey('Role', on_delete=models.SET_NULL, null=True, blank=True)  # lien avec le rôle

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  # CHANGED: remove phone_number → only email+password required

    objects = UserManager()

    def __str__(self):
        return self.email

    def get_full_name(self):
        """Return the user's name or email as fallback."""
        return self.name or self.email
    
    @property
    def username(self):
        """Alias for email to maintain compatibility."""
        return self.email

    def save(self, *args, **kwargs):
        # Always keep email lowercased at storage level
        if self.email:
            self.email = self.email.lower()
        
        # Track password history when password changes
        if self.pk:  # Only for existing users
            old_user = User.objects.filter(pk=self.pk).first()
            if old_user and old_user.password != self.password:
                # Password was changed, save to history
                PasswordHistory.objects.create(
                    user=self,
                    password_hash=old_user.password
                )
        
        super().save(*args, **kwargs)

# Modèle Role (rôle utilisateur)
class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)  # Nom du rôle, exemple: 'Cleaner', 'Employer', 'Admin'
    
    def __str__(self):
        return self.name

# Modèle Cleaner
class Cleaner(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # Existing fields
    portfolio = models.TextField(null=True, blank=True)
    years_of_experience = models.IntegerField(null=True, blank=True)
    dbs_check = models.BooleanField(default=False)
    insurance_details = models.CharField(max_length=255, null=True, blank=True)
    clean_level = models.IntegerField(default=1, null=True, blank=True)

    # Personal/Address fields from onboarding
    date_of_birth = models.DateField(null=True, blank=True)
    address_line1 = models.CharField(max_length=255, null=True, blank=True)
    address_line2 = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    county = models.CharField(max_length=100, null=True, blank=True)
    postcode = models.CharField(max_length=10, null=True, blank=True)
    country = models.CharField(max_length=100, default="United Kingdom", null=True, blank=True)

    # Service preferences from onboarding
    minimum_hours = models.PositiveSmallIntegerField(default=1, null=True, blank=True)
    availability = models.JSONField(default=dict, blank=True)  # {Monday: true, Tuesday: false, ...}
    
    # Service zones - backend mapping for geographic validation only
    service_zones = models.ManyToManyField(
        'services.ServiceZone',
        blank=True,
        related_name='cleaners',
        help_text="Admin-defined zones for validation (e.g., England, UK) - not shown to users"
    )
    
    # Service areas - actual cities/towns where cleaner works
    service_areas = models.JSONField(
        default=list,
        blank=True,
        help_text="""
        List of specific areas where cleaner offers services. Each area contains:
        {
            'name': 'Manchester',
            'latitude': 53.48,
            'longitude': -2.24,
            'boundary_data': {...GeoJSON polygon...},
            'osm_type': 'relation',
            'osm_id': '123456'
        }
        """
    )

    # Verification documents from onboarding
    id_document_front = models.FileField(upload_to='verification/ids/', null=True, blank=True)
    id_document_back = models.FileField(upload_to='verification/ids/', null=True, blank=True)
    cv = models.FileField(upload_to='verification/cvs/', null=True, blank=True)
    dbs_certificate_number = models.CharField(max_length=50, null=True, blank=True)
    
    # Document verification status (admin can check these individually)
    VERIFICATION_STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected - Resubmit Required'),
    ]
    
    id_verified = models.CharField(
        max_length=10, 
        choices=VERIFICATION_STATUS_CHOICES, 
        default='pending',
        help_text="ID documents verification status"
    )
    dbs_verified = models.CharField(
        max_length=10, 
        choices=VERIFICATION_STATUS_CHOICES, 
        default='pending',
        help_text="DBS certificate verification status"
    )
    references_verified = models.CharField(
        max_length=10, 
        choices=VERIFICATION_STATUS_CHOICES, 
        default='pending',
        help_text="References verification status"
    )

    # Admin verification system
    is_verified_by_admin = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey('Admin', null=True, blank=True, on_delete=models.SET_NULL, related_name='verified_cleaners')

    # Review system - auto 3 stars on creation
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=3.00)
    total_reviews = models.IntegerField(default=0)

    def __str__(self):
        return f"Cleaner {self.user.email}"
    
    def covers_location(self, latitude, longitude):
        """
        Check if cleaner offers services at the given coordinates.
        Checks each service area's boundary.
        """
        if not self.service_areas:
            return False
        
        try:
            from shapely.geometry import Point, shape
            point = Point(float(longitude), float(latitude))
            
            for area in self.service_areas:
                if area.get('boundary_data'):
                    try:
                        polygon = shape(area['boundary_data'])
                        if polygon.contains(point):
                            return True
                    except Exception:
                        continue
            return False
        except Exception:
            return False

# Modèle Employer
class Employer(models.Model):
    """Modèle pour Employer."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employer')

    # CHANGED: optional at signup; can be set later
    business_name = models.CharField(max_length=255, null=True, blank=True)  # was required
    location = models.CharField(max_length=255, null=True, blank=True)       # was required

    # Personal
    bio = models.TextField(null=True, blank=True, help_text="About You")
    
    # Address (Specific to Employer/Property)
    address_line1 = models.CharField(max_length=255, null=True, blank=True)
    address_line2 = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    county = models.CharField(max_length=100, null=True, blank=True)
    postcode = models.CharField(max_length=20, null=True, blank=True)
    
    # Property Details
    PROPERTY_TYPE_CHOICES = [
        ('apartment', 'Apartment'),
        ('house', 'House'),
        ('office', 'Office'),
        ('commercial', 'Commercial'),
    ]
    property_type = models.CharField(max_length=20, choices=PROPERTY_TYPE_CHOICES, null=True, blank=True)
    
    # Room Counts
    bedrooms = models.PositiveSmallIntegerField(null=True, blank=True, default=0)
    bathrooms = models.PositiveSmallIntegerField(null=True, blank=True, default=0)
    toilets = models.PositiveSmallIntegerField(null=True, blank=True, default=0)
    kitchens = models.PositiveSmallIntegerField(null=True, blank=True, default=0)
    rooms = models.PositiveSmallIntegerField(null=True, blank=True, default=0, help_text="For office/commercial spaces")
    
    parking_available = models.BooleanField(default=False)
    elevator_access = models.BooleanField(default=False)
    pets_in_property = models.BooleanField(default=False)
    access_instructions = models.TextField(null=True, blank=True)
    
    # Cleaning Preferences
    FREQUENCY_CHOICES = [
        ('one_time', 'One-time'),
        ('weekly', 'Weekly'),
        ('bi_weekly', 'Bi-weekly'),
        ('monthly', 'Monthly'),
    ]
    cleaning_frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, null=True, blank=True)
    
    TIME_CHOICES = [
        ('morning', 'Morning (8 AM - 12 PM)'),
        ('afternoon', 'Afternoon (12 PM - 5 PM)'),
        ('evening', 'Evening (5 PM - 9 PM)'),
        ('flexible', 'Flexible'),
    ]
    preferred_time = models.CharField(max_length=20, choices=TIME_CHOICES, null=True, blank=True)
    
    cleaning_priorities = models.JSONField(default=list, blank=True, help_text="List of priorities e.g. ['kitchen', 'bathroom']")
    special_requirements = models.TextField(null=True, blank=True)
    
    # Changed to BooleanField as per request (True=Yes, False=No)
    cleaning_supplies = models.BooleanField(default=False, null=True, blank=True)

    def __str__(self):
        return f"Employer {self.user.email} ({'Disponibility' if True else 'Indisponibility'})"

# Modèle Admin
class Admin(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    logs = models.TextField(null=True, blank=True)  # CHANGED: optional
    def __str__(self):
        return f"Admin {self.user.email}"


# Password Reset Rate Limiting
class PasswordResetAttempt(models.Model):
    """Track password reset requests for rate limiting."""
    email = models.EmailField(db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True, db_index=True)
    attempted_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-attempted_at']
        indexes = [
            models.Index(fields=['email', '-attempted_at']),
            models.Index(fields=['ip_address', '-attempted_at']),
        ]
    
    def __str__(self):
        return f"Reset attempt for {self.email} at {self.attempted_at}"


class CleanerReference(models.Model):
    """Store professional and character references for cleaners."""
    REFERENCE_TYPES = [
        ('professional', 'Professional Reference'),
        ('character', 'Character Reference'),
    ]
    
    cleaner = models.ForeignKey(Cleaner, on_delete=models.CASCADE, related_name='references')
    reference_type = models.CharField(max_length=20, choices=REFERENCE_TYPES)
    name = models.CharField(max_length=255)
    relationship = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.reference_type} reference for {self.cleaner.user.email}: {self.name}"


class LoginAttempt(models.Model):
    """Track login attempts for rate limiting and brute force prevention."""
    email = models.EmailField(db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True, db_index=True)
    attempted_at = models.DateTimeField(auto_now_add=True, db_index=True)
    success = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-attempted_at']
        indexes = [
            models.Index(fields=['email', 'success', '-attempted_at']),
            models.Index(fields=['ip_address', '-attempted_at']),
        ]
    
    def __str__(self):
        status = "successful" if self.success else "failed"
        return f"{status.capitalize()} login attempt for {self.email} at {self.attempted_at}"


# Password History for preventing password reuse
class PasswordHistory(models.Model):
    """Store historical passwords to prevent reuse."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_history')
    password_hash = models.CharField(max_length=128)  # Stores hashed password
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Password History'
        verbose_name_plural = 'Password Histories'
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]
    
    def __str__(self):
        return f"Password history for {self.user.email} at {self.created_at}"
