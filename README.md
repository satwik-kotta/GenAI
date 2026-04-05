# AI Planner Agent (FastAPI + Gemini + APIs)

We built a modular AI agent using FastAPI where Gemini handles intent extraction, APIs provide real-time context, and the system executes decisions by directly integrating with Google Calendar.

## 1) Project Structure

```text
project/
├── app/
│   ├── main.py
│   ├── routes/
│   │   └── planner.py
│   ├── services/
│   │   ├── llm.py
│   │   ├── weather.py
│   │   ├── places.py
│   │   ├── calendar.py
│   │   └── logic.py
│   ├── models/
│   │   └── schemas.py
│   └── utils/
│       └── config.py
├── credentials.json
├── requirements.txt
└── README.md
```

## 2) Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy env template and add real values:

```bash
cp .env.example .env
```

4. Create Google OAuth desktop credentials and put values in `credentials.json`.

## 3) Run API

```bash
uvicorn app.main:app --reload
```

Open docs at `http://127.0.0.1:8000/docs`.

## 3) Frontend Integration

This backend is CORS-enabled for React development servers on ports 3000 and 5173 by default.

### Main API Surface

- `GET /health` - server health check
- `GET /api/v1` - API info and endpoint list
- `POST /api/v1/auth/google` - sign in using Google ID token
- `GET /api/v1/auth/me` - fetch current signed-in user
- `POST /api/v1/intent/parse` - parse user text into structured intent
- `POST /api/v1/weather/current` - get current weather for a city
- `POST /api/v1/places/search` - search nearby places for a query
- `POST /api/v1/plan/preview` - build a plan without creating a calendar event
- `POST /api/v1/plan/execute` - build a plan and create a Google Calendar event (auth required)
- `POST /api/v1/calendar/events` - create a calendar event directly (auth required)
- `GET /api/v1/plans/history` - fetch signed-in user's saved plan history

### Recommended React Flow

1. Sign in with Google and send ID token to `POST /api/v1/auth/google`.
2. Store returned bearer token in frontend local storage.
3. Call `POST /api/v1/intent/parse` when the user submits a prompt.
4. Call `POST /api/v1/plan/preview` to show weather, activity choice, time window, and place options.
5. Call `POST /api/v1/plan/execute` with bearer token when the user confirms the plan.
6. Show prior plans from `GET /api/v1/plans/history`.

## 4) React Frontend

The React app lives in `frontend/` and is built with Vite.

### Setup

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open the UI at `http://127.0.0.1:5173`.

Set these values in `frontend/.env`:

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
VITE_GOOGLE_CLIENT_ID=your_google_oauth_client_id
```

### Build

```bash
cd frontend
npm run build
```

## 5) Test Input

Use this sample payload on `POST /api/v1/plan/execute`:

```json
{
  "user_input": "I want to go hiking this weekend but only if it is not raining, otherwise suggest something indoors and block 10 to 2",
  "city": "Mumbai"
}
```

## 6) Step-by-Step Progression

- Step 1: FastAPI setup in `app/main.py` and route registration.
- Step 2: Gemini parsing in `app/services/llm.py` with strict JSON extraction.
- Step 3: Weather status via OpenWeather in `app/services/weather.py`.
- Step 4: Decision engine in `app/services/logic.py`.
- Step 5: Places lookup and ranking in `app/services/places.py`.
- Step 6: Google Calendar creation in `app/services/calendar.py`.
- Step 7: End-to-end orchestration in `app/routes/planner.py`.

## 6) Next Enhancements

- Harden Gemini JSON parsing with retries and schema validation.
- Improve natural language date parsing for specific dates.
- Add place selection rules (distance + rating + open now).
- Add unit tests and API integration tests.

## 7) Database

- SQLite file: `planner.db`
- Tables: `users`, `session_tokens`, `plan_history`
- DB is auto-initialized on API startup
