#!/usr/bin/env python
"""
manage.py — Django's command-line utility.

Use this to run the dev server, create migrations, etc.
Examples:
  python manage.py runserver
  python manage.py makemigrations
  python manage.py migrate
  python manage.py createsuperuser
"""

import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "quiz_project.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Make sure it's installed and your "
            "virtualenv is activated."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
