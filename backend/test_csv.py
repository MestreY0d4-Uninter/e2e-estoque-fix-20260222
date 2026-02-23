import io

from app import create_app


def test_csv_template_produtos_contem_header():
    app = create_app()
    client = app.test_client()

    res = client.get("/csv/template/produtos.csv")
    assert res.status_code == 200
    text = res.data.decode("utf-8")

    header = text.splitlines()[0]
    assert header.startswith("sku,nome,categoria,fornecedor,custo,preco")


def test_csv_import_cria_e_atualiza_por_sku(tmp_path, monkeypatch):
    db_path = tmp_path / "app.db"
    monkeypatch.setenv("DB_PATH", str(db_path))

    app = create_app()
    client = app.test_client()

    # 1) cria
    csv1 = (
        "sku,nome,categoria,fornecedor,custo,preco,quantidade_atual,estoque_minimo\n"
        "SKU-1,Produto A,Cat,For,1.0,2.0,5,1\n"
    )
    data = {
        "arquivo": (io.BytesIO(csv1.encode("utf-8")), "produtos.csv"),
    }
    res1 = client.post(
        "/csv/import/produtos",
        data=data,
        content_type="multipart/form-data",
    )
    assert res1.status_code == 200
    assert b"Criados" in res1.data

    # 2) atualiza
    csv2 = (
        "sku,nome,categoria,fornecedor,custo,preco,quantidade_atual,estoque_minimo\n"
        "SKU-1,Produto A2,Cat,For,1.0,2.0,10,1\n"
    )
    data2 = {
        "arquivo": (io.BytesIO(csv2.encode("utf-8")), "produtos.csv"),
    }
    res2 = client.post(
        "/csv/import/produtos",
        data=data2,
        content_type="multipart/form-data",
    )
    assert res2.status_code == 200
    assert b"Atualizados" in res2.data


def test_csv_import_reporta_erros_sem_quebrar(tmp_path, monkeypatch):
    db_path = tmp_path / "app.db"
    monkeypatch.setenv("DB_PATH", str(db_path))

    app = create_app()
    client = app.test_client()

    # linha inválida (sem nome) + válida
    csv_text = (
        "sku,nome,categoria,fornecedor,custo,preco,quantidade_atual,estoque_minimo\n"
        "SKU-1,,Cat,For,1.0,2.0,5,1\n"
        "SKU-2,Produto B,Cat,For,1.0,2.0,5,1\n"
    )
    data = {"arquivo": (io.BytesIO(csv_text.encode("utf-8")), "produtos.csv")}
    res = client.post(
        "/csv/import/produtos",
        data=data,
        content_type="multipart/form-data",
    )
    assert res.status_code == 200
    assert b"Erros" in res.data
    # deve processar a linha válida mesmo com erro na anterior
    assert b"Criados" in res.data
    assert b"Atualizados" in res.data
