from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from accounts.constants import (
    ASSIGNMENT_SCOPE_TYPES,
    LEVELS,
    MODULES,
    RoleCode,
    SCOPES,
)
from accounts.models import Role, RolePermission, UserAssignment
from accounts.services import effective_permissions

User = get_user_model()


def _uuid_exists(model, object_id):
    from django.core.exceptions import ValidationError as DjangoValidationError

    try:
        return model.objects.filter(pk=object_id).exists()
    except (DjangoValidationError, ValueError):
        return False


class RolePermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RolePermission
        fields = ("module", "level", "scope")

    def validate_module(self, value):
        if value not in MODULES:
            raise serializers.ValidationError("Unknown module.")
        return value

    def validate_level(self, value):
        if value not in LEVELS:
            raise serializers.ValidationError("Unknown permission level.")
        return value

    def validate_scope(self, value):
        if value not in SCOPES:
            raise serializers.ValidationError("Unknown permission scope.")
        return value


class RoleSerializer(serializers.ModelSerializer):
    permissions = RolePermissionSerializer(many=True, read_only=True)

    class Meta:
        model = Role
        fields = ("id", "code", "name", "is_system", "permissions", "created_at", "updated_at")
        read_only_fields = ("id", "code", "name", "is_system", "created_at", "updated_at")


class RoleUpdateSerializer(serializers.Serializer):
    permissions = RolePermissionSerializer(many=True)

    def validate(self, attrs):
        if self.instance and self.instance.code == RoleCode.SUPER_ADMIN:
            raise serializers.ValidationError(
                "Super Admin permissions cannot be changed."
            )
        modules = [item["module"] for item in attrs["permissions"]]
        if len(modules) != len(set(modules)):
            raise serializers.ValidationError("Duplicate modules are not allowed.")
        return attrs

    def update(self, instance, validated_data):
        for item in validated_data["permissions"]:
            RolePermission.objects.update_or_create(
                role=instance,
                module=item["module"],
                defaults={"level": item["level"], "scope": item["scope"]},
            )
        return instance


class UserAssignmentSerializer(serializers.ModelSerializer):
    constituency = serializers.SerializerMethodField()

    class Meta:
        model = UserAssignment
        fields = (
            "id",
            "scope_type",
            "object_id",
            "constituency",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "constituency", "created_at", "updated_at")

    def validate_scope_type(self, value):
        if value not in ASSIGNMENT_SCOPE_TYPES:
            raise serializers.ValidationError("Unknown assignment scope type.")
        return value

    def validate_object_id(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("object_id is required.")
        return value

    def validate(self, attrs):
        scope_type = attrs.get("scope_type")
        object_id = attrs.get("object_id")
        if scope_type == "constituency":
            from fleet.models import Constituency

            if not _uuid_exists(Constituency, object_id):
                raise serializers.ValidationError({"object_id": "Unknown constituency."})
        elif scope_type == "vehicle":
            from fleet.models import Vehicle

            if not _uuid_exists(Vehicle, object_id):
                raise serializers.ValidationError({"object_id": "Unknown vehicle."})
        return attrs

    def get_constituency(self, obj):
        if obj.scope_type != "constituency":
            return None
        from fleet.models import Constituency

        if not _uuid_exists(Constituency, obj.object_id):
            return None
        constituency = Constituency.objects.filter(pk=obj.object_id).first()
        if constituency is None:
            return None
        return {
            "id": str(constituency.id),
            "code": constituency.code,
            "number": constituency.number,
            "name": constituency.name,
            "district": constituency.district,
        }


class UserAssignmentReplaceSerializer(serializers.Serializer):
    assignments = UserAssignmentSerializer(many=True)

    def validate_assignments(self, value):
        seen = set()
        for item in value:
            key = (item["scope_type"], item["object_id"])
            if key in seen:
                raise serializers.ValidationError("Duplicate assignments are not allowed.")
            seen.add(key)
        return value


class UserSerializer(serializers.ModelSerializer):
    role = serializers.SlugRelatedField(slug_field="code", read_only=True)
    role_name = serializers.CharField(source="role.name", read_only=True, default=None)
    permissions = serializers.SerializerMethodField()
    assignments = UserAssignmentSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "full_name",
            "role",
            "role_name",
            "is_active",
            "date_joined",
            "created_at",
            "updated_at",
            "permissions",
            "assignments",
        )
        read_only_fields = fields

    def get_permissions(self, obj):
        return effective_permissions(obj)


class UserCreateSerializer(serializers.ModelSerializer):
    role = serializers.SlugRelatedField(slug_field="code", queryset=Role.objects.all())
    password = serializers.CharField(write_only=True, min_length=8)
    assignments = UserAssignmentSerializer(many=True, required=False)

    class Meta:
        model = User
        fields = ("id", "email", "password", "full_name", "role", "is_active", "assignments")
        read_only_fields = ("id",)

    def create(self, validated_data):
        assignments = validated_data.pop("assignments", [])
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)
        for assignment in assignments:
            UserAssignment.objects.create(user=user, **assignment)
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    role = serializers.SlugRelatedField(
        slug_field="code",
        queryset=Role.objects.all(),
        required=False,
    )
    password = serializers.CharField(write_only=True, min_length=8, required=False)

    class Meta:
        model = User
        fields = ("email", "password", "full_name", "role", "is_active")

    def validate(self, attrs):
        instance = self.instance
        next_active = attrs.get("is_active", instance.is_active)
        next_role = attrs.get("role", instance.role)
        becoming_non_admin = not (
            next_active and next_role and next_role.code == RoleCode.SUPER_ADMIN
        )
        if becoming_non_admin and instance.role and instance.role.code == RoleCode.SUPER_ADMIN:
            remaining = (
                User.objects.filter(
                    is_active=True,
                    role__code=RoleCode.SUPER_ADMIN,
                )
                .exclude(pk=instance.pk)
                .exists()
            )
            if not remaining:
                raise serializers.ValidationError(
                    "Cannot remove or deactivate the last Super Admin."
                )
        return attrs

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = User.USERNAME_FIELD

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["email"] = user.email
        token["role"] = user.role.code if user.role else None
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data
