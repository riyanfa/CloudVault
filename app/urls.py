from django.urls import path, include
from rest_framework.routers import DefaultRouter
from app.viewset import FileViewSet

app_name = "app"

router = DefaultRouter()
router.register("files", FileViewSet, basename="files")

urlpatterns = [
    path("", include(router.urls)),
]