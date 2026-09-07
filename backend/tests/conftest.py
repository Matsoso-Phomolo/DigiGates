import os
import pytest

pytestmark=pytest.mark.mysql
@pytest.fixture(scope="session")
def mysql_client():
    if not os.getenv("DIGIGATES_TEST_MYSQL"):
        pytest.skip("Set DIGIGATES_TEST_MYSQL=1 and MYSQL_* variables to run MySQL integration tests")
    from fastapi.testclient import TestClient
    from app.database import Base,engine
    from app.main import app
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    with TestClient(app) as client: yield client
    Base.metadata.drop_all(engine)
@pytest.fixture
def circuit_json():
    return {"version":1,"variables":[{"id":"v1","label":"A","box":1}],"operators":[],"final_operator":{"id":"final","type":"NOT","inputs":[{"source_type":"variable","source_id":"v1","input_position":1}]}}
