# EdHub360 Backend

Python microservices powering the EdHub360 learning platform, deployed on Google Cloud Run.

## Services

| Service | Port (local) | Description |
|---|---|---|
| `login` | 8001 | Auth — Google, Microsoft, Facebook OAuth + JWT |
| `subscription` | — | Stripe billing and plan management |
| `ai_chat` | — | AI conversational assistant |
| `flashcard` | — | Flashcard deck management |
| `quiz` | — | Quiz generation |
| `notebook` | — | Notes / notebook |
| `study_planner` | — | Study schedule |
| `cs_bot` | — | CS-specific Q&A bot |
| `courses` | — | Course catalogue |

## Tech Stack

- **Framework**: FastAPI (async)
- **ORM**: SQLAlchemy 2.0 (async) + asyncpg
- **Database**: PostgreSQL (Cloud SQL on GCP)
- **Auth**: JWT (python-jose), bcrypt, OAuth via provider APIs
- **Payments**: Stripe
- **Deployment**: Docker → Google Artifact Registry → Cloud Run
- **CI/CD**: Google Cloud Build

## Local Development — Login Service

```bash
cd Backend/login

# Create and activate virtualenv
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

pip install -r app/requirements.txt   # or requirements.txt at service root
```

Create `Backend/login/.env` (never commit):

```env
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/studenthub
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30

GOOGLE_CLIENT_ID=your-google-client-id

FACEBOOK_APP_ID=your-facebook-app-id
FACEBOOK_APP_SECRET=your-facebook-app-secret

BCRYPT_ROUNDS=12
RATE_LIMIT_REQUESTS=5
DEBUG=true

CORS_ORIGINS=["http://localhost:5173","https://localhost:5173"]

FRONTEND_BASE_URL=https://localhost:5173/StudentHub

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your-email@gmail.com
SMTP_FROM_NAME=EdHub360
```

```bash
uvicorn app.main:app --reload --port 8001
```

API docs available at `http://localhost:8001/docs`.

## Auth Flow

All OAuth providers follow the same pattern:

1. Frontend obtains an access token from the provider (Google/Microsoft/Facebook)
2. Token is POSTed to `/auth/{provider}`
3. Backend verifies the token against the provider's API (userinfo / Graph API)
4. User is created or updated in the database
5. JWT access token + refresh token are returned

### Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/auth/google` | Google Sign-In |
| POST | `/auth/microsoft` | Microsoft Sign-In |
| POST | `/auth/facebook` | Facebook Sign-In |
| POST | `/auth/login` | Email/password login |
| POST | `/auth/register` | Email/password registration |
| POST | `/auth/refresh` | Rotate refresh token |
| POST | `/auth/logout` | Revoke refresh token |
| GET | `/auth/session/check` | Validate session (lightweight) |
| GET | `/auth/me` | Current user profile |
| POST | `/auth/forgot-password` | Send password reset email |
| POST | `/auth/reset-password` | Apply password reset |

## Subscription Service

Manages Stripe billing. Deployed separately on Cloud Run.

Key endpoints: `/plans`, `/checkout`, `/subscriptions/{user_id}`, `/webhooks/stripe`

Free plan uses a $0 Stripe subscription. Expiry after 7 days is handled by the built-in APScheduler job, not Stripe trial settings.

## Deployment

Each service has its own `Dockerfile` and `cloudbuild.yaml`. Cloud Build builds the Docker image, pushes to Artifact Registry, and deploys to Cloud Run with secrets sourced from Secret Manager.

```bash
# Trigger manually (requires gcloud auth)
gcloud builds submit --config Backend/subscription/cloudbuild.yaml Backend/
```

## Security Notes

- `.env` files are git-ignored — never commit secrets
- The Facebook `appsecret_proof` (HMAC-SHA256) is sent with every Graph API call to prevent token replay attacks
- Refresh tokens are stored as SHA-256 hashes; the raw token only exists in transit
- New login revokes all previous sessions for the same user
