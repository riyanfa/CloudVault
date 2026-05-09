from django.contrib.auth.models import User
from django.db.models import Q
from django.http import FileResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import  IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.exceptions import ValidationError
from .models import File
from .serializers import FileSerializer


class FileViewSet(ModelViewSet):

    permission_classes = [IsAuthenticated]
    queryset = File.objects.all()
    parser_classes = [MultiPartParser, FormParser,JSONParser]
    serializer_class = FileSerializer

    def get_queryset(self):
        return File.objects.filter(Q(owner=self.request.user)|Q(shared_with=self.request.user)).distinct().order_by("-uploaded_at")

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
        if "file" in self.request.FILES or "file" in self.request.data:
            raise ValidationError({"file": "File cannot be updated."})
        serializer.save()
    @action(detail=True,methods=['get'],url_path='download')
    def download(self,request,pk=None):
        file_obj=self.get_object()
        file_down=file_obj.file.open("rb")
        return FileResponse(
            file_down,
            as_attachment=True,
            content_type=file_obj.file_type,
            filename=file_obj.file_name,
        )
    @action(detail=True,methods=['post'],url_path='share',parser_classes=[JSONParser])
    def share(self,request,pk=None):
        file_obj=self.get_object()

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
        )   )
    @action(detail=True,methods=['post'],url_path='remove_share',parser_classes=[JSONParser])
    def remove_share(self,request,pk=None):
        file_obj=self.get_object()

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