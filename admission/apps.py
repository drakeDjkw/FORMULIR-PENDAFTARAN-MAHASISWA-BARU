from django.apps import AppConfig
from django.db.backends.signals import connection_created
from django.utils.translation import gettext_lazy as _


def sqlite_unicode_lower(sender, connection, **kwargs):
    # SQLite's built-in LOWER only lowercases ASCII letters.
    # Replace it with Python's str.lower() so case-insensitive search works for every alphabet.
    if connection.vendor == "sqlite":
        connection.connection.create_function(
            "LOWER", 1, lambda s: s.lower() if isinstance(s, str) else s, deterministic=True
        )


class AdmissionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "admission"
    verbose_name = _("New student admission")

    def ready(self):
        connection_created.connect(sqlite_unicode_lower)
