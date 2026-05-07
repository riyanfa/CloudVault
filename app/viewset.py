from django.http import FileResponse
from rest_framework import status, serializers
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import  IsAuthenticated
from rest_framework.viewsets import ModelViewSet
from rest_framework.exceptions import ValidationError
from .models import File
from .serializers import FileSerializer


class FileViewSet(ModelViewSet):

    permission_classes = [IsAuthenticated]
    queryset = File.objects.all()
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = FileSerializer

    def get_queryset(self):
        return File.objects.filter(owner=self.request.user).order_by("-uploaded_at")

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