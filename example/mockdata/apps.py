import sqlite3
import sys
import warnings

from django.apps import AppConfig
from django.conf import settings

# Held for the lifetime of the process.
_keepalive_conn = None

# Management commands that don't need (and shouldn't trigger) DB setup/seeding.
_SKIP_FOR_COMMANDS = {"makemigrations", "migrate", "collectstatic"}


class MockdataConfig(AppConfig):
    name = "mockdata"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        management_command = sys.argv[1] if len(sys.argv) > 1 else ""
        if management_command in _SKIP_FOR_COMMANDS:
            return

        global _keepalive_conn
        if _keepalive_conn is not None:
            return  # already initialized

        self._keep_shared_memory_db_alive()
        self._create_schema_and_seed()

    def _keep_shared_memory_db_alive(self):
        """Keep one database connection for the lifetime of a process."""
        global _keepalive_conn
        db_name = settings.DATABASES["default"]["NAME"]
        _keepalive_conn = sqlite3.connect(db_name, uri=True)

    def _create_schema_and_seed(self):
        from django.core.management import call_command

        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore", message="Accessing the database during app initialization"
            )
            call_command("migrate", run_syncdb=True, verbosity=0)

            from .seed import populate_mock_data

            populate_mock_data()
