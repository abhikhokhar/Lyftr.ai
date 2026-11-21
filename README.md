
# Lyftr AI — LLM Chatbot with Key Failover and Response Caching

Lyftr AI is a full-stack AI chatbot built using React, FastAPI, LiteLLM, and SQLAlchemy. It supports multi-turn conversations, automatic LLM API key failover, response caching, per-message token tracking, and persistent chat history.

The application is designed to remain reliable even when an LLM provider encounters rate limits, quota errors, or server failures.

## 1. Live URLs

| Component | URL |
|---|---|
| Frontend | https://lyftr-ai.abhikhokhar.com |
| Backend API | https://lyftr-ai-roq0.onrender.com |
| API Health Check | https://lyftr-ai-roq0.onrender.com/health |
| API Documentation | https://lyftr-ai-roq0.onrender.com/docs |
| GitHub Repository | https://github.com/abhikhokhar/Lyftr.ai |

**Note:** The backend is hosted on Render's free instance, which may spin down after inactivity. The first request after inactivity can take longer.

## 2. Run Locally

### Prerequisites

- Python 3.12+
- Node.js 22+
- npm
- Docker Desktop (for containerized execution)
- Two valid LLM API keys

### A. Environment Configuration

Create a `.env` file inside the `backend/` directory.

```env
LLM_API_KEYS=your_first_api_key,your_second_api_key

MODEL_NAME=gemini/gemini-3.1-flash-lite

DATABASE_URL=sqlite:///./lyftr.db

ENABLE_FAILURE_SIMULATION=true

ALLOWED_ORIGINS=http://localhost:5173
```

Replace the API key placeholders with your actual API keys. Never commit API keys or `.env` files to GitHub.

### B. Run Without Docker

**Step 1: Start the backend**

```bash
cd backend

python -m venv .venv
```

Activate the virtual environment:

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start FastAPI:

```bash
uvicorn app.main:app --reload
```

Backend runs at:

http://localhost:8000

API documentation:

http://localhost:8000/docs

**Step 2: Start the frontend**

Open another terminal:

```bash
cd frontend

npm install
npm run dev
```

Frontend runs at:

http://localhost:5173

### C. Run With Docker

Make sure Docker Desktop is running.

From the project root:

```bash
docker compose up --build -d
```

The application will be available at:

- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- API documentation: http://localhost:8000/docs

To stop the application:

```bash
docker compose down
```

To view container logs:

```bash
docker compose logs -f
```

The Docker Compose configuration uses a named volume to persist the SQLite database across container restarts.

## 3. Design Decisions

### A. Automatic API Key Failover

Lyftr AI supports multiple LLM API keys to improve reliability.

The backend attempts API keys sequentially:

1. The first API key is used for the initial request.
2. If the provider returns an error, the next configured key is attempted.
3. This process continues until a key succeeds.
4. If all configured keys fail, the backend returns HTTP 503.

Supported failure scenarios include rate limits (429), quota errors, and server errors (5xx).

The `X-Simulate-Failure` header allows failures to be tested without intentionally exhausting API quotas.

Examples:

```http
X-Simulate-Failure: key_1=429
```

Simulates a rate-limit error for the first key.

```http
X-Simulate-Failure: key_1=500,key_2=429
```

Simulates failures for both configured keys.

```http
X-Simulate-Failure: *=429
```

Simulates a rate-limit error for every configured key.

The simulation feature can be enabled or disabled using:

```env
ENABLE_FAILURE_SIMULATION=true
```

API keys are never returned in API responses or exposed in error messages.

### B. Response Caching with LiteLLM

LiteLLM's built-in caching mechanism is used to avoid unnecessary repeated LLM API calls.

```python
litellm.cache = litellm.Cache(type="local")
```

When an identical request is received, LiteLLM can return the previously generated response instead of making another provider call.

Every assistant response includes a `resolution_source` field:

| Value | Meaning |
|---|---|
| `LIVE_INFERENCE` | Response generated through an LLM provider |
| `LLM_CACHE` | Response returned from LiteLLM cache |

The frontend displays the response source, model, latency, input tokens, and output tokens.

Caching is disabled for simulated-failure requests so that failure scenarios can be tested accurately.

### C. Database and Session Storage

SQLAlchemy is used as the database abstraction layer.

**Local development and Docker**

SQLite is used for storing conversations, messages, and usage records.

```env
DATABASE_URL=sqlite:///./lyftr.db
```

Docker uses a persistent named volume for SQLite storage.

**Production deployment**

The deployed backend uses Neon PostgreSQL.

```env
DATABASE_URL=your_neon_postgresql_connection_string
```

PostgreSQL was selected for the hosted environment because it is better suited to concurrent requests, managed cloud database hosting, and production workloads.

The same SQLAlchemy models and database operations are used across both environments, allowing the database to be configured through an environment variable.

### D. Multi-Turn Conversation Management

Each conversation is associated with a unique session ID.

For every new message:

1. The backend retrieves the previous messages belonging to that session.
2. The recent conversation history is included in the LLM prompt.
3. The assistant generates a context-aware response.
4. Both user and assistant messages are saved in the database.
5. Usage metadata is stored with the assistant message.

The application limits the LLM context to the latest 20 stored messages.

Separate session IDs maintain separate conversation histories.

### E. Per-Message Usage Metadata

Each assistant response includes:

| Field | Description |
|---|---|
| `resolution_source` | Whether the response came from cache or live inference |
| `model` | LLM model used |
| `latency_ms` | Response generation time in milliseconds |
| `input_tokens` | Number of prompt tokens |
| `output_tokens` | Number of generated tokens |
| `key_id` | API key identifier used |
| `fallback_attempts` | Number of previous keys that failed |
| `cache_hit` | Whether the response was served from cache |

The frontend displays this information alongside each AI response.

## 4. Verification

The project includes automated tests using pytest and FastAPI's TestClient.

The test suite covers schema validation, API behavior, LLM failover, caching metadata, simulated failures, conversation persistence, and multi-turn context.

Run the tests from the backend directory:

```bash
python -m pytest -v
```

**Latest local test result: 23 tests passed.**

### A. Health Check

Request:

```http
GET /health
```

Example response:

```json
{
  "status": "ok",
  "keys_configured": 2,
  "cache_enabled": true
}
```

### B. Chat Request

Request:

```http
POST /chat
Content-Type: application/json
```

Example body:

```json
{
  "session_id": "session-123",
  "message": "Explain what an API is."
}
```

The response contains the generated reply and its usage metadata.

### C. Retrieve Conversation History

Request:

```http
GET /sessions/session-123/messages
```

This endpoint returns the messages stored for the specified session, including assistant response metadata.

### D. Verify Key Failover

Send a chat request with:

```http
X-Simulate-Failure: key_1=429
```

Verify that the backend attempts the next configured key and returns a successful response if that key works.

If all keys fail:

```http
X-Simulate-Failure: *=429
```

The expected response is HTTP 503 with a clean error message.

### E. Verify Cache Hits

1. Send the same request twice with identical session context and message.
2. Check the metadata returned with each response.
3. Verify that the second eligible request can return `LLM_CACHE`.
4. Compare latency to observe the benefit of caching.

### F. Verify Token Usage

Check the metadata for each assistant response in the frontend.

Input and output tokens are displayed separately for every response.

## 5. Setup Used

### Technology Stack

| Layer | Technologies |
|---|---|
| Frontend | React, Vite, Tailwind CSS |
| Backend | Python, FastAPI |
| LLM Integration | LiteLLM, Gemini |
| ORM | SQLAlchemy |
| Local Database | SQLite |
| Production Database | Neon PostgreSQL |
| Caching | LiteLLM built-in cache |
| Testing | Pytest, FastAPI TestClient |
| Containerization | Docker, Docker Compose |
| Backend Hosting | Render |
| Frontend Hosting | Vercel |
| Version Control | Git, GitHub |

### Development Tools

- Visual Studio Code
- Git and GitHub
- Docker Desktop
- Postman / FastAPI Swagger UI
- Python virtual environment
- AI-assisted development tools

### Project Structure

```text
Lyftr.ai/
│
├── backend/
│   ├── app/
│   │   ├── routes/
│   │   │   ├── chat.py
│   │   │   ├── health.py
│   │   │   ├── cache.py
│   │   │   └── analytics.py
│   │   │
│   │   ├── services/
│   │   │   ├── chat_service.py
│   │   │   ├── llm_service.py
│   │   │   └── cache_service.py
│   │   │
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   └── main.py
│   │
│   ├── tests/
│   │   ├── test_api.py
│   │   ├── test_chat_service.py
│   │   ├── test_llm_service.py
│   │   └── test_schemas.py
│   │
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env
│
├── frontend/
│   ├── src/
│   ├── public/
│   ├── Dockerfile
│   ├── nginx.conf
│   └── package.json
│
├── docker-compose.yml
├── .dockerignore
└── README.md
```

## 6. Bonus Features

In addition to the core requirements, the following features have been implemented:

- **Custom domain:** The frontend is accessible through a custom domain.
- **Production deployment:** Frontend and backend are deployed separately using Vercel and Render.
- **Managed PostgreSQL:** Neon PostgreSQL is used for production database hosting.
- **Usage metadata:** Each assistant response displays token consumption, latency, model, cache status, and fallback information.
- **Persistent conversation history:** Messages and their metadata are stored and can be retrieved using the session history API.
- **Failure simulation:** Custom request headers allow testing of API key failures without consuming provider quota.
- **Containerized deployment:** Multi-stage Dockerfiles and Docker Compose simplify local deployment.
- **Automated tests:** A pytest suite verifies the main backend functionality.

---

