import os
import uuid

from django.conf import settings
from django.db import models


# Create your models here.
def user_directory_path(instance, filename):
    ext = os.path.splitext(filename)[1]
    safe_name = f"file{instance.file_uuid}{ext}"
    return f"files/user_{instance.owner.id}/{safe_name}"


class Folder(models.Model):
    folder_uuid = models.UUIDField(
        primary_key=True, default=uuid.uuid4, unique=True, editable=False
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="folders"
    )
    folder_name = models.CharField(max_length=255)
    parent_folder = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="sub_folders",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    shared_with = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="shared_folders"
    )

    def __str__(self):
        return self.folder_name


class File(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="files"
    )
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()
    file_uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    file = models.FileField(upload_to=user_directory_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    folder = models.ForeignKey(
        Folder, on_delete=models.CASCADE, null=True, blank=True, related_name="files"
    )
    shared_with = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="shared_files"
    )

    def __str__(self):
        return self.file_name
