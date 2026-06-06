# CloudVault

CloudVault is a Django REST Framework API for cloud-style file storage. It supports JWT authentication, folder nesting, file upload/download, ownership rules, and read-only sharing.

This project is built for education and portfolio demonstration. It is not production-ready as-is.

## Features

- User registration with Django password validation
- JWT login and token refresh
- Authenticated file upload, listing, detail, update, delete, and download
- Folder creation, nesting, update, delete, and file listing
- Owner-based access control for files and folders
- Folder sharing by username
- Shared folder access includes subfolders and nested files
- Shared access is read-only for non-owners
- Direct file sharing by username
- File metadata tracking: original file name, content type, size, upload timestamp, owner username
- File upload validation for size, content type, extension, and empty files
- UUID-based file and folder lookups
- API tests covering ownership, sharing, nested folder access, and validation

## Tech Stack

- Python
- Django
- Django REST Framework
- Simple JWT
- SQLite for local development
- AWS S3 integration in progress

## Local Development Notes

This project currently uses SQLite and local media storage for development. Uploaded files are stored under the configured `MEDIA_ROOT`; S3/private object storage integration is being developed.

Important limitations:

- `DEBUG=True` is enabled for local development.
- `SECRET_KEY` is hardcoded for education/local use.
- Upload validation is basic and should still be hardened before production.
- There is no trash/recycle-bin flow; deleting a folder cascades to its subfolders and files.
- S3/private object storage integration is in progress and is not yet the active storage flow.

## Setup

Create and activate a virtual environment, then install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Apply migrations:

```bash
python manage.py migrate
```

Run the development server:

```bash
python manage.py runserver
```

Run checks and tests:

```bash
python manage.py check
python manage.py test app
```

## API Overview

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/register/` | Register a new user and return JWT tokens |
| POST | `/api/auth/login/` | Obtain JWT access and refresh tokens |
| POST | `/api/auth/refresh/` | Refresh access token |
| GET | `/api/whoami` | Return the authenticated user |

### Folders

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/folders/` | List folders owned by or shared with the user |
| POST | `/api/folders/` | Create a folder |
| GET | `/api/folders/{folder_uuid}/` | Retrieve a folder |
| PATCH | `/api/folders/{folder_uuid}/` | Update a folder; owner only |
| DELETE | `/api/folders/{folder_uuid}/` | Delete a folder; owner only |
| GET | `/api/folders/{folder_uuid}/files/` | List files directly inside a folder |
| POST | `/api/folders/{folder_uuid}/share/` | Share a folder by username; owner only |
| POST | `/api/folders/{folder_uuid}/remove_share/` | Remove folder share by username; owner only |

Folder sharing behavior:

- Sharing a folder gives the target user read access to that folder.
- Sharing a folder also gives read access to all descendant subfolders and nested files.
- Shared users cannot update, delete, or re-share folders.

### Files

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/files/` | List files owned by, directly shared with, or available through shared folders |
| POST | `/api/files/` | Upload a file |
| GET | `/api/files/{file_uuid}/` | Retrieve file metadata |
| PATCH | `/api/files/{file_uuid}/` | Update file metadata or move folder; owner only |
| DELETE | `/api/files/{file_uuid}/` | Delete a file; owner only |
| GET | `/api/files/{file_uuid}/download/` | Download a file |
| POST | `/api/files/{file_uuid}/share/` | Share a file by username; owner only |
| POST | `/api/files/{file_uuid}/remove_share/` | Remove file share by username; owner only |

File sharing behavior:

- A file can be accessed if the user owns it, it is directly shared with them, or it is inside a folder shared with them.
- Removing direct file sharing does not remove access if the file is still inside a shared folder.

## Example Usage

### Register

```bash
curl -X POST http://127.0.0.1:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "strongpassword123"
  }'
```

### Login

```bash
curl -X POST http://127.0.0.1:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "strongpassword123"
  }'
```

Use the returned access token:

```bash
Authorization: Bearer <access_token>
```

### Create A Folder

```bash
curl -X POST http://127.0.0.1:8000/api/folders/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "folder_name": "Documents"
  }'
```

### Create A Subfolder

```bash
curl -X POST http://127.0.0.1:8000/api/folders/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "folder_name": "Receipts",
    "parent_folder": "<folder_uuid>"
  }'
```

### Upload A File

```bash
curl -X POST http://127.0.0.1:8000/api/files/ \
  -H "Authorization: Bearer <access_token>" \
  -F "file=@/path/to/file.pdf" \
  -F "folder=<folder_uuid>"
```

### Download A File

```bash
curl -L http://127.0.0.1:8000/api/files/<file_uuid>/download/ \
  -H "Authorization: Bearer <access_token>" \
  -o downloaded-file.pdf
```

### Share A Folder

```bash
curl -X POST http://127.0.0.1:8000/api/folders/<folder_uuid>/share/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "otheruser"
  }'
```

### Share A File

```bash
curl -X POST http://127.0.0.1:8000/api/files/<file_uuid>/share/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "otheruser"
  }'
```
