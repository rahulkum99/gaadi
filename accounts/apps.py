from django.apps import AppConfig
from django.db.models.signals import post_migrate


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"

    def ready(self):
        post_migrate.connect(_seed_roles, sender=self)


def _seed_roles(sender, **kwargs):
    from accounts.services import seed_roles_and_permissions

    seed_roles_and_permissions()
