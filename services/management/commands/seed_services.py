from django.core.management.base import BaseCommand
from services.models import Service, Category


class Command(BaseCommand):
    help = 'Seeds the database with standard cleaning services and categories'

    def handle(self, *args, **options):
        self.stdout.write('Seeding cleaning services...')

        # Define categories
        categories_data = [
            {'name': 'Residential Cleaning', 'description': 'Home and apartment cleaning services'},
            {'name': 'Commercial Cleaning', 'description': 'Office and business cleaning services'},
            {'name': 'Specialized Cleaning', 'description': 'Specialized and deep cleaning services'},
            {'name': 'Move-Related Cleaning', 'description': 'Moving in/out cleaning services'},
            {'name': 'Outdoor Cleaning', 'description': 'Exterior and outdoor cleaning services'},
        ]

        categories = {}
        for cat_data in categories_data:
            cat, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults={'description': cat_data['description'], 'active': True}
            )
            categories[cat_data['name']] = cat
            status = 'Created' if created else 'Found'
            self.stdout.write(f"  {status} category: {cat.name}")

        # Define services with their categories
        services_data = [
            # Residential Cleaning
            {
                'name': 'Regular Cleaning',
                'description': 'Standard house cleaning including dusting, vacuuming, mopping, and general tidying of all rooms.',
                'category': 'Residential Cleaning',
                'min_hourly_rate': 12.00,
                'min_hours_required': 2,
            },
            {
                'name': 'Deep Cleaning',
                'description': 'Thorough cleaning including behind appliances, inside cabinets, detailed scrubbing, and hard-to-reach areas.',
                'category': 'Specialized Cleaning',
                'min_hourly_rate': 15.00,
                'min_hours_required': 3,
            },
            {
                'name': 'Kitchen Cleaning',
                'description': 'Focused kitchen cleaning including appliances, countertops, cabinets, sink, and floor.',
                'category': 'Residential Cleaning',
                'min_hourly_rate': 12.00,
                'min_hours_required': 1,
            },
            {
                'name': 'Bathroom Cleaning',
                'description': 'Detailed bathroom cleaning including toilet, shower/bath, sink, mirrors, and tiles.',
                'category': 'Residential Cleaning',
                'min_hourly_rate': 12.00,
                'min_hours_required': 1,
            },
            {
                'name': 'Bedroom Cleaning',
                'description': 'Bedroom cleaning including bed making, dusting, vacuuming, and organizing.',
                'category': 'Residential Cleaning',
                'min_hourly_rate': 12.00,
                'min_hours_required': 1,
            },
            {
                'name': 'Living Room Cleaning',
                'description': 'Living area cleaning including dusting furniture, vacuuming, and tidying.',
                'category': 'Residential Cleaning',
                'min_hourly_rate': 12.00,
                'min_hours_required': 1,
            },
            # Specialized Cleaning
            {
                'name': 'Oven Cleaning',
                'description': 'Professional oven and cooktop deep cleaning, removing grease and burnt-on residue.',
                'category': 'Specialized Cleaning',
                'min_hourly_rate': 15.00,
                'min_hours_required': 1,
            },
            {
                'name': 'Carpet Cleaning',
                'description': 'Professional carpet cleaning including stain removal and deep extraction.',
                'category': 'Specialized Cleaning',
                'min_hourly_rate': 15.00,
                'min_hours_required': 2,
            },
            {
                'name': 'Upholstery Cleaning',
                'description': 'Cleaning of sofas, chairs, and other upholstered furniture.',
                'category': 'Specialized Cleaning',
                'min_hourly_rate': 15.00,
                'min_hours_required': 2,
            },
            {
                'name': 'Window Cleaning',
                'description': 'Interior and exterior window cleaning including frames and sills.',
                'category': 'Specialized Cleaning',
                'min_hourly_rate': 14.00,
                'min_hours_required': 2,
            },
            {
                'name': 'Fridge Cleaning',
                'description': 'Deep cleaning of refrigerator interior, shelves, and drawers.',
                'category': 'Specialized Cleaning',
                'min_hourly_rate': 12.00,
                'min_hours_required': 1,
            },
            {
                'name': 'Laundry & Ironing',
                'description': 'Washing, drying, folding, and ironing clothes and linens.',
                'category': 'Residential Cleaning',
                'min_hourly_rate': 12.00,
                'min_hours_required': 2,
            },
            # Move-Related
            {
                'name': 'End of Tenancy Cleaning',
                'description': 'Comprehensive cleaning for rental properties at the end of a tenancy, meeting landlord standards.',
                'category': 'Move-Related Cleaning',
                'min_hourly_rate': 15.00,
                'min_hours_required': 4,
            },
            {
                'name': 'Move-In Cleaning',
                'description': 'Thorough cleaning of a property before moving in, ensuring a fresh start.',
                'category': 'Move-Related Cleaning',
                'min_hourly_rate': 15.00,
                'min_hours_required': 3,
            },
            {
                'name': 'Move-Out Cleaning',
                'description': 'Complete cleaning after moving out furniture, including all rooms and fixtures.',
                'category': 'Move-Related Cleaning',
                'min_hourly_rate': 15.00,
                'min_hours_required': 3,
            },
            # Commercial
            {
                'name': 'Office Cleaning',
                'description': 'Professional office cleaning including desks, common areas, kitchens, and restrooms.',
                'category': 'Commercial Cleaning',
                'min_hourly_rate': 14.00,
                'min_hours_required': 2,
            },
            {
                'name': 'Commercial Kitchen Cleaning',
                'description': 'Industrial kitchen deep cleaning meeting health and safety standards.',
                'category': 'Commercial Cleaning',
                'min_hourly_rate': 18.00,
                'min_hours_required': 3,
            },
            {
                'name': 'Retail Store Cleaning',
                'description': 'Cleaning of retail spaces including floors, displays, and fitting rooms.',
                'category': 'Commercial Cleaning',
                'min_hourly_rate': 14.00,
                'min_hours_required': 2,
            },
            # Outdoor
            {
                'name': 'Patio & Decking Cleaning',
                'description': 'Pressure washing and cleaning of patios, decks, and outdoor furniture.',
                'category': 'Outdoor Cleaning',
                'min_hourly_rate': 15.00,
                'min_hours_required': 2,
            },
            {
                'name': 'Garage Cleaning',
                'description': 'Garage cleaning and organizing, including floor cleaning and decluttering.',
                'category': 'Outdoor Cleaning',
                'min_hourly_rate': 14.00,
                'min_hours_required': 2,
            },
            {
                'name': 'Driveway Cleaning',
                'description': 'Pressure washing and cleaning of driveways and paths.',
                'category': 'Outdoor Cleaning',
                'min_hourly_rate': 15.00,
                'min_hours_required': 2,
            },
            # Additional Specialized
            {
                'name': 'After Party Cleaning',
                'description': 'Post-event cleanup including rubbish removal, surface cleaning, and restoring order.',
                'category': 'Specialized Cleaning',
                'min_hourly_rate': 15.00,
                'min_hours_required': 3,
            },
            {
                'name': 'After Builders Cleaning',
                'description': 'Post-construction cleaning including dust removal, debris clearing, and surface polishing.',
                'category': 'Specialized Cleaning',
                'min_hourly_rate': 18.00,
                'min_hours_required': 4,
            },
            {
                'name': 'Spring Cleaning',
                'description': 'Seasonal deep clean covering all areas of the home with extra attention to detail.',
                'category': 'Specialized Cleaning',
                'min_hourly_rate': 15.00,
                'min_hours_required': 4,
            },
            {
                'name': 'One-Off Cleaning',
                'description': 'Single visit cleaning service for any purpose, customized to your needs.',
                'category': 'Residential Cleaning',
                'min_hourly_rate': 13.00,
                'min_hours_required': 2,
            },
            {
                'name': 'Airbnb/Holiday Let Cleaning',
                'description': 'Turnover cleaning between guests for short-term rental properties.',
                'category': 'Commercial Cleaning',
                'min_hourly_rate': 15.00,
                'min_hours_required': 2,
            },
            {
                'name': 'Student Accommodation Cleaning',
                'description': 'Cleaning services tailored for student housing and shared accommodations.',
                'category': 'Residential Cleaning',
                'min_hourly_rate': 12.00,
                'min_hours_required': 2,
            },
        ]

        created_count = 0
        updated_count = 0

        for svc_data in services_data:
            category = categories.get(svc_data.pop('category'))
            service, created = Service.objects.update_or_create(
                name=svc_data['name'],
                defaults={
                    'description': svc_data['description'],
                    'category': category,
                    'min_hourly_rate': svc_data['min_hourly_rate'],
                    'min_hours_required': svc_data['min_hours_required'],
                    'active': True,
                }
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"  Created: {service.name}"))
            else:
                updated_count += 1
                self.stdout.write(f"  Updated: {service.name}")

        self.stdout.write(self.style.SUCCESS(
            f"\nDone! Created {created_count} new services, updated {updated_count} existing."
        ))
        self.stdout.write(self.style.SUCCESS(
            f"Total services: {Service.objects.filter(active=True).count()}"
        ))
