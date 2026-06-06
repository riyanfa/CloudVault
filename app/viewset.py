from django.contrib.auth.models import User
from django.db.models import Q
from django.http import FileResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from .models import File, Folder
from .serializers import FileSerializer, FolderSerializer


def get_shared_folder_tree_ids(user):
    folder_ids = set(
        Folder.objects.filter(shared_with=user).values_list("folder_uuid", flat=True)
    )
    unchecked_ids = set(folder_ids)

    while unchecked_ids:
        child_ids = set(
            Folder.objects.filter(parent_folder_id__in=unchecked_ids).values_list(
                "folder_uuid", flat=True
            )
        )
        child_ids -= folder_ids
        folder_ids.update(child_ids)
        unchecked_ids = child_ids

    return folder_ids


class FolderViewSet(ModelViewSet):
    queryset = Folder.objects.none()
    lookup_field = "folder_uuid"
    serializer_class = FolderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Folder.objects.none()

        if not self.request.user.is_authenticated:
            return Folder.objects.none()

        shared_folder_ids = get_shared_folder_tree_ids(self.request.user)

        return (
            Folder.objects.filter(
                Q(owner=self.request.user) | Q(folder_uuid__in=shared_folder_ids)
            )
            .distinct()
            .order_by("-created_at")
        )

    def update(self, request, *args, **kwargs):
        folder = self.get_object()

        if folder.owner != request.user:
            raise PermissionDenied("Only the owner can update this folder.")

        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        folder = self.get_object()

        if folder.owner != self.request.user:
            raise PermissionDenied("Only the owner can update this folder.")

        serializer.save(owner=self.request.user)

    def perform_destroy(self, instance):
        if instance.owner != self.request.user:
            raise PermissionDenied("Only the owner can delete this folder.")

        instance.delete()

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=["get"], url_path="files")
    def files(self, request, folder_uuid=None):
        folder = self.get_object()
        files = File.objects.filter(folder=folder).order_by("-uploaded_at")
        serializer = FileSerializer(files, many=True, context={"request": request})
        return Response(serializer.data)

    @action(
        detail=True, methods=["post"], url_path="share", parser_classes=[JSONParser]
    )
    def share(self, request, folder_uuid=None):
        folder_obj = self.get_object()

        if folder_obj.owner != request.user:
            raise PermissionDenied("Only the owner can share this Folder.")

        username = request.data.get("username")

        if not username:
            raise ValidationError({"username": "Username is required."})

        target_user = get_object_or_404(User, username=username)

        if folder_obj.shared_with.filter(id=target_user.id).exists():
            raise ValidationError(
                {"detail": "User is already shared with this Folder."}
            )

        if target_user == request.user:
            raise ValidationError(
                {"user_id": "You cannot share a Folder with yourself."}
            )
        folder_obj.shared_with.add(target_user)

        return Response(
            {"detail": f"Folder shared with {target_user.username}."},
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="remove_share",
        parser_classes=[JSONParser],
    )
    def remove_share(self, request, folder_uuid=None):
        folder_obj = self.get_object()

        if folder_obj.owner != request.user:
            raise PermissionDenied("Only the owner can remove share on this Folder.")

        username = request.data.get("username")

        if not username:
            raise ValidationError({"username": "Username is required."})

        target_user = get_object_or_404(User, username=username)

        if folder_obj.shared_with.filter(id=target_user.id).exists():
            folder_obj.shared_with.remove(target_user)

            return Response(
                {"detail": f"Folder unshared with {target_user.username}."},
                status=status.HTTP_200_OK,
            )

        return Response(
            {"detail": f"Folder is not shared with {target_user.username}."},
            status=status.HTTP_200_OK,
        )


class FileViewSet(ModelViewSet):
    queryset = File.objects.none()
    lookup_field = "file_uuid"
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    serializer_class = FileSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return File.objects.none()

        if not self.request.user.is_authenticated:
            return File.objects.none()

        shared_folder_ids = get_shared_folder_tree_ids(self.request.user)

        return (
            File.objects.filter(
                Q(owner=self.request.user)
                | Q(shared_with=self.request.user)
                | Q(folder_id__in=shared_folder_ids)
            )
            .distinct()
            .order_by("-uploaded_at")
        )

    def perform_create(self, serializer):
        uploaded_file = self.request.FILES.get("file")
        if not uploaded_file:
            raise ValidationError("No file was uploaded.")

        serializer.save(
            owner=self.request.user,
            file_name=uploaded_file.name,
            file_type=uploaded_file.content_type,
            file_size=uploaded_file.size,
        )

    def perform_update(self, serializer):
        file_obj = self.get_object()

        if file_obj.owner != self.request.user:
            raise PermissionDenied("Only the owner can update this file.")

        if "file" in self.request.FILES or "file" in self.request.data:
            raise ValidationError({"file": "File cannot be updated."})

        serializer.save()

    def perform_destroy(self, instance):
        if instance.owner != self.request.user:
            raise PermissionDenied("Only the owner can delete this file.")

        instance.delete()

    @action(detail=True, methods=["get"])
    def download(self, request, file_uuid=None):
        file_obj = self.get_object()
        return FileResponse(
            file_obj.file,
            as_attachment=True,
            content_type=file_obj.file_type,
            filename=file_obj.file_name,
        )

    @action(
        detail=True, methods=["post"], url_path="share", parser_classes=[JSONParser]
    )
    def share(self, request, file_uuid=None):
        file_obj = self.get_object()

        if file_obj.owner != request.user:
            raise PermissionDenied("Only the owner can share this file.")

        username = request.data.get("username")

        if not username:
            raise ValidationError({"username": "Username is required."})

        target_user = get_object_or_404(User, username=username)

        if file_obj.shared_with.filter(id=target_user.id).exists():
            raise ValidationError({"detail": "User is already shared with this file."})

        if target_user == request.user:
            raise ValidationError({"user_id": "You cannot share a file with yourself."})
        file_obj.shared_with.add(target_user)

        return Response(
            {"detail": f"File shared with {target_user.username}."},
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="remove_share",
        parser_classes=[JSONParser],
    )
    def remove_share(self, request, file_uuid=None):
        file_obj = self.get_object()

        if file_obj.owner != request.user:
            raise PermissionDenied("Only the owner can remove share on this file.")

        username = request.data.get("username")

        if not username:
            raise ValidationError({"username": "Username is required."})

        target_user = get_object_or_404(User, username=username)

        if file_obj.shared_with.filter(id=target_user.id).exists():
            file_obj.shared_with.remove(target_user)

            return Response(
                {"detail": f"File unshared with {target_user.username}."},
                status=status.HTTP_200_OK,
            )

        return Response(
            {"detail": f"File is not shared with {target_user.username}."},
            status=status.HTTP_200_OK,
        )
