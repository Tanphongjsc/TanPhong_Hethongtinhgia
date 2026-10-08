#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    # Test commands always start from isolated localhost settings; no Supabase DDL.
    command = sys.argv[1] if len(sys.argv) > 1 else ''
    if command == 'test':
        explicit = [arg.split('=', 1)[1] for arg in sys.argv if arg.startswith('--settings=')]
        if '--settings' in sys.argv:
            index = sys.argv.index('--settings')
            explicit.append(sys.argv[index + 1] if index + 1 < len(sys.argv) else '')
        target = explicit[-1] if explicit else os.environ.get('DJANGO_SETTINGS_MODULE', 'config.test_settings')
        if target != 'config.test_settings' or os.environ.get('APP_ENV') == 'production':
            sys.exit('Tests chỉ chạy với config.test_settings trên PostgreSQL localhost; không chạy production.')
    if command in ('flush', 'migrate', 'makemigrations') and (os.environ.get('APP_ENV') == 'production' or os.environ.get('DJANGO_SETTINGS_MODULE') == 'config.production' or any('config.production' in arg for arg in sys.argv[2:])):
        sys.exit('Production không chạy flush/migrate/makemigrations. Business schema được quản lý database-first.')
    default_settings = 'config.test_settings' if command == 'test' else ('config.production' if os.environ.get('APP_ENV') in ('production', 'staging') else 'config.settings')
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', default_settings)
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
