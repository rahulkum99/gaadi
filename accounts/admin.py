from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from accounts.models import Role, RolePermission, User, UserAssignment


class AccountsUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("email", "full_name", "role")


class AccountsUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"


class UserAssignmentInline(admin.TabularInline):
    model = UserAssignment
    extra = 0


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    form = AccountsUserChangeForm
    add_form = AccountsUserCreationForm
    ordering = ("email",)
    list_display = ("email", "full_name", "role", "is_active", "is_staff")
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("email", "full_name")
    inlines = (UserAssignmentInline,)
    fieldsets = (
        (None, {"fields": ("email", "password", "full_name", "role")}),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "full_name", "role", "password1", "password2"),
            },
        ),
    )
    filter_horizontal = ("groups", "user_permissions")


class RolePermissionInline(admin.TabularInline):
    model = RolePermission
    extra = 0


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_system")
    search_fields = ("name", "code")
    inlines = (RolePermissionInline,)


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = ("role", "module", "level", "scope")
    list_filter = ("role", "module", "level", "scope")


@admin.register(UserAssignment)
class UserAssignmentAdmin(admin.ModelAdmin):
    list_display = ("user", "scope_type", "object_id")
    list_filter = ("scope_type",)
    search_fields = ("user__email", "object_id")
