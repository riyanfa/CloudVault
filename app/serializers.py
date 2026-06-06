from django.contrib.auth.models import User
from django.contrib.auth.password_validation import (
    validate_password as validate_django_password,
)
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import File, Folder


class FolderSerializer(serializers.ModelSerializer):
    is_owner = serializers.SerializerMethodField()

    # pyrefly: ignore [bad-override]
    class Meta:
        model = Folder
        fields = ["folder_uuid", "folder_name", "parent_folder", "is_owner"]
        read_only_fields = ["folder_uuid", "is_owner"]

    @extend_schema_field(serializers.BooleanField)
    def get_is_owner(self, obj):
        request = self.context.get("request")

        if not request:
            return False
        return obj.owner == request.user

    def validate_folder_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError("Folder name cannot be empty.")

        if "/" in value or "\\" in value:
            raise serializers.ValidationError("Folder name cannot contain '/' or '\\'.")

        if value in [".", ".."]:
            raise serializers.ValidationError("Folder name cannot be '.' or '..'.")

        return value

    def validate(self, attrs):
        request = self.context.get("request")

        if not request:
            raise serializers.ValidationError("Request context is required.")

        parent_folder = attrs.get("parent_folder")
        folder_name = attrs.get("folder_name")

        if self.instance:
            parent_folder = (
                parent_folder
                if "parent_folder" in attrs
                else self.instance.parent_folder
            )

            folder_name = (
                folder_name if "folder_name" in attrs else self.instance.folder_name
            )

        if parent_folder and parent_folder.owner != request.user:
            raise serializers.ValidationError(
                {"parent_folder": "You cannot use this parent folder."}
            )

        if self.instance and parent_folder == self.instance:
            raise serializers.ValidationError(
                {"parent_folder": "A folder cannot be its own parent."}
            )

        if self.instance and parent_folder:
            current_parent = parent_folder

            while current_parent:
                if current_parent == self.instance:
                    raise serializers.ValidationError(
                        {
                            "parent_folder": "A folder cannot be moved inside its own subfolder."
                        }
                    )

                current_parent = current_parent.parent_folder

        if folder_name:
            same_name_folder = Folder.objects.filter(
                owner=request.user,
                parent_folder=parent_folder,
                folder_name=folder_name,
            )
            if self.instance:
                same_name_folder = same_name_folder.exclude(pk=self.instance.pk)
            if same_name_folder.exists():
                raise serializers.ValidationError(
                    {
                        "folder_name": "You already have a folder with this name in this location."
                    }
                )
        return attrs


class FileSerializer(serializers.ModelSerializer):
    is_owner = serializers.SerializerMethodField()
    owner_username = serializers.CharField(source="owner.username", read_only=True)
    file_name = serializers.CharField(required=False)

    # pyrefly: ignore [bad-override]
    class Meta:
        model = File
        fields = [
            "file_uuid",
            "file",
            "owner_username",
            "file_name",
            "file_type",
            "file_size",
            "folder",
            "uploaded_at",
            "is_owner",
        ]
        read_only_fields = [
            "file_uuid",
            "file_type",
            "file_size",
            "uploaded_at",
            "is_owner",
        ]

    def validate_file_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("File name cannot be empty")
        if len(value) > 255:
            raise serializers.ValidationError(
                "File name cannot be more than 255 characters"
            )
        if "/" in value or "\\" in value:
            raise serializers.ValidationError("File name cannot contain '/' or '\\'")
        if value in [".", ".."]:
            raise serializers.ValidationError("File name cannot be '.' or '..'")
        return value

    @extend_schema_field(serializers.BooleanField)
    def get_is_owner(self, obj):
        request = self.context.get("request")

        if not request:
            return False
        return obj.owner == request.user

    def validate_folder(self, folder):
        request = self.context.get("request")
        if not request:
            raise serializers.ValidationError("Request context is required.")

        if folder and folder.owner != request.user:
            raise serializers.ValidationError("You cannot use this folder.")

        return folder


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    # pyrefly: ignore [bad-override]
    class Meta:
        model = User
        fields = ["username", "email", "password"]

    def validate(self, attrs):
        user = User(username=attrs["username"], email=attrs.get("email"))
        validate_django_password(attrs["password"], user=user)
        return attrs

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email"),
            password=validated_data["password"],
        )
        return user


class TokenPairSerializer(serializers.Serializer):
    refresh = serializers.CharField()
    access = serializers.CharField()


class RegisterResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    email = serializers.EmailField(allow_blank=True, allow_null=True)
    message = serializers.CharField()
    tokens = TokenPairSerializer()


class WhoamiSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    username = serializers.CharField()
