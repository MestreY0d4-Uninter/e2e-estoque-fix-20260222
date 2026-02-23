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


def test_movimentacao_atualiza_quantidade(tmp_path, monkeypatch):
    db_path = tmp_path / "app.db"
    monkeypatch.setenv("DB_PATH", str(db_path))

    app = create_app()
    client = app.test_client()

    client.post(
        "/produtos/novo",
        data={"nome": "Caderno", "sku": "CAD-01", "quantidade_atual": "10"},
        follow_redirects=True,
    )

    client.post(
        "/movimentacoes/nova",
        data={
            "produto_id": "1",
            "tipo": "saida",
            "quantidade": "3",
            "observacao": "Venda",
        },
        follow_redirects=True,
    )

    with closing(sqlite3.connect(db_path)) as conn:
        row = conn.execute(
            "SELECT quantidade_atual FROM produtos WHERE id=1"
        ).fetchone()
        assert row is not None
        assert int(row[0]) == 7


def test_saida_nao_permite_estoque_negativo(tmp_path, monkeypatch):
    db_path = tmp_path / "app.db"
    monkeypatch.setenv("DB_PATH", str(db_path))

    app = create_app()
    client = app.test_client()

    client.post(
        "/produtos/novo",
        data={"nome": "Grampeador", "sku": "GR-01", "quantidade_atual": "2"},
        follow_redirects=True,
    )

    res = client.post(
        "/movimentacoes/nova",
        data={
            "produto_id": "1",
            "tipo": "saida",
            "quantidade": "5",
            "observacao": "Teste",
        },
        follow_redirects=True,
    )

    assert res.status_code == 200
    assert b"estoque ficaria negativo" in res.data

    with closing(sqlite3.connect(db_path)) as conn:
        row = conn.execute(
            "SELECT quantidade_atual FROM produtos WHERE id=1"
        ).fetchone()
        assert row is not None
        assert int(row[0]) == 2


def test_movimentacao_atualiza_quantidade_e_bloqueia_negativo(tmp_path, monkeypatch):
    db_path = tmp_path / "app.db"
    monkeypatch.setenv("DB_PATH", str(db_path))

    app = create_app()
    client = app.test_client()

    # cria produto
    client.post(
        "/produtos/novo",
        data={
            "nome": "Caderno",
            "sku": "CAD-01",
            "quantidade_atual": "0",
            "estoque_minimo": "0",
        },
        follow_redirects=True,
    )

    # captura id
    with closing(sqlite3.connect(db_path)) as conn:
        row = conn.execute(
            "SELECT id, quantidade_atual FROM produtos WHERE sku='CAD-01'"
        ).fetchone()
        assert row is not None
        produto_id = int(row[0])
        assert int(row[1]) == 0

    # entrada 5
    r1 = client.post(
        "/movimentacoes/nova",
        data={
            "produto_id": str(produto_id),
            "tipo": "entrada",
            "quantidade": "5",
            "observacao": "compra",
        },
        follow_redirects=True,
    )
    assert r1.status_code == 200
    assert b"Movimenta\xc3\xa7\xc3\xa3o registrada" in r1.data

    with closing(sqlite3.connect(db_path)) as conn:
        row2 = conn.execute(
            "SELECT quantidade_atual FROM produtos WHERE id=?", (produto_id,)
        ).fetchone()
        assert row2 is not None
        assert int(row2[0]) == 5

    # saída 10 (negativo) deve bloquear
    r2 = client.post(
        "/movimentacoes/nova",
        data={
            "produto_id": str(produto_id),
            "tipo": "saida",
            "quantidade": "10",
        },
    )
    assert r2.status_code == 200
    assert b"estoque ficaria negativo" in r2.data

    with closing(sqlite3.connect(db_path)) as conn:
        row3 = conn.execute(
            "SELECT quantidade_atual FROM produtos WHERE id=?", (produto_id,)
        ).fetchone()
        assert row3 is not None
        assert int(row3[0]) == 5
