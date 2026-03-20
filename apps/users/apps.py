from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    # This name must match what's in INSTALLED_APPS in settings.py
    name = "apps.users"
