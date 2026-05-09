import os

from django.contrib.auth.models import User
from django.db import models
import uuid

from django.conf import settings

# Create your models here.

def user_directory_path(instance, filename):
    ext = os.path.splitext(filename)[1]
    safe_name = f"file{uuid.uuid4().hex}{ext}"
    return f"files/user_{instance.owner.id}/{safe_name}"
class File(models.Model):
    owner=models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,related_name="files")
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()
    file_uuid = models.UUIDField(null=True,editable=False,unique=True)
    file = models.FileField(upload_to=user_directory_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    Folder=models.ForeignKey('self',on_delete=models.CASCADE,null=True,blank=True,related_name='folders')
    shared_with = models.ManyToManyField(User, related_name="shared_files")
    def __str__(self):
        return self.file_name