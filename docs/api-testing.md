# API Testing Guide

This guide documents how to interact with the Urology Data Platform API.

## Prerequisites

```bash
# Start infrastructure
docker-compose up -d

# Run database migrations
~/.pixi/bin/pixi run alembic upgrade head

# Start the API server
~/.pixi/bin/pixi run uvicorn src.main:app --reload
```

The API will be available at http://localhost:8000

## Interactive Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Health Check

```bash
curl http://localhost:8000/health
```

Response:
```json
{"status": "healthy"}
```

### Authentication

#### Register a User

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testdoc",
    "email": "doc@hospital.com",
    "password": "secure123",
    "role": "urologist",
    "hospital_id": "HOSP001"
  }'
```

Response:
```json
{
  "id": "uuid-here",
  "username": "testdoc",
  "email": "doc@hospital.com",
  "role": "urologist",
  "hospital_id": "HOSP001",
  "is_active": true,
  "created_at": "2024-01-21T10:00:00"
}
```

#### Login (Get JWT Token)

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -d "username=testdoc&password=secure123"
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Save the token for authenticated requests:**
```bash
export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Patients (Requires Authentication)

All patient endpoints require the `Authorization: Bearer <token>` header.

#### Create Patient

```bash
curl -X POST http://localhost:8000/api/patients/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "mrn": "MRN001",
    "first_name": "张",
    "last_name": "三",
    "date_of_birth": "1985-03-15",
    "gender": "male",
    "hospital_id": "HOSP001"
  }'
```

Response:
```json
{
  "id": "uuid-here",
  "mrn": "MRN001",
  "first_name": "张",
  "last_name": "三",
  "date_of_birth": "1985-03-15",
  "gender": "male",
  "hospital_id": "HOSP001",
  "created_at": "2024-01-21T10:00:00",
  "updated_at": "2024-01-21T10:00:00"
}
```

#### List Patients

```bash
# List all patients
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/patients/

# With pagination
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/patients/?skip=0&limit=10"

# With search
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/patients/?search=张"
```

#### Get Single Patient

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/patients/{patient_id}
```

#### Update Patient

```bash
curl -X PATCH http://localhost:8000/api/patients/{patient_id} \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "李",
    "hospital_id": "HOSP002"
  }'
```

#### Delete Patient

```bash
curl -X DELETE http://localhost:8000/api/patients/{patient_id} \
  -H "Authorization: Bearer $TOKEN"
```

Returns: `204 No Content`

## Running Tests

```bash
# Run all tests
~/.pixi/bin/pixi run pytest -v

# Run with coverage
~/.pixi/bin/pixi run pytest -v --cov=src --cov-report=term-missing

# Run specific test file
~/.pixi/bin/pixi run pytest tests/test_auth.py -v

# Run specific test class
~/.pixi/bin/pixi run pytest tests/test_patients.py::TestCreatePatient -v
```

## Error Responses

### 401 Unauthorized
```json
{"detail": "Could not validate credentials"}
```

### 400 Bad Request
```json
{"detail": "Username already registered"}
```

### 404 Not Found
```json
{"detail": "Patient not found"}
```

### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
```
