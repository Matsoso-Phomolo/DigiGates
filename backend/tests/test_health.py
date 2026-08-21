import os
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
from fastapi.testclient import TestClient
from app.main import app
def test_health(): assert TestClient(app).get("/api/health").json() == {"status": "ok"}
