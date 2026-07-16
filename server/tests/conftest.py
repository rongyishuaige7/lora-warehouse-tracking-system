"""Pytest fixtures: temporary DB and Flask test client."""
import os
import tempfile

import pytest


@pytest.fixture(scope="session")
def temp_db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    try:
        os.unlink(path)
    except OSError:
        pass


@pytest.fixture(scope="module")
def app(temp_db_path):
    os.environ["WAREHOUSE_DB_PATH"] = temp_db_path
    os.environ.pop("WAREHOUSE_CONFIG_PATH", None)
    import server as srv
    srv.db.init_db()
    return srv.app


@pytest.fixture
def client(app):
    return app.test_client()
