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
        row = conn.execute("SELECT value FROM app_state WHERE key='visitas'").fetchone()
        assert row is not None
        assert int(row[0]) == 2


def test_sku_unico_bloqueia_duplicado(tmp_path, monkeypatch):
    db_path = tmp_path / "app.db"
    monkeypatch.setenv("DB_PATH", str(db_path))

    app = create_app()
    client = app.test_client()

    res1 = client.post(
        "/produtos/novo",
        data={
            "nome": "Caneta Azul",
            "sku": "SKU-001",
            "categoria": "Papelaria",
            "fornecedor": "Fornecedor A",
            "custo": "1,50",
            "preco": "3,00",
            "quantidade_atual": "10",
            "estoque_minimo": "2",
        },
        follow_redirects=True,
    )
    assert res1.status_code == 200

    res2 = client.post(
        "/produtos/novo",
        data={
            "nome": "Caneta Vermelha",
            "sku": "SKU-001",
        },
    )
    assert res2.status_code == 200
    assert b"SKU j\xc3\xa1 existe" in res2.data


def test_lista_indica_estoque_baixo(tmp_path, monkeypatch):
    db_path = tmp_path / "app.db"
    monkeypatch.setenv("DB_PATH", str(db_path))

    app = create_app()
    client = app.test_client()

    client.post(
        "/produtos/novo",
        data={
            "nome": "Pilhas AAA",
            "sku": "AAA-01",
            "quantidade_atual": "1",
            "estoque_minimo": "5",
        },
        follow_redirects=True,
    )

    res = client.get("/produtos")
    assert res.status_code == 200
    assert b"estoque baixo" in res.data
