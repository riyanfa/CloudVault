from django.urls import path, include
from rest_framework.routers import DefaultRouter
from app.viewset import FileViewSet, FolderViewSet
from app.views import whoami
app_name = "app"

router = DefaultRouter()
router.register("files", FileViewSet, basename="files")
router.register("folder", FolderViewSet, basename="folder")
urlpatterns = [
    path("", include(router.urls)),
    path("whoami",whoami,name="whoami")
]