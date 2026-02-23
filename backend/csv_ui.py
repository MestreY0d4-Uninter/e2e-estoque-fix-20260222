"""Importação/Exportação CSV (V1).

Escopo:
- Exportar produtos em CSV
- Importar produtos via CSV (cria/atualiza por SKU)
- Relatório de erros por linha (não quebra o app)
- Template CSV para download
- (Opcional) exportar movimentações em CSV

Rotas:
- GET  /csv (tela)
- GET  /csv/template/produtos.csv
- GET  /csv/export/produtos.csv
- POST /csv/import/produtos
- GET  /csv/export/movimentacoes.csv
"""

from __future__ import annotations

import csv
import io
import sqlite3
from contextlib import closing

from flask import Flask, Response, redirect, render_template_string, request, url_for


PRODUTOS_HEADERS = [
    "sku",
    "nome",
    "categoria",
    "fornecedor",
    "custo",
    "preco",
    "quantidade_atual",
    "estoque_minimo",
]


def register_csv_routes(app: Flask, *, db_path: str, base_style: str) -> None:
    def query_all(sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        with closing(sqlite3.connect(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(sql, params)
            return list(cur.fetchall())

    def execute(sql: str, params: tuple = ()) -> None:
        with closing(sqlite3.connect(db_path)) as conn:
            conn.execute(sql, params)
            conn.commit()

    def upsert_produto(row: dict[str, str]) -> tuple[bool, str]:
        """Cria/atualiza produto pelo SKU. Retorna (ok, msg)."""

        sku = (row.get("sku") or "").strip()
        nome = (row.get("nome") or "").strip()
        if not sku:
            return False, "SKU é obrigatório"
        if not nome:
            return False, "Nome é obrigatório"

        categoria = (row.get("categoria") or "").strip() or None
        fornecedor = (row.get("fornecedor") or "").strip() or None

        def parse_int(value: str | None) -> int:
            v = (value or "").strip()
            if v == "":
                return 0
            if not v.lstrip("-").isdigit():
                raise ValueError("inteiro inválido")
            return int(v)

        def parse_float(value: str | None) -> float:
            v = (value or "").strip().replace(",", ".")
            if v == "":
                return 0.0
            return float(v)

        try:
            custo = parse_float(row.get("custo"))
            preco = parse_float(row.get("preco"))
            quantidade_atual = parse_int(row.get("quantidade_atual"))
            estoque_minimo = parse_int(row.get("estoque_minimo"))
        except ValueError:
            return False, "Campos numéricos inválidos (custo/preco/quantidades)"

        try:
            with closing(sqlite3.connect(db_path)) as conn:
                conn.execute("BEGIN")
                existing = conn.execute(
                    "SELECT id FROM produtos WHERE sku=?", (sku,)
                ).fetchone()

                if existing:
                    conn.execute(
                        """
                        UPDATE produtos
                        SET nome=?, categoria=?, fornecedor=?, custo=?, preco=?,
                            quantidade_atual=?, estoque_minimo=?,
                            atualizado_em=CURRENT_TIMESTAMP
                        WHERE sku=?
                        """,
                        (
                            nome,
                            categoria,
                            fornecedor,
                            float(custo),
                            float(preco),
                            int(quantidade_atual),
                            int(estoque_minimo),
                            sku,
                        ),
                    )
                    conn.commit()
                    return True, "atualizado"

                conn.execute(
                    """
                    INSERT INTO produtos(
                      nome, sku, categoria, fornecedor, custo, preco,
                      quantidade_atual, estoque_minimo
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        nome,
                        sku,
                        categoria,
                        fornecedor,
                        float(custo),
                        float(preco),
                        int(quantidade_atual),
                        int(estoque_minimo),
                    ),
                )
                conn.commit()
                return True, "criado"
        except sqlite3.IntegrityError as e:
            return False, f"Erro de integridade no banco: {e}"

    page_template = """
<!doctype html>
<html lang="pt-BR">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>CSV</title>
    {{ base_style | safe }}
  </head>
  <body>
    <div class="card">
      <div class="row">
        <a class="btn" href="{{ url_for('index') }}">Início</a>
        <a class="btn" href="{{ url_for('produtos_list') }}">Produtos</a>
        <a class="btn" href="{{ url_for('movimentacoes_list') }}">Movimentações</a>
      </div>

      <h1>CSV (Importar / Exportar)</h1>

      <h2>Produtos</h2>
      <div class="row">
        <a class="btn" href="{{ url_for('csv_export_produtos') }}">Exportar produtos (CSV)</a>
        <a class="btn" href="{{ url_for('csv_template_produtos') }}">Baixar template (CSV)</a>
      </div>

      <div class="spacer"></div>

      <form method="post" action="{{ url_for('csv_import_produtos') }}" enctype="multipart/form-data">
        <label>Importar produtos via CSV (cria/atualiza por SKU)<br />
          <input type="file" name="arquivo" accept=".csv,text/csv" required />
        </label>
        <div class="spacer"></div>
        <button class="btn" type="submit">Importar</button>
      </form>

      <div class="spacer"></div>

      {% if resultado %}
        <h3>Resultado</h3>
        <div class="ok">
          Linhas processadas: <strong>{{ resultado.total }}</strong><br />
          Criados: <strong>{{ resultado.criados }}</strong> | Atualizados: <strong>{{ resultado.atualizados }}</strong> | Erros: <strong>{{ resultado.erros|length }}</strong>
        </div>

        {% if resultado.erros %}
          <div class="spacer"></div>
          <div class="error">
            <strong>Erros (por linha):</strong>
            <ul>
              {% for e in resultado.erros %}
                <li>Linha {{ e.linha }}: {{ e.msg }}</li>
              {% endfor %}
            </ul>
          </div>
        {% endif %}
      {% endif %}

      <div class="spacer"></div>
      <h2>Movimentações (export opcional)</h2>
      <div class="row">
        <a class="btn" href="{{ url_for('csv_export_movimentacoes') }}">Exportar movimentações (CSV)</a>
      </div>

      <div class="spacer"></div>
      <p class="muted">Obs.: Importação de movimentações está fora de escopo.</p>
    </div>
  </body>
</html>
"""

    @app.get("/csv")
    def csv_home():
        # resultado pode ser passado via sessão/flash no futuro; por simplicidade,
        # apenas renderiza.
        return render_template_string(
            page_template, base_style=base_style, resultado=None
        )

    @app.get("/csv/template/produtos.csv")
    def csv_template_produtos():
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=PRODUTOS_HEADERS)
        writer.writeheader()
        writer.writerow(
            {
                "sku": "SKU-001",
                "nome": "Produto exemplo",
                "categoria": "Categoria",
                "fornecedor": "Fornecedor",
                "custo": "1.50",
                "preco": "3.00",
                "quantidade_atual": "10",
                "estoque_minimo": "2",
            }
        )
        data = buf.getvalue().encode("utf-8")
        return Response(
            data,
            mimetype="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": 'attachment; filename="template-produtos.csv"'
            },
        )

    @app.get("/csv/export/produtos.csv")
    def csv_export_produtos():
        rows = query_all(
            """
            SELECT sku, nome, categoria, fornecedor, custo, preco, quantidade_atual, estoque_minimo
            FROM produtos
            ORDER BY nome ASC
            """
        )
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=PRODUTOS_HEADERS)
        writer.writeheader()
        for r in rows:
            writer.writerow(
                {k: ("" if r[k] is None else r[k]) for k in PRODUTOS_HEADERS}
            )
        data = buf.getvalue().encode("utf-8")
        return Response(
            data,
            mimetype="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="produtos.csv"'},
        )

    @app.post("/csv/import/produtos")
    def csv_import_produtos():
        f = request.files.get("arquivo")
        if f is None:
            return redirect(url_for("csv_home"))

        raw = f.read()
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            # fallback para latin-1
            text = raw.decode("latin-1")

        reader = csv.DictReader(io.StringIO(text))
        headers = reader.fieldnames or []

        missing = [h for h in PRODUTOS_HEADERS if h not in headers]
        if missing:
            resultado = {
                "total": 0,
                "criados": 0,
                "atualizados": 0,
                "erros": [
                    {
                        "linha": 1,
                        "msg": f"CSV inválido: colunas obrigatórias ausentes: {', '.join(missing)}",
                    }
                ],
            }
            return render_template_string(
                page_template, base_style=base_style, resultado=resultado
            )

        total = 0
        criados = 0
        atualizados = 0
        erros: list[dict[str, object]] = []

        for idx, row in enumerate(reader, start=2):
            total += 1
            ok, msg = upsert_produto(row)
            if not ok:
                erros.append({"linha": idx, "msg": msg})
                continue
            if msg == "criado":
                criados += 1
            elif msg == "atualizado":
                atualizados += 1

        resultado = {
            "total": total,
            "criados": criados,
            "atualizados": atualizados,
            "erros": erros,
        }

        return render_template_string(
            page_template, base_style=base_style, resultado=resultado
        )

    @app.get("/csv/export/movimentacoes.csv")
    def csv_export_movimentacoes():
        rows = query_all(
            """
            SELECT m.id, m.criado_em, p.sku AS produto_sku, p.nome AS produto_nome,
                   m.tipo, m.quantidade, m.observacao
            FROM movimentacoes m
            JOIN produtos p ON p.id = m.produto_id
            ORDER BY m.criado_em DESC, m.id DESC
            LIMIT 2000
            """
        )

        headers = [
            "id",
            "criado_em",
            "produto_sku",
            "produto_nome",
            "tipo",
            "quantidade",
            "observacao",
        ]
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=headers)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: ("" if r[k] is None else r[k]) for k in headers})

        data = buf.getvalue().encode("utf-8")
        return Response(
            data,
            mimetype="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="movimentacoes.csv"'},
        )

    # Evitar "imported but unused" em lint quando helper não é usado.
    _ = execute
