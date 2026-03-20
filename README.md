# AI-Powered Quiz API

A REST API built with Django and Django REST Framework that lets users create topic-based quizzes, where questions are generated automatically using Google Gemini AI.

---

## Table of Contents
1. [Local Setup](#local-setup)
2. [Project Structure](#project-structure)
3. [Database Schema](#database-schema)
4. [API Endpoints](#api-endpoints)
5. [Authentication](#authentication)
6. [AI Integration](#ai-integration)
7. [Design Decisions](#design-decisions)
8. [Deployment](#deployment)

---

## Local Setup

### 1. Prerequisites
- Python 3.11+
- PostgreSQL (running locally)
- A free Google Gemini API key: https://aistudio.google.com

### 2. Clone and install dependencies
```bash
git clone <your-repo-url>
cd quiz_api

# Create a virtual environment
python -m venv venv
source venv/bin/activate        # Mac/Linux
# venv\Scripts\activate         # Windows

# Install packages
pip install -r requirements.txt
```

### 3. Set up environment variables
```bash
cp .env.example .env
# Open .env and fill in:
#   SECRET_KEY=<generate one at https://djecrety.ir>
#   DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/quiz_db
#   GEMINI_API_KEY=<your key from https://aistudio.google.com>
```

### 4. Create the PostgreSQL database
```bash
psql -U postgres
CREATE DATABASE quiz_db;
\q
```

### 5. Run migrations (creates all tables)
```bash
python manage.py migrate
```

### 6. Create an admin superuser
```bash
python manage.py createsuperuser
# Then open /admin/ and set this user's role to "admin" in the Users table
```

### 7. Start the development server
```bash
python manage.py runserver
# API is now at: http://localhost:8000/api/
# Admin panel:   http://localhost:8000/admin/
```

---

## Project Structure

```
quiz_api/
├── manage.py                    # Django CLI tool
├── requirements.txt             # Python dependencies
├── Procfile                     # For Railway/Heroku deployment
├── .env.example                 # Environment variable template
│
├── quiz_project/                # Django project config
│   ├── settings.py              # All settings (DB, auth, caching, etc.)
│   ├── urls.py                  # Root URL router
│   └── wsgi.py                  # WSGI entry point for production
│
└── apps/                        # All feature apps
    ├── users/                   # User registration, auth, profiles
    │   ├── models.py            # Custom User model (extends AbstractUser)
    │   ├── serializers.py       # Register, profile serializers
    │   ├── views.py             # Register, login, profile, admin views
    │   ├── permissions.py       # IsAdminUser, IsOwnerOrAdmin
    │   └── urls.py              # /api/users/ routes
    │
    ├── quiz/                    # Quiz and attempt management
    │   ├── models.py            # Quiz, Question, QuizAttempt, UserAnswer
    │   ├── ai_service.py        # Google Gemini integration + caching
    │   ├── serializers.py       # Quiz, attempt serializers
    │   ├── views.py             # Quiz CRUD, attempt, submit views
    │   └── urls.py              # /api/quiz/ routes
    │
    └── analytics/               # Performance stats
        ├── views.py             # My stats, quiz stats, leaderboard, history
        └── urls.py              # /api/analytics/ routes
```

---

## Database Schema

### users
| Column      | Type         | Notes                          |
|-------------|--------------|--------------------------------|
| id          | bigint PK    | Auto-generated                 |
| username    | varchar(150) | Unique                         |
| email       | varchar(254) |                                |
| password    | varchar(128) | Hashed (never plain text)      |
| role        | varchar(10)  | 'user' or 'admin'              |
| bio         | text         | Optional profile description   |
| date_joined | timestamp    | Auto-set on creation           |

### quizzes
| Column         | Type        | Notes                           |
|----------------|-------------|---------------------------------|
| id             | bigint PK   |                                 |
| title          | varchar(255)|                                 |
| topic          | varchar(200)| Used to prompt the AI           |
| difficulty     | varchar(10) | 'easy', 'medium', 'hard'        |
| question_count | int         | 3–20                            |
| status         | varchar(10) | 'draft', 'ready', 'failed'      |
| created_by_id  | FK → users  |                                 |
| created_at     | timestamp   |                                 |

### questions
| Column         | Type        | Notes                                |
|----------------|-------------|--------------------------------------|
| id             | bigint PK   |                                      |
| quiz_id        | FK → quizzes|                                      |
| question_text  | text        |                                      |
| option_a/b/c/d | varchar(500)|                                      |
| correct_option | varchar(1)  | 'A', 'B', 'C', or 'D'               |
| explanation    | text        | Shown after quiz submission          |
| order          | int         | Position in quiz                     |

### quiz_attempts
| Column           | Type       | Notes                               |
|------------------|------------|-------------------------------------|
| id               | bigint PK  |                                     |
| user_id          | FK → users |                                     |
| quiz_id          | FK → quizzes|                                    |
| status           | varchar(15)| 'in_progress', 'completed', etc.    |
| score            | int        | Number of correct answers           |
| score_percentage | float      | 0.0 – 100.0                         |
| total_questions  | int        |                                     |
| started_at       | timestamp  |                                     |
| completed_at     | timestamp  | Null until submitted                |

### user_answers
| Column          | Type             | Notes                          |
|-----------------|------------------|--------------------------------|
| id              | bigint PK        |                                |
| attempt_id      | FK → quiz_attempts|                               |
| question_id     | FK → questions   |                                |
| selected_option | varchar(1)       | 'A', 'B', 'C', or 'D'         |
| is_correct      | boolean          | Set automatically on save      |
| answered_at     | timestamp        |                                |
| UNIQUE          | (attempt, question) | One answer per question     |

---

## API Endpoints

### Authentication
| Method | URL                    | Auth? | Description                    |
|--------|------------------------|-------|--------------------------------|
| POST   | /api/users/register/   | No    | Create a new account           |
| POST   | /api/auth/login/       | No    | Get JWT access + refresh tokens|
| POST   | /api/auth/refresh/     | No    | Refresh expired access token   |

### User Management
| Method | URL                        | Auth?     | Description              |
|--------|----------------------------|-----------|--------------------------|
| GET    | /api/users/me/             | User      | View my profile          |
| PUT    | /api/users/me/             | User      | Update my profile        |
| GET    | /api/users/                | Admin     | List all users           |
| GET    | /api/users/<id>/           | Admin     | View a user              |
| DELETE | /api/users/<id>/           | Admin     | Delete a user            |
| POST   | /api/users/<id>/promote/   | Admin     | Change user role         |

### Quizzes
| Method | URL                          | Auth?     | Description                    |
|--------|------------------------------|-----------|--------------------------------|
| GET    | /api/quiz/                   | User      | List all ready quizzes         |
| POST   | /api/quiz/                   | User      | Create quiz (AI generates Qs)  |
| GET    | /api/quiz/<id>/              | User      | Get quiz + questions           |
| DELETE | /api/quiz/<id>/              | Owner/Admin| Delete a quiz                 |
| GET    | /api/quiz/my-quizzes/        | User      | Quizzes I created              |

### Attempts
| Method | URL                              | Auth?      | Description              |
|--------|----------------------------------|------------|--------------------------|
| POST   | /api/quiz/<id>/attempt/          | User       | Start a quiz attempt     |
| POST   | /api/quiz/attempts/<id>/submit/  | Owner      | Submit answers           |
| GET    | /api/quiz/attempts/<id>/         | Owner/Admin| View attempt results     |
| GET    | /api/quiz/my-attempts/           | User       | My attempt history       |
| GET    | /api/quiz/all-attempts/          | Admin      | All attempts (admin)     |

### Analytics
| Method | URL                           | Auth?     | Description                  |
|--------|-------------------------------|-----------|------------------------------|
| GET    | /api/analytics/me/            | User      | My overall stats             |
| GET    | /api/analytics/quiz/<id>/     | Owner/Admin| Stats for a specific quiz   |
| GET    | /api/analytics/leaderboard/   | User      | Top 10 users by score        |
| GET    | /api/analytics/history/       | User      | My completed quiz history    |
| GET    | /api/analytics/admin/dashboard/| Admin    | Platform-wide stats          |

---

## Authentication

This API uses **JWT (JSON Web Tokens)**. Here's how to use it:

### Step 1: Register
```http
POST /api/users/register/
Content-Type: application/json

{
  "username": "john",
  "email": "john@example.com",
  "password": "SecurePass123!",
  "password_confirm": "SecurePass123!"
}
```

### Step 2: Login
```http
POST /api/auth/login/
Content-Type: application/json

{
  "username": "john",
  "password": "SecurePass123!"
}
```
Response:
```json
{
  "access": "eyJ0eX...",    ← use this in every request header
  "refresh": "eyJ0eX..."    ← use this to get new access tokens
}
```

### Step 3: Use the token
```http
GET /api/quiz/
Authorization: Bearer eyJ0eX...
```

### Step 4: Refresh when expired (access token lasts 1 hour)
```http
POST /api/auth/refresh/
Content-Type: application/json

{ "refresh": "eyJ0eX..." }
```

---

## AI Integration

We use **Google Gemini 1.5 Flash** (free tier) to generate quiz questions.

### How it works (`apps/quiz/ai_service.py`):
1. Build a prompt asking Gemini for N questions on a topic at a difficulty level
2. Request JSON-only output (no markdown, no extra text)
3. Send HTTP POST to Gemini API
4. Parse and validate the JSON response
5. Cache the result for 24 hours (same topic/difficulty won't re-call the API)
6. Save questions to the database

### Getting a free API key:
1. Go to https://aistudio.google.com
2. Click "Get API key" → "Create API key"
3. Copy the key into your `.env` as `GEMINI_API_KEY`

### Error handling:
- **Timeout**: Returns 503 with a user-friendly message
- **Rate limit (429)**: Returns 503 asking user to try again later
- **Invalid key (403)**: Returns 503 with configuration error message
- **Bad JSON**: Retries parsing with whitespace cleanup
- **Quiz marked `failed`**: Status saved so admin can see which quizzes failed

### Caching strategy:
- Cache key: `ai_quiz_{topic}_{difficulty}_{count}`
- TTL: 24 hours
- Same topic/difficulty combo reuses cached questions (no API cost)
- Production upgrade path: swap `LocMemCache` for Redis

---

## Design Decisions

### Custom User Model
Extended Django's `AbstractUser` instead of using a separate Profile model. This is simpler and avoids extra JOINs on every user query. The `role` field controls permissions.

### Role-based permissions vs. Django's built-in groups
We use a simple `role` field ('user' or 'admin') rather than Django's Groups system. This is easier to understand and sufficient for the requirements. Groups would be better if we needed granular per-permission control.

### Quiz status (draft → ready → failed)
When a quiz is first saved, it's in `draft` state. After AI generates questions successfully, it becomes `ready`. If the AI call fails, it becomes `failed`. This prevents users from attempting quizzes with no questions.

### Answers stored with `is_correct`
`UserAnswer.is_correct` is calculated and stored when the answer is saved (in the `save()` method). This denormalization makes analytics queries much faster — no need to join questions on every stats query.

### Caching
- AI responses are cached for 24 hours (avoids repeat API calls for same topic)
- Production: replace `LocMemCache` with Redis for multi-process/multi-server caching
- DRF throttling limits: 20 req/hour for unauthenticated, 200/hour for authenticated users

### Pagination
All list endpoints use DRF's `PageNumberPagination` (10 items/page by default).
Use `?page=2` to get the next page.

### select_related and prefetch_related
Used throughout views to minimize N+1 query problems:
- `select_related("quiz")` on attempts — single JOIN instead of N extra queries
- `prefetch_related("questions")` on quiz detail — fetches all questions in one query

---

## Deployment (Railway)

1. Push to GitHub
2. Go to https://railway.app → New Project → Deploy from GitHub
3. Add a PostgreSQL plugin
4. Set environment variables in Railway dashboard:
   - `SECRET_KEY`, `DEBUG=False`, `GEMINI_API_KEY`
   - `DATABASE_URL` is auto-set by Railway's PostgreSQL plugin
   - `ALLOWED_HOSTS=your-app.railway.app`
5. Railway detects the `Procfile` and runs `gunicorn` automatically
6. Run migrations: in Railway shell → `python manage.py migrate`

---

## Testing Approach

Manual testing flow:
1. Register → Login → get JWT token
2. POST /api/quiz/ with a topic → verify questions are generated
3. POST /api/quiz/<id>/attempt/ → get attempt_id
4. POST /api/quiz/attempts/<id>/submit/ with answers → check score
5. GET /api/analytics/me/ → verify stats update

For automated tests, add `tests.py` in each app using Django's `TestCase`:
```python
from django.test import TestCase
from rest_framework.test import APIClient

class QuizCreateTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        # create test user, authenticate...

    def test_create_quiz(self):
        response = self.client.post("/api/quiz/", {...})
        self.assertEqual(response.status_code, 201)
```
