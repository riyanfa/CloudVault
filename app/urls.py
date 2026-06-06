from django.urls import include, path
from rest_framework.routers import DefaultRouter

from app.views import whoami
from app.viewset import FileViewSet, FolderViewSet

app_name = "app"

router = DefaultRouter()
router.register("files", FileViewSet, basename="files")
router.register("folders", FolderViewSet, basename="folders")
urlpatterns = [
    path("", include(router.urls)),
    path("whoami", whoami, name="whoami"),
]
