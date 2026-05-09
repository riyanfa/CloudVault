# CloudVault – Secure Cloud File Storage API

CloudVault is a backend API for secure file upload, storage, and management.  
It allows authenticated users to upload files, view their own files, retrieve file details, and delete files.

The project is built with Django REST Framework and is designed to demonstrate backend API development, authentication, file handling, and cloud storage integration.

---

## Features

- User registration and JWT authentication
- Authenticated file upload
- User-based file ownership
- List uploaded files for the logged-in user
- Retrieve file metadata
- Delete uploaded files
- File metadata tracking:
  - Original file name
  - File type
  - File size
  - Upload timestamp
- File validation for size and type
- Planned AWS S3 integration for private file storage and temporary download URLs

---

## Tech Stack

- Python
- Django
- Django REST Framework
- Simple JWT
- PostgreSQL / SQLite
- AWS S3

---

## API Endpoints

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/register/` | Register a new user |
| POST | `/api/auth/login/` | Obtain JWT access and refresh tokens |
| POST | `/api/auth/refresh/` | Refresh access token |

### Files

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/files/` | List authenticated user's files |
| POST | `/api/files/` | Upload a new file |
| GET | `/api/files/{id}/` | Retrieve file details |
| DELETE | `/api/files/{id}/` | Delete a file |
| GET | `/api/files/{id}/download/` | Get file download URL |

---

## Example API Usage

### Register a User

```bash
curl -X POST http://127.0.0.1:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "strongpassword123"
  }'
