# DigiGates

Interactive digital-logic learning and circuit exploration using the approved stack: React/HTML/CSS/JavaScript, SVG, Web Speech APIs, FastAPI, Pydantic, and MySQL.

## Run locally

1. Create a MySQL database: `CREATE DATABASE digigates CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;`
2. Backend:
   - `cd backend`
   - `python -m venv .venv`
   - `.venv\Scripts\activate` (Windows) or `source .venv/bin/activate`
   - `pip install -r requirements.txt`
   - Copy `.env.example` to `.env` and set secrets/database URL.
   - `uvicorn app.main:app --reload --port 8000`
3. Frontend:
   - `cd frontend`
   - `npm install`
   - Copy `.env.example` to `.env` if the API is not on port 8000.
   - `npm run dev`

The first registered account can be promoted with `UPDATE users SET role='admin' WHERE email='you@example.com';`.

## Tests

- Backend: `cd backend && pytest`
- Frontend: `cd frontend && npm test -- --run`
- Production build: `cd frontend && npm run build`

