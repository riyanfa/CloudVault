import shutil
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from .models import File, Folder

TEST_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class CloudVaultAPITests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="password")
        self.other_user = User.objects.create_user(
            username="other", password="password"
        )

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def test_dashboard_frontend_loads(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "CloudVault")
        self.assertContains(response, "dashboard.js")

    def test_create_folder_uses_serializer_parent_folder_validation(self):
        parent_folder = Folder.objects.create(
            owner=self.owner,
            folder_name="Documents",
        )
        self.authenticate(self.owner)

        response = self.client.post(
            "/api/folders/",
            {
                "folder_name": "Photos",
                "parent_folder": str(parent_folder.folder_uuid),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        folder = Folder.objects.get(folder_name="Photos")
        self.assertEqual(folder.owner, self.owner)
        self.assertEqual(folder.parent_folder, parent_folder)

    def test_create_folder_rejects_another_users_parent_folder(self):
        other_folder = Folder.objects.create(
            owner=self.other_user,
            folder_name="Private",
        )
        self.authenticate(self.owner)

        response = self.client.post(
            "/api/folders/",
            {
                "folder_name": "Photos",
                "parent_folder": str(other_folder.folder_uuid),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("parent_folder", response.data)

    def test_update_folder_rejects_descendant_as_parent(self):
        root_folder = Folder.objects.create(owner=self.owner, folder_name="Root")
        child_folder = Folder.objects.create(
            owner=self.owner,
            folder_name="Child",
            parent_folder=root_folder,
        )
        grandchild_folder = Folder.objects.create(
            owner=self.owner,
            folder_name="Grandchild",
            parent_folder=child_folder,
        )
        self.authenticate(self.owner)

        response = self.client.patch(
            f"/api/folders/{root_folder.folder_uuid}/",
            {"parent_folder": str(grandchild_folder.folder_uuid)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("parent_folder", response.data)

    def test_upload_file_uses_serializer_folder_validation(self):
        folder = Folder.objects.create(owner=self.owner, folder_name="Documents")
        self.authenticate(self.owner)

        response = self.client.post(
            "/api/files/",
            {
                "file": SimpleUploadedFile(
                    "note.txt",
                    b"hello",
                    content_type="text/plain",
                ),
                "folder": str(folder.folder_uuid),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        file_obj = File.objects.get(file_name="note.txt")
        self.assertEqual(file_obj.owner, self.owner)
        self.assertEqual(file_obj.folder, folder)

    def test_upload_file_rejects_another_users_folder(self):
        other_folder = Folder.objects.create(
            owner=self.other_user,
            folder_name="Private",
        )
        self.authenticate(self.owner)

        response = self.client.post(
            "/api/files/",
            {
                "file": SimpleUploadedFile(
                    "note.txt",
                    b"hello",
                    content_type="text/plain",
                ),
                "folder": str(other_folder.folder_uuid),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("folder", response.data)

    def test_upload_file_rejects_empty_file(self):
        self.authenticate(self.owner)

        response = self.client.post(
            "/api/files/",
            {
                "file": SimpleUploadedFile(
                    "empty.txt",
                    b"",
                    content_type="text/plain",
                ),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file", response.data)

    def test_upload_file_accepts_arbitrary_file_type(self):
        self.authenticate(self.owner)

        response = self.client.post(
            "/api/files/",
            {
                "file": SimpleUploadedFile(
                    "script.exe",
                    b"hello",
                    content_type="application/x-msdownload",
                ),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(File.objects.filter(file_name="script.exe").exists())

    def test_upload_file_rejects_blank_original_filename(self):
        self.authenticate(self.owner)

        response = self.client.post(
            "/api/files/",
            {
                "file": SimpleUploadedFile(
                    "   ",
                    b"hello",
                    content_type="text/plain",
                ),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file", response.data)

    def test_upload_file_accepts_declared_type_without_signature_check(self):
        self.authenticate(self.owner)

        response = self.client.post(
            "/api/files/",
            {
                "file": SimpleUploadedFile(
                    "fake.png",
                    b"not a png",
                    content_type="image/png",
                ),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(File.objects.filter(file_name="fake.png").exists())

    def test_upload_file_rejects_oversized_file(self):
        self.authenticate(self.owner)

        with override_settings(CLOUDVAULT_MAX_UPLOAD_SIZE=4):
            response = self.client.post(
                "/api/files/",
                {
                    "file": SimpleUploadedFile(
                        "large.txt",
                        b"hello",
                        content_type="text/plain",
                    ),
                },
                format="multipart",
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file", response.data)

    def test_update_file_moves_to_folder(self):
        folder = Folder.objects.create(owner=self.owner, folder_name="Target")
        file_obj = File.objects.create(
            owner=self.owner,
            file_name="move.txt",
            file_type="text/plain",
            file_size=5,
            file=SimpleUploadedFile(
                "move.txt",
                b"hello",
                content_type="text/plain",
            ),
        )
        self.authenticate(self.owner)

        response = self.client.patch(
            f"/api/files/{file_obj.file_uuid}/",
            {"folder": str(folder.folder_uuid)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        file_obj.refresh_from_db()
        self.assertEqual(file_obj.folder, folder)

    def test_file_list_root_query_excludes_folder_files(self):
        folder = Folder.objects.create(owner=self.owner, folder_name="Target")
        File.objects.create(
            owner=self.owner,
            file_name="root.txt",
            file_type="text/plain",
            file_size=5,
            file=SimpleUploadedFile(
                "root.txt",
                b"hello",
                content_type="text/plain",
            ),
        )
        File.objects.create(
            owner=self.owner,
            file_name="nested.txt",
            file_type="text/plain",
            file_size=5,
            file=SimpleUploadedFile(
                "nested.txt",
                b"hello",
                content_type="text/plain",
            ),
            folder=folder,
        )
        self.authenticate(self.owner)

        response = self.client.get("/api/files/?folder=root")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        file_names = {item["file_name"] for item in response.data}
        self.assertIn("root.txt", file_names)
        self.assertNotIn("nested.txt", file_names)

    def test_delete_file_removes_uploaded_file_from_storage(self):
        self.authenticate(self.owner)

        upload_response = self.client.post(
            "/api/files/",
            {
                "file": SimpleUploadedFile(
                    "delete.txt",
                    b"hello",
                    content_type="text/plain",
                ),
            },
            format="multipart",
        )

        self.assertEqual(upload_response.status_code, status.HTTP_201_CREATED)
        file_obj = File.objects.get(file_name="delete.txt")
        storage = file_obj.file.storage
        file_name = file_obj.file.name
        self.assertTrue(storage.exists(file_name))

        delete_response = self.client.delete(f"/api/files/{file_obj.file_uuid}/")

        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(storage.exists(file_name))

    def test_download_missing_storage_file_returns_not_found(self):
        file_obj = File.objects.create(
            owner=self.owner,
            file_name="missing.png",
            file_type="image/png",
            file_size=5,
            file="files/user_1/missing.png",
        )
        self.authenticate(self.owner)

        response = self.client.get(f"/api/files/{file_obj.file_uuid}/download/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["detail"], "File is no longer available in storage.")

    def test_shared_folder_files_lists_files_for_shared_user(self):
        folder = Folder.objects.create(owner=self.owner, folder_name="Shared")
        folder.shared_with.add(self.other_user)
        File.objects.create(
            owner=self.owner,
            file_name="shared.txt",
            file_type="text/plain",
            file_size=5,
            file=SimpleUploadedFile(
                "shared.txt",
                b"hello",
                content_type="text/plain",
            ),
            folder=folder,
        )
        self.authenticate(self.other_user)

        response = self.client.get(f"/api/folders/{folder.folder_uuid}/files/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["file_name"], "shared.txt")

    def test_shared_folder_access_includes_subfolders_and_nested_files(self):
        root_folder = Folder.objects.create(owner=self.owner, folder_name="Root")
        child_folder = Folder.objects.create(
            owner=self.owner,
            folder_name="Child",
            parent_folder=root_folder,
        )
        root_folder.shared_with.add(self.other_user)
        File.objects.create(
            owner=self.owner,
            file_name="nested.txt",
            file_type="text/plain",
            file_size=5,
            file=SimpleUploadedFile(
                "nested.txt",
                b"hello",
                content_type="text/plain",
            ),
            folder=child_folder,
        )
        self.authenticate(self.other_user)

        folders_response = self.client.get("/api/folders/")
        files_response = self.client.get("/api/files/")
        child_files_response = self.client.get(
            f"/api/folders/{child_folder.folder_uuid}/files/"
        )

        folder_ids = {item["folder_uuid"] for item in folders_response.data}
        file_names = {item["file_name"] for item in files_response.data}

        self.assertEqual(folders_response.status_code, status.HTTP_200_OK)
        self.assertEqual(files_response.status_code, status.HTTP_200_OK)
        self.assertEqual(child_files_response.status_code, status.HTTP_200_OK)
        self.assertIn(str(root_folder.folder_uuid), folder_ids)
        self.assertIn(str(child_folder.folder_uuid), folder_ids)
        self.assertIn("nested.txt", file_names)
        self.assertEqual(child_files_response.data[0]["file_name"], "nested.txt")

    def test_shared_subfolder_access_is_read_only(self):
        root_folder = Folder.objects.create(owner=self.owner, folder_name="Root")
        child_folder = Folder.objects.create(
            owner=self.owner,
            folder_name="Child",
            parent_folder=root_folder,
        )
        root_folder.shared_with.add(self.other_user)
        self.authenticate(self.other_user)

        response = self.client.patch(
            f"/api/folders/{child_folder.folder_uuid}/",
            {"folder_name": "Changed"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_folder_share_requires_username(self):
        folder = Folder.objects.create(owner=self.owner, folder_name="Documents")
        self.authenticate(self.owner)

        response = self.client.post(
            f"/api/folders/{folder.folder_uuid}/share/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", response.data)

    def test_file_share_requires_username(self):
        file_obj = File.objects.create(
            owner=self.owner,
            file_name="note.txt",
            file_type="text/plain",
            file_size=5,
            file=SimpleUploadedFile(
                "note.txt",
                b"hello",
                content_type="text/plain",
            ),
        )
        self.authenticate(self.owner)

        response = self.client.post(
            f"/api/files/{file_obj.file_uuid}/share/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", response.data)

    def test_shared_user_cannot_share_folder(self):
        folder = Folder.objects.create(owner=self.owner, folder_name="Documents")
        folder.shared_with.add(self.other_user)
        self.authenticate(self.other_user)

        response = self.client.post(
            f"/api/folders/{folder.folder_uuid}/share/",
            {"username": self.owner.username},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_register_rejects_weak_password(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "username": "weakuser",
                "email": "weak@example.com",
                "password": "123",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data)

    def test_shared_user_cannot_share_file(self):
        file_obj = File.objects.create(
            owner=self.owner,
            file_name="note.txt",
            file_type="text/plain",
            file_size=5,
            file=SimpleUploadedFile(
                "note.txt",
                b"hello",
                content_type="text/plain",
            ),
        )
        file_obj.shared_with.add(self.other_user)
        self.authenticate(self.other_user)

        response = self.client.post(
            f"/api/files/{file_obj.file_uuid}/share/",
            {"username": self.owner.username},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
