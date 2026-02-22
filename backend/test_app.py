import os
import sqlite3
from contextlib import closing

from app import create_app


def test_health_ok():
    app = create_app()
    client = app.test_client()

    res = client.get("/health")
    assert res.status_code == 200
    assert res.json == {"ok": True}


def test_visitas_persistem(tmp_path, monkeypatch):
    db_path = tmp_path / "app.db"
    monkeypatch.setenv("DB_PATH", str(db_path))

    app = create_app()
    client = app.test_client()

    assert client.get("/").status_code == 200

    client.get("/incrementar")
    client.get("/incrementar")

    with closing(sqlite3.connect(db_path)) as conn:
        row = conn.execute(
            "SELECT value FROM app_state WHERE key='visitas'"
        ).fetchone()
        assert row is not None
        assert int(row[0]) == 2
