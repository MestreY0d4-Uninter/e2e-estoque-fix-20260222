from app import create_app


def test_estoque_baixo_lista_itens(tmp_path, monkeypatch):
    db_path = tmp_path / "app.db"
    monkeypatch.setenv("DB_PATH", str(db_path))

    app = create_app()
    client = app.test_client()

    # produto com estoque baixo
    client.post(
        "/produtos/novo",
        data={
            "nome": "Papel A4",
            "sku": "PAPEL-01",
            "quantidade_atual": "2",
            "estoque_minimo": "5",
        },
        follow_redirects=True,
    )

    # produto OK
    client.post(
        "/produtos/novo",
        data={
            "nome": "Mouse",
            "sku": "MOUSE-01",
            "quantidade_atual": "10",
            "estoque_minimo": "2",
        },
        follow_redirects=True,
    )

    res = client.get("/estoque-baixo")
    assert res.status_code == 200
    assert b"PAPEL-01" in res.data
    assert b"MOUSE-01" not in res.data
