from django.contrib.auth.models import User
from rest_framework import serializers

from .models import File

class FileSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(
            source="owner.username",
            read_only=True
        )
    file_name=serializers.CharField(required=False)

    class Meta:
        model = File
        fields = [
            "file_uuid",
            "file",
            "owner_username",
            "file_name",
            "file_type",
            "file_size",
            "uploaded_at",
        ]
        read_only_fields = [
            "file_type",
            "file_size",
            "uploaded_at",
        ]

    def validate_file_name(self,value):
        value=value.strip()
        if not value:
            raise serializers.ValidationError("File name cannot be empty")
        if len(value)>255:
            raise serializers.ValidationError("File name cannot be more than 255 characters")
        if "/" in value or "\\" in value:
            raise serializers.ValidationError("File name cannot contain '/' or '\\'")
        if value in [".",".."]:
            raise serializers.ValidationError("File name cannot be '.' or '..'")
        return value


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["username", "email", "password"]

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email"),
            password=validated_data["password"],
        )
        return user