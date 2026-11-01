from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from accounts.constants import (
    ASSIGNMENT_SCOPE_TYPES,
    LEVELS,
    MODULES,
    RoleCode,
    SCOPES,
)
from accounts.managers import UserManager
from base.models import TimeStampedUUIDModel


class Role(TimeStampedUUIDModel):
    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=128)
    is_system = models.BooleanField(default=True)

    class Meta:
        ordering = ("created_at",)

    def __str__(self):
        return self.name

    @property
    def is_super_admin(self):
        return self.code == RoleCode.SUPER_ADMIN


class RolePermission(TimeStampedUUIDModel):
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="permissions",
    )
    module = models.CharField(max_length=64, choices=[(module, module) for module in MODULES])
    level = models.CharField(max_length=16, choices=[(level, level) for level in LEVELS])
    scope = models.CharField(max_length=16, choices=[(scope, scope) for scope in SCOPES])

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("role", "module"), name="unique_role_module"),
        ]
        ordering = ("role_id", "module")

    def __str__(self):
        return f"{self.role.code}:{self.module}={self.level}/{self.scope}"


class User(TimeStampedUUIDModel, AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255, blank=True)
    role = models.ForeignKey(
        Role,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="users",
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        ordering = ("email",)

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.lower()
        if self.role_id and self.role.is_super_admin:
            self.is_staff = True
            self.is_superuser = True
        elif self.role_id:
            self.is_staff = False
            self.is_superuser = False
        super().save(*args, **kwargs)


class UserAssignment(TimeStampedUUIDModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    scope_type = models.CharField(
        max_length=32,
        choices=[(item, item) for item in ASSIGNMENT_SCOPE_TYPES],
    )
    object_id = models.CharField(max_length=64)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("user", "scope_type", "object_id"),
                name="unique_user_assignment",
            ),
        ]
        ordering = ("scope_type", "object_id")

    def __str__(self):
        return f"{self.user.email}:{self.scope_type}:{self.object_id}"
