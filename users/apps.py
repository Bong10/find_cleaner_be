from django.apps import AppConfig
from django.db.models.signals import post_migrate

class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'

    def ready(self):
        from django.db.utils import OperationalError
        from django.contrib.auth import get_user_model
        from .models import Role  # Make sure Role model is in users.models
        from django.conf import settings

        def create_default_roles(sender, **kwargs):
            try:
                Role.objects.get_or_create(name='Admin')
                Role.objects.get_or_create(name='Employer')
                Role.objects.get_or_create(name='Cleaner')
                print("Default roles ensured.")
            except OperationalError:
                print("⚠️ Database not ready yet. Skipping role creation.")

        def create_default_admin(sender, **kwargs):
            User = get_user_model()
            admin_email = 'digitalweb079@gmail.com'
            admin_password = 'Admin123!'  # Use environment variables in production!

            if not User.objects.filter(email=admin_email).exists():
                User.objects.create_superuser(
                    email=admin_email,
                    password=admin_password,
                    is_active=True
                )
                print("Default admin user created.")

        post_migrate.connect(create_default_roles, sender=self)
        post_migrate.connect(create_default_admin, sender=self)
