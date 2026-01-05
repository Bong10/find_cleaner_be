from django.core.management.base import BaseCommand
from users.models import Cleaner
from services.models import ServiceZone

class Command(BaseCommand):
    help = 'Automatically assigns cleaners to service zones based on their service areas'

    def handle(self, *args, **options):
        self.stdout.write('Starting assignment of cleaners to zones...')
        
        cleaners = Cleaner.objects.all()
        active_zones = ServiceZone.objects.filter(is_active=True)
        
        updated_count = 0
        
        for cleaner in cleaners:
            service_areas = cleaner.service_areas
            if not service_areas:
                self.stdout.write(f"Cleaner {cleaner.id}: No service areas found.")
                continue
            
            self.stdout.write(f"Cleaner {cleaner.id}: Checking {len(service_areas)} areas...")
                
            matched_zones = set()
            
            # Check existing zones to avoid unnecessary updates if possible, 
            # but we want to ensure they are correct, so we'll recalculate.
            
            for area in service_areas:
                # Handle both dict (new format) and potentially string (old format if any left)
                if isinstance(area, dict):
                    # Handle both latitude/longitude and lat/lng keys
                    lat = area.get('latitude') or area.get('lat')
                    lng = area.get('longitude') or area.get('lng')
                    name = area.get('name', 'Unknown')
                    
                    if lat is not None and lng is not None:
                        self.stdout.write(f"  - Checking area '{name}' ({lat}, {lng})")
                        for zone in active_zones:
                            # 1. Geometric match
                            if zone.contains_point(lat, lng):
                                matched_zones.add(zone)
                                self.stdout.write(f"    -> Matches zone (geometric): {zone.name}")
                                continue
                            
                            # 2. Text-based match (Fallback)
                            address = area.get('address', {})
                            if isinstance(address, dict):
                                address_components = [
                                    address.get('city'),
                                    address.get('county'),
                                    address.get('state'),
                                    address.get('state_district'),
                                    address.get('region')
                                ]
                                if zone.name in [comp for comp in address_components if comp]:
                                    matched_zones.add(zone)
                                    self.stdout.write(f"    -> Matches zone (text): {zone.name}")
                    else:
                        self.stdout.write(f"  - Area '{name}' missing coordinates")
                else:
                    self.stdout.write(f"  - Invalid area format: {area}")
            
            if matched_zones:
                # Get current zone IDs
                current_zone_ids = set(cleaner.service_zones.values_list('id', flat=True))
                new_zone_ids = set(z.id for z in matched_zones)
                
                # Only update if there's a change
                if current_zone_ids != new_zone_ids:
                    cleaner.service_zones.set(matched_zones)
                    updated_count += 1
                    self.stdout.write(f'Updated cleaner {cleaner.id} ({cleaner.user.email if cleaner.user else "No User"}): Added to {[z.name for z in matched_zones]}')
        
        self.stdout.write(self.style.SUCCESS(f'Successfully updated {updated_count} cleaners.'))
