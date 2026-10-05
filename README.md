# DigiGates

DigiGates is an interactive digital logic learning application developed for the CS4431 Human-Computer Interaction project.

The application provides three main learning environments:

- **Learn** — learn digital logic concepts and practise individual logic gates.
- **Explore** — interact with predefined digital circuits.
- **Build** — construct and simulate digital circuits.

React/JavaScript performs real-time circuit simulation in the browser. FastAPI, Pydantic, SQLAlchemy, and MySQL provide the backend and persistent application data.

Switch evaluation, signal propagation, LEDs, Boolean expressions, and truth-table highlighting remain frontend-side.

---

## Technology Stack

### Frontend

- React
- JavaScript
- Vite
- HTML/CSS
- SVG

### Backend

- Python 3.11+
- FastAPI
- Pydantic
- SQLAlchemy
- Alembic
- PyMySQL

### Database

- MySQL 8+
- Aiven MySQL is used for the shared project database.

---

## Project Structure

```text
DigiGates/
├── backend/
│   ├── alembic/
│   ├── app/
│   ├── tests/
│   ├── .env.example
│   ├── alembic.ini
│   ├── requirements.txt
│   └── schema.sql
│
├── frontend/
│   ├── src/
│   ├── .env.example
│   ├── package.json
│   └── package-lock.json
│
├── Certificates/
├── .gitignore
└── README.md
```

---

# Getting Started

## 1. Prerequisites

Install the following before setting up DigiGates:

- Git
- Python 3.11 or later
- Node.js
- npm

The project also requires access to the DigiGates MySQL database.

> Do not commit database passwords, secret keys, certificates containing private credentials, or other secrets to Git.

---

## 2. Clone the Repository

```bash
git clone <repository-url>
cd DigiGates
```

Replace `<repository-url>` with the DigiGates GitHub repository URL.

---

# Backend Setup

## 3. Create a Python Virtual Environment

The backend should run inside its own Python virtual environment.

### Windows — Command Prompt

```cmd
cd backend
py -3.11 -m venv .venv
.venv\Scripts\activate.bat
```

If the Python launcher is unavailable but Python 3.11 is installed:

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

Verify:

```cmd
python --version
where python
```

### Windows — PowerShell

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Verify:

```powershell
python --version
Get-Command python
```

### Linux

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
```

Verify:

```bash
python --version
which python
```

---

## 4. Install Backend Dependencies

With the virtual environment activated:

### Windows and Linux

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

---

# Database Configuration

DigiGates uses MySQL for persistent application data.

The shared project environment uses Aiven MySQL. Each team member must configure their local backend with the approved project database credentials.

## 5. Create the Backend Environment File

Never commit the real `.env` file.

### Windows — Command Prompt

```cmd
copy .env.example .env
```

### Windows — PowerShell

```powershell
Copy-Item .env.example .env
```

### Linux

```bash
cp .env.example .env
```

Then configure the values required by `backend/.env.example`, including:

```text
MYSQL_HOST=
MYSQL_PORT=
MYSQL_DATABASE=
MYSQL_USER=
MYSQL_PASSWORD=

SECRET_KEY=
ACCESS_TOKEN_MINUTES=
FRONTEND_ORIGIN=
SQL_ECHO=
```

Use the DigiGates team's approved Aiven connection details.

Do not place real passwords or secret keys in this README.

---

## Optional Local MySQL Development

A local MySQL 8+ database may also be used for isolated development.

From an administrative MySQL session:

```sql
CREATE DATABASE digigates
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

CREATE USER 'digigates_app'@'localhost'
    IDENTIFIED BY 'choose-a-local-password';

GRANT SELECT, INSERT, UPDATE, DELETE,
      CREATE, ALTER, INDEX, DROP, REFERENCES
ON digigates.*
TO 'digigates_app'@'localhost';

FLUSH PRIVILEGES;
```

Configure `backend/.env` to use the local database instead of Aiven.

---

# Database Migrations

DigiGates uses Alembic to manage database schema migrations.

Before applying migrations to the shared Aiven database, confirm that you are using the correct database and that the migration has not already been applied.

To apply pending migrations:

```bash
alembic upgrade head
```

Do not reset, drop, or recreate the shared database unless the team has explicitly agreed to do so.

---

# Seed Data

The backend provides seed data for the supported logic gates.

Run:

```bash
python -m app.seed
```

The seed operation idempotently inserts:

- BUFFER
- NOT
- AND
- OR
- NAND
- NOR
- XOR
- XNOR

It does not create an administrator with a hardcoded password.

For local development, register an account normally and deliberately promote the selected account when administrator access is required.

Example:

```sql
UPDATE users
SET role = 'ADMIN'
WHERE email = 'your-admin@example.com';
```

---

# Run the Backend

From `DigiGates/backend`, with `.venv` activated:

```bash
python -m uvicorn app.main:app --reload --port 8000
```

A successful startup should include:

```text
Uvicorn running on http://127.0.0.1:8000
Application startup complete.
```

Backend API:

```text
http://127.0.0.1:8000
```

Interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

> Opening `http://127.0.0.1:8000/` may return `{"detail":"Not Found"}` because DigiGates does not currently require a `GET /` route. This does not mean the backend has failed.

Keep the backend terminal running while using DigiGates.

---

# Frontend Setup

Open a second terminal.

## 6. Install Frontend Dependencies

### Windows

```cmd
cd frontend
npm install
```

### Linux

```bash
cd frontend
npm install
```

---

## 7. Configure the Frontend

If frontend environment configuration is required, create it from the example file.

### Windows — Command Prompt

```cmd
copy .env.example .env
```

### Windows — PowerShell

```powershell
Copy-Item .env.example .env
```

### Linux

```bash
cp .env.example .env
```

Configure the values according to `frontend/.env.example`.

---

# Run the Frontend

```bash
npm run dev
```

Vite will display the local development URL in the terminal.

Open the exact `Local` URL reported by Vite in your browser.

The frontend and backend should run simultaneously in separate terminals.

---

# Tests

## Backend Tests

Activate the backend virtual environment first.

Run the circuit-validation tests:

```bash
pytest -q tests/test_circuit_validation.py
```

MySQL integration tests must use a dedicated disposable test database.

Never run destructive integration tests against development or production data.

Example:

```sql
CREATE DATABASE digigates_test
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

GRANT ALL PRIVILEGES
ON digigates_test.*
TO 'digigates_app'@'localhost';
```

### Windows — PowerShell

```powershell
$env:DIGIGATES_TEST_MYSQL='1'
$env:MYSQL_DATABASE='digigates_test'
pytest -q
```

### Windows — Command Prompt

```cmd
set DIGIGATES_TEST_MYSQL=1
set MYSQL_DATABASE=digigates_test
pytest -q
```

### Linux

```bash
export DIGIGATES_TEST_MYSQL=1
export MYSQL_DATABASE=digigates_test
pytest -q
```

---

## Frontend Verification

From `frontend`:

```bash
npm test -- --run
npm run build
```

---

# API

## Authentication

```text
POST /api/auth/register
POST /api/auth/login
GET  /api/auth/me
```

## Administrator Resources

Administrator-only list, view, add, update, and delete operations are provided for:

```text
/api/admin/logic-gates
/api/admin/lessons
/api/admin/prebuilt-circuits
/api/admin/exercises
```

## Learner APIs

```text
GET                  /api/lessons
GET                  /api/prebuilt-circuits
POST | GET           /api/saved-circuits
GET | PUT | DELETE   /api/saved-circuits/{id}
PUT | GET            /api/progress
POST                 /api/exercise-attempts
```

Circuit JSON is versioned and documented by `CircuitDefinition` in:

```text
backend/app/schemas.py
```

API validation covers:

- variable uniqueness
- A–Z variable labels
- four-box maximum
- gate types and arity
- row and column bounds
- adjacent rows
- source existence
- unique input positions
- forward-only dependencies

Validation occurs before circuit data is persisted to MySQL.

---

# Development Workflow

When working on DigiGates:

1. Pull the latest changes from Git.
2. Activate the backend `.venv`.
3. Start the FastAPI backend.
4. Start the React/Vite frontend in a second terminal.
5. Make and test changes.
6. Run relevant backend and frontend tests.
7. Review changed files.
8. Commit only source code and safe configuration examples.
9. Never commit `.env` files or credentials.
10. Push the tested changes to the shared repository.

---

# Troubleshooting

## Wrong Python Interpreter on Windows

Check:

```cmd
where python
python --version
```

When the backend virtual environment is activated, the first Python path should point to:

```text
DigiGates\backend\.venv\Scripts\python.exe
```

If another application's bundled Python appears first, recreate `.venv` using a known Python 3.11 installation.

---

## `{"detail":"Not Found"}` at Port 8000

This is expected when requesting `/` if no root API route is defined.

Use:

```text
http://127.0.0.1:8000/docs
```

to inspect the API.

---

## Frontend Cannot Reach Backend

Confirm that:

- FastAPI is running.
- The backend is listening on port `8000`.
- The frontend environment points to the correct API URL.
- `FRONTEND_ORIGIN` is correctly configured.
- Both frontend and backend are running simultaneously.

---

## Database Connection Failure

Check:

- `MYSQL_HOST`
- `MYSQL_PORT`
- `MYSQL_DATABASE`
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- SSL/certificate requirements for the configured database
- Network connectivity to the database service

Never paste database passwords into GitHub issues, commits, screenshots, or public documentation.

---

# Security

- Never commit `.env`.
- Never commit production or shared database passwords.
- Never hardcode administrator passwords.
- Keep `SECRET_KEY` private.
- Use dedicated databases for integration testing.
- Treat shared Aiven database data as persistent team data.
- Review `.gitignore` before committing new environment or certificate files.

---

# DigiGates

DigiGates is developed as an educational Human-Computer Interaction project focused on making digital logic concepts interactive, understandable, and learnable through direct manipulation, visual feedback, exploration, and circuit construction.