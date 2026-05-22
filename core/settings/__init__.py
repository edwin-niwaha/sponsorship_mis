"""Helpers for choosing the active Django settings module."""


def get_settings_module(django_env=None, command=None):
    if django_env == "production":
        return "core.settings.production"
    if django_env == "development" or command == "runserver":
        return "core.settings.development"
    return "core.settings.production"
