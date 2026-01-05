from django.db import models
from django.core.validators import MinValueValidator
import math


class ServiceZone(models.Model):
    """
    Geographic service zones defined by admin.
    Cleaners can only offer services in zones they're eligible for based on their location.
    """
    name = models.CharField(max_length=100, unique=True, help_text="e.g., 'Manchester', 'Cambridgeshire'")
    description = models.TextField(blank=True, help_text="Additional details about this service zone")
    
    # Geographic data
    center_latitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6,
        help_text="Center point latitude (for display purposes)"
    )
    center_longitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6,
        help_text="Center point longitude (for display purposes)"
    )
    
    # Boundary polygon data from OpenStreetMap
    boundary_data = models.JSONField(
        null=True,
        blank=True,
        help_text="GeoJSON polygon data defining the actual boundary of this area"
    )
    
    # OSM reference for updates
    osm_type = models.CharField(
        max_length=20,
        blank=True,
        help_text="OpenStreetMap type (relation, way, node)"
    )
    osm_id = models.CharField(
        max_length=50,
        blank=True,
        help_text="OpenStreetMap ID for this location"
    )
    
    # Fallback radius for locations without boundary data
    radius_km = models.DecimalField(
        max_digits=6, 
        decimal_places=2,
        validators=[MinValueValidator(0.1)],
        default=15.0,
        help_text="Fallback radius if boundary data unavailable"
    )
    
    # Hierarchy
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='children',
        help_text="Parent zone (e.g., England for Cambridgeshire). Parent zones automatically include all cleaners from child zones."
    )
    
    # Management
    is_active = models.BooleanField(default=True, help_text="Only active zones are available for selection")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Service Zone'
        verbose_name_plural = 'Service Zones'
    
    def __str__(self):
        return self.name
    
    def contains_point(self, latitude, longitude):
        """
        Check if a given lat/lng point is within this zone.
        Uses actual boundary polygon if available, otherwise falls back to radius.
        """
        # Try boundary-based check first (most accurate)
        if self.boundary_data and isinstance(self.boundary_data, dict):
            try:
                from shapely.geometry import Point, shape
                point = Point(float(longitude), float(latitude))
                polygon = shape(self.boundary_data)
                return polygon.contains(point)
            except Exception:
                pass  # Fall back to radius if shapely not available or data invalid
        
        # Fallback: radius-based check using Haversine formula
        R = 6371  # Earth's radius in kilometers
        
        lat1_rad = math.radians(float(self.center_latitude))
        lat2_rad = math.radians(float(latitude))
        delta_lat = math.radians(float(latitude) - float(self.center_latitude))
        delta_lng = math.radians(float(longitude) - float(self.center_longitude))
        
        a = math.sin(delta_lat / 2) ** 2 + \
            math.cos(lat1_rad) * math.cos(lat2_rad) * \
            math.sin(delta_lng / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        distance = R * c
        return distance <= float(self.radius_km)
    
    def get_all_cleaners(self):
        """
        Get all cleaners in this zone AND all child zones.
        This enables hierarchy: England zone automatically includes Cambridgeshire cleaners.
        """
        from users.models import Cleaner
        
        # Get cleaners directly assigned to this zone
        cleaner_ids = set(self.cleaners.values_list('id', flat=True))
        
        # Recursively get cleaners from all descendant zones
        for child_zone in self.children.filter(is_active=True):
            cleaner_ids.update(child_zone.get_all_cleaners().values_list('id', flat=True))
        
        return Cleaner.objects.filter(id__in=cleaner_ids)
    
    def get_child_zones(self):
        """
        Get all descendant zones (children, grandchildren, etc.).
        """
        descendants = []
        for child in self.children.filter(is_active=True):
            descendants.append(child)
            descendants.extend(child.get_child_zones())
        return descendants
    
    def is_contained_by(self, other_zone):
        """
        Check if this zone's boundary is contained within another zone's boundary.
        Used for auto-detecting parent-child relationships.
        """
        if not self.boundary_data or not other_zone.boundary_data:
            return False
        
        try:
            from shapely.geometry import shape
            this_polygon = shape(self.boundary_data)
            other_polygon = shape(other_zone.boundary_data)
            return other_polygon.contains(this_polygon)
        except Exception:
            return False
    
    def suggest_parent_zone(self):
        """
        Auto-detect potential parent zone by checking if this zone is contained
        within any existing zone's boundary.
        Returns the smallest containing zone (most specific parent).
        """
        if not self.boundary_data:
            return None
        
        potential_parents = []
        for zone in ServiceZone.objects.filter(is_active=True).exclude(id=self.id):
            if self.is_contained_by(zone):
                potential_parents.append(zone)
        
        if not potential_parents:
            return None
        
        # Return the smallest containing zone (sort by area)
        try:
            from shapely.geometry import shape
            potential_parents.sort(key=lambda z: shape(z.boundary_data).area)
            return potential_parents[0]  # Smallest = most specific
        except Exception:
            return potential_parents[0] if potential_parents else None


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Service(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='services')
    min_hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    min_hours_required = models.PositiveSmallIntegerField(default=1)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} (≥{self.min_hours_required}h @ ≥{self.min_hourly_rate}/h)"


class EligibilityApplication(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('reviewed', 'Reviewed'),
        ('contacted', 'Contacted'),
        ('rejected', 'Rejected'),
    )

    full_name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    postcode = models.CharField(max_length=20)
    contact_method = models.CharField(max_length=20, default='email')
    eligibility_criteria = models.JSONField(default=list)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Application from {self.full_name} ({self.created_at.strftime('%Y-%m-%d')})"

