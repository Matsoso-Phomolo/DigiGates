# DigiGates

React/JavaScript performs real-time simulation. FastAPI, Pydantic, SQLAlchemy, and MySQL store persistent application data. Switch evaluation, signal propagation, LEDs, expressions, and truth-table highlighting remain frontend-side.

## MySQL setup

Use MySQL 8+. From an administrative MySQL session:

```sql
CREATE DATABASE digigates CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'digigates_app'@'localhost' IDENTIFIED BY 'choose-a-local-password';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, DROP, REFERENCES
  ON digigates.* TO 'digigates_app'@'localhost';
FLUSH PRIVILEGES;
```

Copy `backend/.env.example` to `backend/.env`. Configure `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_DATABASE`, `MYSQL_USER`, `MYSQL_PASSWORD`, `SECRET_KEY`, `ACCESS_TOKEN_MINUTES`, `FRONTEND_ORIGIN`, and `SQL_ECHO`. No real secrets are committed.

## Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env.
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload --port 8000
```

`python -m app.seed` idempotently inserts BUFFER, NOT, AND, OR, NAND, NOR, XOR, and XNOR. It does not create an administrator with a hardcoded password. For local development, register normally and deliberately promote the selected account:

```sql
UPDATE users SET role='ADMIN' WHERE email='your-admin@example.com';
```

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

## Tests

```powershell
cd backend
pytest -q tests/test_circuit_validation.py
```

MySQL integration tests require a dedicated disposable database. Never target development or production data.

```sql
CREATE DATABASE digigates_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL PRIVILEGES ON digigates_test.* TO 'digigates_app'@'localhost';
```

```powershell
$env:DIGIGATES_TEST_MYSQL='1'
$env:MYSQL_DATABASE='digigates_test'
pytest -q
```

Frontend verification:

```powershell
cd frontend
npm test -- --run
npm run build
```

## API

Authentication: `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`.

Administrator-only list/view/add/update/delete resources:

- `/api/admin/logic-gates`
- `/api/admin/lessons`
- `/api/admin/prebuilt-circuits`
- `/api/admin/exercises`

Learner APIs:

- `GET /api/lessons`
- `GET /api/prebuilt-circuits`
- `POST|GET /api/saved-circuits`
- `GET|PUT|DELETE /api/saved-circuits/{id}`
- `PUT|GET /api/progress`
- `POST /api/exercise-attempts`

Circuit JSON is versioned and documented by `CircuitDefinition` in `backend/app/schemas.py`. API validation covers variable uniqueness, A–Z labels, the four-box maximum, gate types and arity, row/column bounds, adjacent rows, source existence, unique input positions, and forward-only dependencies before MySQL persistence.
