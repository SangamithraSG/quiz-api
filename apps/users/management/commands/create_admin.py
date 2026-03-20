"""
create_admin.py — Custom management command.

Usage:
  python manage.py create_admin

Creates a superuser with admin role in one step.
Useful for quick setup during development or deployment.
"""

from django.core.management.base import BaseCommand
from apps.users.models import User


class Command(BaseCommand):
    # This text shows when you run: python manage.py help create_admin
    help = "Creates an admin user quickly for development/testing."

    def handle(self, *args, **options):
        username = "admin"
        password = "Admin123!"
        email = "admin@example.com"

        # Don't create a duplicate if it already exists
        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(f"User '{username}' already exists. Skipping.")
            )
            return

        # create_superuser sets is_staff=True and is_superuser=True automatically
        user = User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
        )
        # Set our custom role field to "admin"
        user.role = User.ROLE_ADMIN
        user.save()

        self.stdout.write(self.style.SUCCESS(
            f"\n✓ Admin user created!\n"
            f"  Username : {username}\n"
            f"  Password : {password}\n"
            f"  Role     : admin\n"
            f"\nYou can now log in at /admin/ or POST to /api/auth/login/\n"
            f"IMPORTANT: Change the password in production!\n"
        ))
