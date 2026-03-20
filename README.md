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

## Local Setup Instructions

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
