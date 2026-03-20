# QuizAI — AI-Powered Quiz API

A full-stack quiz platform built with Django REST Framework and Groq AI. Users can register, take AI-generated quizzes on any topic, track their performance, and compete on a leaderboard. Admins can create quizzes by simply providing a topic — the AI generates all the questions automatically.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Features](#2-features)
3. [Tech Stack](#3-tech-stack)
4. [Project Structure](#4-project-structure)
5. [Database Schema](#5-database-schema)
6. [API Endpoints](#6-api-endpoints)
7. [Authentication System](#7-authentication-system)
8. [AI Integration](#8-ai-integration)
9. [Role-Based Permissions](#9-role-based-permissions)
10. [Caching Strategy](#10-caching-strategy)
11. [Local Setup Instructions](#11-local-setup-instructions)
12. [Environment Variables](#12-environment-variables)
13. [Running Tests](#13-running-tests)
14. [Frontend](#14-frontend)
15. [Design Decisions and Trade-offs](#15-design-decisions-and-trade-offs)
16. [Challenges and Solutions](#16-challenges-and-solutions)

---

## 1. Project Overview

QuizAI is a REST API that powers a complete quiz application. Here is the full user journey:

1. A user registers and logs in to get a JWT access token
2. An admin creates a quiz by providing a topic, difficulty, and question count
3. The API calls Groq AI (free tier) which generates multiple-choice questions automatically
4. Questions are saved to the database with a correct answer and explanation for each
5. A regular user browses available quizzes and starts an attempt
6. The user answers each question — correct answers are hidden until submission
7. On submission, the API calculates the score, percentage, and stores the result
8. The user can view detailed results including which answers were right or wrong
9. Analytics endpoints show personal performance stats, quiz history, and a leaderboard

---

## 2. Features

### User Management
- Register a new account with username, email, and password
- Login with JWT token authentication (access + refresh tokens)
- View and update your own profile (bio, email)
- Role-based system: regular users and admins have different capabilities
- Admin can promote/demote users, view all users, and delete accounts

### Quiz System
- Admin creates a quiz by specifying topic, difficulty (easy/medium/hard), and question count
- Groq AI automatically generates all multiple-choice questions with 4 options each
- Each question includes an explanation of the correct answer
- Questions are hidden from users until they submit — no cheating possible
- Quizzes support filtering by topic and difficulty
- All list endpoints are paginated (10 items per page)

### Attempt Management
- Users start a quiz attempt which is tracked as in-progress
- Only one in-progress attempt per quiz at a time per user
- Users submit all answers at once (or partially — unanswered ones default to A)
- On submission: score, percentage, and correct answers are revealed
- Attempt history is saved permanently for analytics

### Analytics
- Personal stats: total attempts, average score, best score, accuracy percentage
- Per-difficulty breakdown: how many easy/medium/hard quizzes attempted
- Per-quiz stats (admin/creator only): which questions were hardest, average score
- Global leaderboard: top 10 users ranked by average score
- Full quiz history with scores and dates

### Performance
- AI responses cached for 24 hours — same topic/difficulty won't re-call the API
- Database indexes on frequently queried fields (topic, difficulty, status, user+status)
- select_related and prefetch_related used throughout to prevent N+1 query problems
- Pagination on all list endpoints
- DRF throttling: 20 requests/hour for anonymous, 200/hour for authenticated users

---

## 3. Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Backend framework | Django 4.2 | Web framework, ORM, admin panel |
| API framework | Django REST Framework | Serializers, views, authentication |
| Authentication | SimpleJWT | JWT access and refresh tokens |
| Database | PostgreSQL | Primary database |
| AI service | Groq API (llama-3.1-8b-instant) | Quiz question generation |
| Caching | Django LocMemCache (dev) | Cache AI responses |
| CORS | django-cors-headers | Allow frontend to call the API |
| Deployment | Gunicorn + WhiteNoise | Production server and static files |

---

## 4. Project Structure

```
quiz_api_final/
│
├── manage.py                          # Django CLI entry point
├── requirements.txt                   # Python dependencies
├── Procfile                           # Deployment config for Railway/Heroku
├── .env.example                       # Environment variable template
├── README.md                          # This file
│
├── quiz_project/                      # Django project configuration
│   ├── settings.py                    # All settings: DB, auth, caching, AI, etc.
│   ├── urls.py                        # Root URL router — maps /api/* to apps
│   └── wsgi.py                        # WSGI entry point for production servers
│
└── apps/                              # All feature apps
    │
    ├── users/                         # User management app
    │   ├── models.py                  # Custom User model (extends AbstractUser)
    │   ├── serializers.py             # Register, profile, public user serializers
    │   ├── views.py                   # Register, profile, admin user management
    │   ├── permissions.py             # IsAdminUser, IsOwnerOrAdmin permission classes
    │   ├── urls.py                    # /api/users/* routes
    │   ├── admin.py                   # Django admin panel configuration
    │   ├── tests.py                   # Unit tests for auth and permissions
    │   └── management/
    │       └── commands/
    │           └── create_admin.py    # `python manage.py create_admin` command
    │
    ├── quiz/                          # Quiz and attempt management app
    │   ├── models.py                  # Quiz, Question, QuizAttempt, UserAnswer models
    │   ├── ai_service.py              # Groq AI integration, prompt building, caching
    │   ├── serializers.py             # Quiz, question, attempt, answer serializers
    │   ├── views.py                   # All quiz and attempt API views
    │   ├── urls.py                    # /api/quiz/* routes
    │   ├── admin.py                   # Django admin with inline questions
    │   └── tests.py                   # Unit tests for quiz creation and attempts
    │
    └── analytics/                     # Performance analytics app
        ├── views.py                   # Stats, leaderboard, history, admin dashboard
        ├── urls.py                    # /api/analytics/* routes
        └── tests.py                   # Unit tests for analytics endpoints
```

---

## 5. Database Schema

### Table: users

| Column | Type | Notes |
|--------|------|-------|
| id | bigint PK | Auto-generated |
| username | varchar(150) | Unique |
| email | varchar(254) | |
| password | varchar(128) | Hashed with PBKDF2 — never plain text |
| role | varchar(10) | Either 'user' or 'admin' — default 'user' |
| bio | text | Optional profile description |
| is_active | boolean | Account enabled/disabled |
| date_joined | timestamp | Auto-set on registration |
| last_login | timestamp | Updated on each login |

### Table: quizzes

| Column | Type | Notes |
|--------|------|-------|
| id | bigint PK | |
| title | varchar(255) | Display name of the quiz |
| topic | varchar(200) | Sent to AI to generate questions |
| difficulty | varchar(10) | 'easy', 'medium', or 'hard' |
| question_count | int | Between 3 and 20 |
| status | varchar(10) | 'draft' → 'ready' → 'failed' |
| created_by_id | FK → users | The admin who created it |
| created_at | timestamp | |
| updated_at | timestamp | |

### Table: questions

| Column | Type | Notes |
|--------|------|-------|
| id | bigint PK | |
| quiz_id | FK → quizzes | Which quiz this belongs to |
| question_text | text | The full question |
| option_a | varchar(500) | First choice |
| option_b | varchar(500) | Second choice |
| option_c | varchar(500) | Third choice |
| option_d | varchar(500) | Fourth choice |
| correct_option | varchar(1) | 'A', 'B', 'C', or 'D' |
| explanation | text | Shown after quiz submission |
| order | int | Position of question in quiz |

### Table: quiz_attempts

| Column | Type | Notes |
|--------|------|-------|
| id | bigint PK | |
| user_id | FK → users | Who is attempting |
| quiz_id | FK → quizzes | Which quiz |
| status | varchar(15) | 'in_progress', 'completed', 'abandoned' |
| score | int | Number of correct answers |
| score_percentage | float | 0.0 to 100.0 |
| total_questions | int | Snapshot of question count at time of attempt |
| started_at | timestamp | Auto-set when attempt created |
| completed_at | timestamp | Set when user submits |

### Table: user_answers

| Column | Type | Notes |
|--------|------|-------|
| id | bigint PK | |
| attempt_id | FK → quiz_attempts | Which attempt this belongs to |
| question_id | FK → questions | Which question was answered |
| selected_option | varchar(1) | The option the user chose: A, B, C, or D |
| is_correct | boolean | Auto-calculated in save() method |
| answered_at | timestamp | |
| UNIQUE | (attempt, question) | One answer per question per attempt |

### Relationships Diagram

```
User ──────────< QuizAttempt >────────── Quiz
                     │                    │
                     │                    │
               UserAnswer ──────────> Question
```

- One User can have many QuizAttempts
- One Quiz can have many QuizAttempts and many Questions
- One QuizAttempt has many UserAnswers
- Each UserAnswer links to one Question

---

## 6. API Endpoints

### Authentication

| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| POST | /api/users/register/ | No | Create new account |
| POST | /api/auth/login/ | No | Get access + refresh JWT tokens |
| POST | /api/auth/refresh/ | No | Get new access token using refresh token |

### User Management

| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| GET | /api/users/me/ | User | View your own profile |
| PUT/PATCH | /api/users/me/ | User | Update your profile |
| GET | /api/users/ | Admin | List all users |
| GET | /api/users/\<id\>/ | Admin | View any user |
| DELETE | /api/users/\<id\>/ | Admin | Delete a user |
| POST | /api/users/\<id\>/promote/ | Admin | Change user role |

### Quizzes

| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| GET | /api/quiz/ | User | List all ready quizzes (paginated) |
| POST | /api/quiz/ | Admin | Create quiz — AI generates questions |
| GET | /api/quiz/\<id\>/ | User | Get quiz with questions (no answers) |
| DELETE | /api/quiz/\<id\>/ | Admin | Delete a quiz |
| GET | /api/quiz/my-quizzes/ | Admin | Quizzes created by this admin |

**Query parameters for GET /api/quiz/:**
- `?topic=python` — filter by topic (case-insensitive contains)
- `?difficulty=easy` — filter by difficulty (easy/medium/hard)
- `?page=2` — pagination

### Attempts

| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| POST | /api/quiz/\<id\>/attempt/ | User | Start a new attempt |
| POST | /api/quiz/attempts/\<id\>/submit/ | Owner | Submit answers and get results |
| GET | /api/quiz/attempts/\<id\>/ | Owner/Admin | View attempt results |
| GET | /api/quiz/my-attempts/ | User | All my attempts |
| GET | /api/quiz/all-attempts/ | Admin | All attempts by all users |

### Analytics

| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| GET | /api/analytics/me/ | User | Your overall performance stats |
| GET | /api/analytics/history/ | User | Your completed quiz history |
| GET | /api/analytics/leaderboard/ | User | Top 10 users by average score |
| GET | /api/analytics/quiz/\<id\>/ | Owner/Admin | Stats for a specific quiz |
| GET | /api/analytics/admin/dashboard/ | Admin | Platform-wide statistics |

---

## 7. Authentication System

This API uses **JWT (JSON Web Tokens)** for authentication.

### How it works

**Step 1 — Register:**
```
POST /api/users/register/
Body: { "username": "alice", "email": "alice@example.com", "password": "SecurePass123!", "password_confirm": "SecurePass123!" }
```

**Step 2 — Login:**
```
POST /api/auth/login/
Body: { "username": "alice", "password": "SecurePass123!" }
Response: { "access": "eyJ...", "refresh": "eyJ..." }
```

**Step 3 — Use the access token in every request:**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Step 4 — Refresh when expired (access token lasts 1 hour):**
```
POST /api/auth/refresh/
Body: { "refresh": "eyJ..." }
Response: { "access": "eyJ..." }  ← new access token
```

### Token Lifetimes
- Access token: **1 hour** — used in every API request
- Refresh token: **7 days** — used only to get a new access token

---

## 8. AI Integration

### How quiz generation works

When an admin sends `POST /api/quiz/` with a topic, difficulty, and count:

1. The quiz is saved to the database with `status = "draft"`
2. `ai_service.py` builds a detailed prompt asking Groq to generate exactly N questions in JSON format
3. The prompt instructs Groq to return ONLY a JSON array — no markdown, no explanation
4. The API calls Groq's `llama-3.1-8b-instant` model
5. The JSON response is parsed and each question is validated
6. Valid questions are saved to the database using `bulk_create` (one DB query)
7. The quiz status is updated to `"ready"`
8. The full quiz with questions is returned to the caller

### Error handling

| Scenario | What happens |
|----------|-------------|
| AI timeout (>60 seconds) | Returns 503 with "AI service timed out" |
| Rate limit (429) | Returns 503 with "please wait and try again" |
| Invalid API key (401) | Returns 503 with configuration error message |
| Bad JSON from AI | Attempts to extract JSON from the response, fails gracefully |
| No valid questions | Returns 503 and marks quiz as "failed" |
| Quiz marked failed | Status saved in DB so admin can see which quizzes failed |

### Caching

AI responses are cached for **24 hours** using the key format:
```
ai_quiz_{topic}_{difficulty}_{count}
```

For example: `ai_quiz_python_programming_easy_5`

This means if two admins both create a Python/easy/5 quiz, only the first call hits the AI. The second gets the cached result instantly and for free.

### AI Service (Groq)

We use **Groq** (https://console.groq.com) with the `llama-3.1-8b-instant` model.

Why Groq:
- Completely free tier with generous limits
- Very fast response times (under 3 seconds usually)
- Returns reliable JSON when prompted correctly
- No credit card required

---

## 9. Role-Based Permissions

There are two roles: `user` (default) and `admin`.

### What each role can do

| Action | User | Admin |
|--------|------|-------|
| Register / Login | ✅ | ✅ |
| View own profile | ✅ | ✅ |
| Update own profile | ✅ | ✅ |
| Browse quizzes | ✅ | ✅ |
| **Create a quiz** | ❌ | ✅ |
| **Delete a quiz** | ❌ | ✅ |
| **Attempt a quiz** | ✅ | ❌ |
| View own attempt results | ✅ | ✅ |
| View analytics and leaderboard | ✅ | ✅ |
| View quiz stats (creator) | ❌ | ✅ |
| View all users | ❌ | ✅ |
| Promote/demote users | ❌ | ✅ |
| Admin dashboard | ❌ | ✅ |

### Custom Permission Classes (apps/users/permissions.py)

**IsAdminUser** — Only allows users whose `role == "admin"`. Returns 403 for regular users.

**IsOwnerOrAdmin** — Object-level permission. Allows access if the user owns the object (e.g. their own attempt) OR is an admin.

---

## 10. Caching Strategy

### Current setup (development)
Django's `LocMemCache` — stores cache in the Python process memory. Fast, zero setup required, but does not persist across server restarts and does not work across multiple processes.

### What is cached
- AI-generated questions: cached for 24 hours by topic + difficulty + count
- This prevents hitting the AI API repeatedly for the same quiz configuration

### Production upgrade path
Replace `LocMemCache` with Redis by installing `django-redis` and updating `settings.py`:
```python
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
    }
}
```
Redis works across multiple processes and persists through server restarts.

---

## 11. Local Setup Instructions

### Prerequisites
- Python 3.11 or newer
- PostgreSQL (running locally)
- A free Groq API key from https://console.groq.com/keys

### Step 1 — Get the code
Download and extract the project zip, then open the folder in VS Code.

### Step 2 — Create a virtual environment
```bash
python -m venv venv

# Activate on Windows:
venv\Scripts\activate

# Activate on Mac/Linux:
source venv/bin/activate
```

### Step 3 — Install dependencies
```bash
pip install -r requirements.txt
```

### Step 4 — Create the database
Open pgAdmin or psql and run:
```sql
CREATE DATABASE quiz_db;
```

### Step 5 — Set up environment variables
Copy `.env.example` to `.env` and fill in your values:
```
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/quiz_db
```

Then open `quiz_project/settings.py` and set your Groq key directly at the bottom:
```python
GEMINI_API_KEY = "gsk_your_groq_key_here"
GEMINI_API_URL = "https://api.groq.com/openai/v1/chat/completions"
```

### Step 6 — Run migrations
```bash
python manage.py migrate
```

This creates all database tables automatically.

### Step 7 — Create an admin user
```bash
python manage.py create_admin
```

This creates:
- Username: `admin`
- Password: `Admin123!`
- Role: admin

**Change the password in production!**

### Step 8 — Start the server
```bash
python manage.py runserver
```

The API is now available at `http://localhost:8000`

### Step 9 — Test with the frontend
Open `quiz_frontend_clean.html` in your browser. Sign in with:
- `admin` / `Admin123!` to create quizzes
- Any registered user to attempt quizzes

---

## 12. Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| SECRET_KEY | Yes | Django secret key for signing tokens. Generate at https://djecrety.ir |
| DEBUG | Yes | Set to `True` in development, `False` in production |
| ALLOWED_HOSTS | Yes | Comma-separated list of allowed hostnames |
| DATABASE_URL | Yes | PostgreSQL connection string |
| GEMINI_API_KEY | Yes | Your Groq API key (starts with `gsk_`) |
| CORS_ALLOWED_ORIGINS | Production only | Frontend URL(s) allowed to call the API |

---

## 13. Running Tests

```bash
# Run all tests
python manage.py test

# Run tests for a specific app
python manage.py test apps.users
python manage.py test apps.quiz
python manage.py test apps.analytics
```

### What is tested

**Users app (10 tests):**
- Successful registration
- Password mismatch validation
- Duplicate username rejection
- Missing required fields
- Successful login
- Wrong password rejection
- Profile requires authentication
- Authenticated profile access
- Regular user cannot access admin endpoints
- Admin can access admin endpoints

**Quiz app (11 tests):**
- Quiz creation success (AI mocked)
- AI failure marks quiz as failed
- Invalid question count rejected
- Unauthenticated quiz creation rejected
- Correct answers hidden before submission
- Attempt start success
- Duplicate attempt returns existing
- Draft quiz cannot be attempted
- All correct answers = 100% score
- All wrong answers = 0% score
- Submission reveals correct answers
- Cannot submit completed attempt twice
- Wrong question ID rejected
- Another user cannot submit your attempt

**Analytics app (5 tests):**
- Zero stats for new user
- Stats update after completed attempt
- Leaderboard accessible to authenticated users
- Leaderboard requires authentication
- Admin dashboard blocked for regular users
- Admin dashboard accessible for admin users

### Note on AI tests
The quiz creation tests use `unittest.mock.patch` to replace the real `generate_questions` function with a fake one. This means tests run instantly without needing a real Groq API key.

---

## 14. Frontend

A single-file HTML frontend (`quiz_frontend_clean.html`) is included. It connects directly to `http://localhost:8000/api`.

### Pages

**Login / Register** — JWT token is stored in localStorage. Switching tabs between login and register is smooth. Error messages are shown for wrong credentials, duplicate usernames, and weak passwords.

**Dashboard** — Shows your personal stats (attempts, average score, best score, accuracy) at the top. Below that is a filterable table of all available quizzes. Admins see an additional "Create a quiz" panel with AI generation.

**Take a Quiz** — Question-by-question interface with a progress bar, dot navigation (click any dot to jump to that question), and A/B/C/D option buttons. Users can go back and change answers before submitting.

**Results** — Score ring shows percentage with colour coding (green = good, blue = ok, red = needs work). Full question breakdown shows which answers were right/wrong and the explanation for each.

**Analytics** — Personal stats grid, global leaderboard with medal emojis for top 3, and full quiz history with dates and scores.

### How it connects to the backend
All API calls use `fetch()` with the JWT token in the `Authorization: Bearer` header. The base URL `http://localhost:8000/api` is defined at the top of the script — change this to your deployed URL when going to production.

---

## 15. Design Decisions and Trade-offs

### Custom User Model instead of separate Profile model
We extend Django's `AbstractUser` directly with a `role` field and `bio` field. This is simpler than a separate `Profile` model and avoids extra JOIN queries every time you need user data. The trade-off is that it must be set up before the first migration — changing it later is complex.

### Quiz status: draft → ready → failed
Instead of creating the quiz only after AI succeeds, we save it immediately as "draft" and update the status after AI generation. This means:
- The quiz ID is generated immediately (useful for tracking)
- Failed quizzes are visible in the admin panel for debugging
- Users never see draft or failed quizzes (only "ready" ones are listed)

### Storing is_correct on UserAnswer
We calculate and store whether each answer is correct at the moment of saving, rather than calculating it on every analytics query. This denormalization makes analytics queries significantly faster — no need to join questions to check answers every time stats are requested.

### JWT instead of session authentication
JWT is stateless — the server does not need to store session data. This makes the API easier to scale horizontally (multiple servers) and works naturally with mobile apps and frontend SPAs.

### Answers hidden until submission
The `QuestionSerializer` (used for listing questions) deliberately excludes `correct_option` and `explanation`. The `QuestionWithAnswerSerializer` (used in results) includes them. This is enforced at the serializer level, not just the view level.

### select_related and prefetch_related throughout
Every view that accesses related objects uses these Django ORM optimizations:
- `select_related("quiz", "user")` on attempts — single SQL JOIN instead of N+1 queries
- `prefetch_related("questions")` on quiz detail — fetches all questions in one query
- `prefetch_related("answers__question")` on attempt detail — single query for all answers with their questions

---

## 16. Challenges and Solutions

### Challenge 1: AI API rate limits
During development, Gemini and OpenRouter API keys hit rate limits quickly because we were testing many times. 

**Solution:** Switched to Groq which has a more generous free tier. Also implemented a 24-hour cache so repeated requests for the same topic do not hit the API at all.

### Challenge 2: AI returning inconsistent JSON
Language models sometimes add markdown code blocks (```json), extra explanations, or use different field names than expected.

**Solution:** The prompt is very explicit about returning ONLY a JSON array. The parser also handles markdown code blocks by stripping ``` wrappers. Each question is individually validated — questions missing required fields or with invalid `correct_option` values are silently skipped.

### Challenge 3: Custom User model must be set before migrations
Django requires you to declare a custom user model before running the first migration. If you try to add it after migrations already exist, it causes errors.

**Solution:** The custom user model was set up as the very first thing in the project before any migrations were run. The migration file is included in the repository so setup is straightforward.

### Challenge 4: Preventing N+1 database queries
Without optimization, loading a list of quiz attempts would trigger a separate database query for each attempt's quiz title and user.

**Solution:** Used `select_related` on all views that access FK relationships, and `prefetch_related` for reverse FK relationships. This reduces multiple queries to a single JOIN.

### Challenge 5: CORS for the frontend
When the frontend HTML file opens in the browser as a `file://` URL and tries to call `http://localhost:8000`, the browser blocks it as a CORS violation by default.

**Solution:** `django-cors-headers` is installed and configured with `CORS_ALLOW_ALL_ORIGINS = True` in development mode. This allows the standalone HTML file to communicate with the API without issues.
