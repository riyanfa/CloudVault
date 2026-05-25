from django.contrib.auth.models import User
from django.db.models import Q
from django.http import FileResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from .models import File, Folder
from .serializers import FileSerializer, FolderSerializer


class FolderViewSet(ModelViewSet):
    lookup_field = "folder_uuid"
    serializer_class = FolderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Folder.objects.filter(
            Q(owner=self.request.user) |
            Q(shared_with=self.request.user)
        ).distinct().order_by("-created_at")

    def perform_update(self, serializer):
        folder = self.get_object()

        if folder.owner != self.request.user:
            raise ValidationError({"detail": "Only the owner can update this folder."})

        serializer.save()

    def perform_destroy(self, instance):
        if instance.owner != self.request.user:
            raise ValidationError({"detail": "Only the owner can delete this folder."})

        instance.delete()

    def perform_create(self, serializer):
        folder_name = self.request.data.get("folder_name")
        parent_folder_uuid = self.request.data.get('parent_folder_uuid')

        parent_folder = None

        if parent_folder_uuid:
            try:
                parent_folder = Folder.objects.get(
                    folder_uuid=parent_folder_uuid,
                    owner=self.request.user
                )
            except Folder.DoesNotExist:
                raise ValidationError({
                    "parent_folder_uuid": "Parent folder does not exist."
                })

        duplicate_exists = Folder.objects.filter(
            owner=self.request.user,
            parent_folder=parent_folder,
            folder_name=folder_name
        ).exists()

        if duplicate_exists:
            raise ValidationError({
                "folder_name": "A folder with this name already exists in this location."
            })

        serializer.save(
            owner=self.request.user,
            parent_folder=parent_folder
        )

    @action(detail=True, methods=['get'], url_path='files')
    def files(self, request, folder_uuid=None):
        files = File.objects.filter(owner=request.user, folder__folder_uuid=folder_uuid)
        serializer = FileSerializer(files, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='share', parser_classes=[JSONParser])
    def share(self, request, folder_uuid=None):
        folder_obj = self.get_object()

        if folder_obj.owner != request.user:
            raise ValidationError({"detail": "Only the owner can share this Folder."})

        username = request.data.get("username")

        target_user = get_object_or_404(User, username=username)

        if folder_obj.shared_with.filter(id=target_user.id).exists():
            raise ValidationError({"detail": "User is already shared with this Folder."})

        if target_user == request.user:
            raise ValidationError({"user_id": "You cannot share a Folder with yourself."})
        folder_obj.shared_with.add(target_user)

        return (Response(
            {"detail": f"Folder shared with {target_user.username}."},
            status=status.HTTP_200_OK
        ))

    @action(detail=True, methods=['post'], url_path='remove_share', parser_classes=[JSONParser])
    def remove_share(self, request, folder_uuid=None):
        folder_obj = self.get_object()

        if folder_obj.owner != request.user:
            raise ValidationError({"detail": "Only the owner can remove share on this Folder."})

        username = request.data.get("username")

        if not username:
            raise ValidationError({"username": "Username is required."})

        target_user = get_object_or_404(User, username=username)

        if folder_obj.shared_with.filter(id=target_user.id).exists():
            folder_obj.shared_with.remove(target_user)

            return Response(
                {"detail": f"Folder unshared with {target_user.username}."},
                status=status.HTTP_200_OK
            )

        return Response(
            {"detail": f"Folder is not shared with {target_user.username}."},
            status=status.HTTP_200_OK
        )


class FileViewSet(ModelViewSet):
    lookup_field = "file_uuid"
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    serializer_class = FileSerializer

    def get_queryset(self):
        return File.objects.filter(Q(owner=self.request.user) | Q(shared_with=self.request.user) | Q(
            folder__shared_with=self.request.user)).distinct().order_by(
            "-uploaded_at")

    def perform_create(self, serializer):
        uploaded_file = self.request.FILES.get("file")
        if not uploaded_file:
            raise ValidationError("No file was uploaded.")
        folder_instance = None
        folder_uuid = self.request.data.get('folder_uuid')
        if folder_uuid:
            try:
                folder_instance = Folder.objects.get(owner=self.request.user,folder_uuid=folder_uuid)
            except Folder.DoesNotExist:
                raise ValidationError({"folder_uuid": "Folder does not exist."})
        serializer.save(
            owner=self.request.user,
            file_name=uploaded_file.name,
            folder=folder_instance,
            file_type=uploaded_file.content_type,
            file_size=uploaded_file.size,
        )

    def perform_update(self, serializer):
            file_obj = self.get_object()

            if file_obj.owner != self.request.user:
                raise ValidationError({"detail": "Only the owner can update this file."})

            if "file" in self.request.FILES or "file" in self.request.data:
                raise ValidationError({"file": "File cannot be updated."})

            serializer.save()

    def perform_destroy(self, instance):
        if instance.owner != self.request.user:
            raise ValidationError({"detail": "Only the owner can delete this file."})

        instance.delete()
    @action(detail=True, methods=['get'])
    def download(self, request, file_uuid=None):
        file_obj = self.get_object()
        return FileResponse(
            file_obj.file,
            as_attachment=True,
            content_type=file_obj.file_type,
            filename=file_obj.file_name,
        )

    @action(detail=True, methods=['post'], url_path='share', parser_classes=[JSONParser])
    def share(self, request, file_uuid=None):
        file_obj = self.get_object()

        if file_obj.owner != request.user:
            raise ValidationError({"detail": "Only the owner can share this file."})

        username = request.data.get("username")

        target_user = get_object_or_404(User, username=username)

        if file_obj.shared_with.filter(id=target_user.id).exists():
            raise ValidationError({"detail": "User is already shared with this file."})

        if target_user == request.user:
            raise ValidationError({"user_id": "You cannot share a file with yourself."})
        file_obj.shared_with.add(target_user)

        return (Response(
            {"detail": f"File shared with {target_user.username}."},
            status=status.HTTP_200_OK
        ))

    @action(detail=True, methods=['post'], url_path='remove_share', parser_classes=[JSONParser])
    def remove_share(self, request, file_uuid=None):
        file_obj = self.get_object()

        if file_obj.owner != request.user:
            raise ValidationError({"detail": "Only the owner can remove share on this file."})

        username = request.data.get("username")

        if not username:
            raise ValidationError({"username": "Username is required."})

        target_user = get_object_or_404(User, username=username)

        if file_obj.shared_with.filter(id=target_user.id).exists():
            file_obj.shared_with.remove(target_user)

            return Response(
                {"detail": f"File unshared with {target_user.username}."},
                status=status.HTTP_200_OK
            )

        return Response(
            {"detail": f"File is not shared with {target_user.username}."},
            status=status.HTTP_200_OK
        )
