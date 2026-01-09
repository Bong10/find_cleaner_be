from django.core.management.base import BaseCommand
from services.models import Category, Service


class Command(BaseCommand):
    help = 'Seed the database with cleaning service categories and services'

    def handle(self, *args, **options):
        self.stdout.write('Seeding categories and services...')

        # Define categories
        categories_data = [
            {'name': 'Residential Cleaning', 'description': 'Home and apartment cleaning services'},
            {'name': 'Commercial Cleaning', 'description': 'Office and business cleaning services'},
            {'name': 'Specialized Cleaning', 'description': 'Deep cleaning and specialty services'},
            {'name': 'Move In/Out Cleaning', 'description': 'End of tenancy and move-related cleaning'},
            {'name': 'Outdoor Cleaning', 'description': 'External and outdoor area cleaning'},
        ]

        # Create categories
        categories = {}
        for cat_data in categories_data:
            category, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults={'description': cat_data['description']}
            )
            categories[cat_data['name']] = category
            status = 'Created' if created else 'Already exists'
            self.stdout.write(f"  {status}: Category '{category.name}'")

        # Define services with their categories
        services_data = [
            # Residential Cleaning
            {'name': 'Regular House Cleaning', 'category': 'Residential Cleaning', 'description': 'Standard weekly or bi-weekly home cleaning', 'min_hourly_rate': 15.00, 'min_hours_required': 2},
            {'name': 'Deep House Cleaning', 'category': 'Residential Cleaning', 'description': 'Thorough deep cleaning of entire home', 'min_hourly_rate': 20.00, 'min_hours_required': 4},
            {'name': 'Apartment Cleaning', 'category': 'Residential Cleaning', 'description': 'Cleaning services for flats and apartments', 'min_hourly_rate': 15.00, 'min_hours_required': 2},
            {'name': 'Kitchen Deep Clean', 'category': 'Residential Cleaning', 'description': 'Intensive kitchen cleaning including appliances', 'min_hourly_rate': 18.00, 'min_hours_required': 2},
            {'name': 'Bathroom Deep Clean', 'category': 'Residential Cleaning', 'description': 'Thorough bathroom sanitization and cleaning', 'min_hourly_rate': 18.00, 'min_hours_required': 1},
            {'name': 'Bedroom Cleaning', 'category': 'Residential Cleaning', 'description': 'Bedroom tidying, dusting, and vacuuming', 'min_hourly_rate': 15.00, 'min_hours_required': 1},

            # Commercial Cleaning
            {'name': 'Office Cleaning', 'category': 'Commercial Cleaning', 'description': 'Regular office space cleaning and maintenance', 'min_hourly_rate': 18.00, 'min_hours_required': 2},
            {'name': 'Retail Store Cleaning', 'category': 'Commercial Cleaning', 'description': 'Shop and retail space cleaning', 'min_hourly_rate': 18.00, 'min_hours_required': 2},
            {'name': 'Restaurant Cleaning', 'category': 'Commercial Cleaning', 'description': 'Food service establishment deep cleaning', 'min_hourly_rate': 22.00, 'min_hours_required': 3},
            {'name': 'Warehouse Cleaning', 'category': 'Commercial Cleaning', 'description': 'Industrial and warehouse space cleaning', 'min_hourly_rate': 20.00, 'min_hours_required': 4},
            {'name': 'Medical Facility Cleaning', 'category': 'Commercial Cleaning', 'description': 'Healthcare facility sanitization', 'min_hourly_rate': 25.00, 'min_hours_required': 3},

            # Specialized Cleaning
            {'name': 'Carpet Cleaning', 'category': 'Specialized Cleaning', 'description': 'Professional carpet shampooing and stain removal', 'min_hourly_rate': 25.00, 'min_hours_required': 2},
            {'name': 'Upholstery Cleaning', 'category': 'Specialized Cleaning', 'description': 'Sofa, chair, and furniture fabric cleaning', 'min_hourly_rate': 25.00, 'min_hours_required': 2},
            {'name': 'Window Cleaning', 'category': 'Specialized Cleaning', 'description': 'Interior and exterior window washing', 'min_hourly_rate': 20.00, 'min_hours_required': 2},
            {'name': 'Oven Cleaning', 'category': 'Specialized Cleaning', 'description': 'Deep oven and range cleaning', 'min_hourly_rate': 50.00, 'min_hours_required': 1},
            {'name': 'Fridge Cleaning', 'category': 'Specialized Cleaning', 'description': 'Refrigerator deep clean and sanitization', 'min_hourly_rate': 30.00, 'min_hours_required': 1},
            {'name': 'Mattress Cleaning', 'category': 'Specialized Cleaning', 'description': 'Mattress deep cleaning and sanitization', 'min_hourly_rate': 40.00, 'min_hours_required': 1},
            {'name': 'After Builders Cleaning', 'category': 'Specialized Cleaning', 'description': 'Post-construction cleanup and dust removal', 'min_hourly_rate': 22.00, 'min_hours_required': 4},
            {'name': 'Hoarding Cleanup', 'category': 'Specialized Cleaning', 'description': 'Sensitive hoarding situation cleaning', 'min_hourly_rate': 25.00, 'min_hours_required': 6},

            # Move In/Out Cleaning
            {'name': 'End of Tenancy Cleaning', 'category': 'Move In/Out Cleaning', 'description': 'Complete property clean for moving out', 'min_hourly_rate': 20.00, 'min_hours_required': 4},
            {'name': 'Move-In Cleaning', 'category': 'Move In/Out Cleaning', 'description': 'Pre-move deep clean of new property', 'min_hourly_rate': 20.00, 'min_hours_required': 3},
            {'name': 'Pre-Sale Property Cleaning', 'category': 'Move In/Out Cleaning', 'description': 'Property cleaning for viewings and sales', 'min_hourly_rate': 20.00, 'min_hours_required': 3},

            # Outdoor Cleaning
            {'name': 'Patio Cleaning', 'category': 'Outdoor Cleaning', 'description': 'Patio and decking pressure washing', 'min_hourly_rate': 22.00, 'min_hours_required': 2},
            {'name': 'Driveway Cleaning', 'category': 'Outdoor Cleaning', 'description': 'Driveway pressure washing and cleaning', 'min_hourly_rate': 22.00, 'min_hours_required': 2},
            {'name': 'Gutter Cleaning', 'category': 'Outdoor Cleaning', 'description': 'Gutter clearing and external pipe cleaning', 'min_hourly_rate': 25.00, 'min_hours_required': 2},
            {'name': 'Garden Furniture Cleaning', 'category': 'Outdoor Cleaning', 'description': 'Outdoor furniture cleaning and restoration', 'min_hourly_rate': 20.00, 'min_hours_required': 1},
        ]

        # Create services
        created_count = 0
        existing_count = 0
        for svc_data in services_data:
            category = categories.get(svc_data['category'])
            service, created = Service.objects.get_or_create(
                name=svc_data['name'],
                defaults={
                    'description': svc_data['description'],
                    'category': category,
                    'min_hourly_rate': svc_data['min_hourly_rate'],
                    'min_hours_required': svc_data['min_hours_required'],
                }
            )
            if created:
                created_count += 1
            else:
                existing_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'\nDone! Created {created_count} new services, {existing_count} already existed.'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'Total: {len(categories_data)} categories, {len(services_data)} services'
        ))
