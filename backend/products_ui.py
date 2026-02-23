"""UI de Produtos (V1).

Mantido em arquivo separado para facilitar leitura. Importado pelo app principal.

Rotas (UI):
- GET  /produtos
- GET  /produtos/novo
- POST /produtos/novo
- GET  /produtos/<id>
- GET  /produtos/<id>/editar
- POST /produtos/<id>/editar
- POST /produtos/<id>/excluir
"""

from __future__ import annotations

import sqlite3
from contextlib import closing

from flask import Flask, redirect, render_template_string, request, url_for


def register_products_routes(app: Flask, *, db_path: str, base_style: str) -> None:
    def parse_int(value: str | None, default: int = 0) -> int:
        if value is None or value == "":
            return default
        try:
            return int(value)
        except ValueError:
            return default

    def parse_float(value: str | None, default: float = 0.0) -> float:
        if value is None or value == "":
            return default
        try:
            # aceitar vírgula como separador
            return float(value.replace(",", "."))
        except ValueError:
            return default

    def query_all(sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        with closing(sqlite3.connect(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(sql, params)
            return list(cur.fetchall())

    def query_one(sql: str, params: tuple = ()) -> sqlite3.Row | None:
        with closing(sqlite3.connect(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(sql, params)
            return cur.fetchone()

    def execute(sql: str, params: tuple = ()) -> None:
        with closing(sqlite3.connect(db_path)) as conn:
            conn.execute(sql, params)
            conn.commit()

    list_template = """
<!doctype html>
<html lang="pt-BR">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Produtos</title>
    {{ base_style | safe }}
  </head>
  <body>
    <div class="card">
      <div class="row">
        <a class="btn" href="{{ url_for('index') }}">Início</a>
        <a class="btn" href="{{ url_for('produtos_new') }}">Novo produto</a>
      </div>

      <h1>Produtos</h1>

      <form method="get" class="row">
        <input name="q" value="{{ q }}" placeholder="Buscar por nome ou SKU" />
        <input name="categoria" value="{{ categoria }}" placeholder="Categoria" />
        <input name="fornecedor" value="{{ fornecedor }}" placeholder="Fornecedor" />
        <button class="btn" type="submit">Filtrar</button>
        <a class="btn" href="{{ url_for('produtos_list') }}">Limpar</a>
      </form>

      <div class="spacer"></div>

      {% if msg_ok %}<div class="ok">{{ msg_ok }}</div>{% endif %}
      {% if msg_err %}<div class="error">{{ msg_err }}</div>{% endif %}

      <div class="spacer"></div>

      <table>
        <thead>
          <tr>
            <th>Nome</th>
            <th>SKU</th>
            <th>Categoria</th>
            <th>Fornecedor</th>
            <th>Qtd.</th>
            <th>Est. mín.</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {% for p in produtos %}
            <tr class="{% if p.low_stock %}low{% endif %}">
              <td>
                <a href="{{ url_for('produtos_detail', produto_id=p.id) }}">{{ p.nome }}</a>
                {% if p.low_stock %} <span class="tag-low">estoque baixo</span>{% endif %}
              </td>
              <td><code>{{ p.sku }}</code></td>
              <td>{{ p.categoria or '-' }}</td>
              <td>{{ p.fornecedor or '-' }}</td>
              <td>{{ p.quantidade_atual }}</td>
              <td>{{ p.estoque_minimo }}</td>
              <td>
                <a class="btn" href="{{ url_for('produtos_edit', produto_id=p.id) }}">Editar</a>
              </td>
            </tr>
          {% else %}
            <tr><td colspan="7" class="muted">Nenhum produto encontrado.</td></tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </body>
</html>
"""

    form_template = """
<!doctype html>
<html lang="pt-BR">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{{ titulo }}</title>
    {{ base_style | safe }}
  </head>
  <body>
    <div class="card">
      <div class="row">
        <a class="btn" href="{{ url_for('produtos_list') }}">Voltar</a>
      </div>

      <h1>{{ titulo }}</h1>

      {% if msg_err %}<div class="error">{{ msg_err }}</div>{% endif %}

      <form method="post">
        <div class="row">
          <div style="flex: 1; min-width: 240px;">
            <label>Nome<br />
              <input name="nome" value="{{ produto.nome }}" required />
            </label>
          </div>
          <div style="width: 220px;">
            <label>SKU (único)<br />
              <input name="sku" value="{{ produto.sku }}" required />
            </label>
          </div>
        </div>

        <div class="spacer"></div>

        <div class="row">
          <div style="flex: 1; min-width: 240px;">
            <label>Categoria<br />
              <input name="categoria" value="{{ produto.categoria }}" />
            </label>
          </div>
          <div style="flex: 1; min-width: 240px;">
            <label>Fornecedor<br />
              <input name="fornecedor" value="{{ produto.fornecedor }}" />
            </label>
          </div>
        </div>

        <div class="spacer"></div>

        <div class="row">
          <div style="width: 180px;">
            <label>Custo<br />
              <input name="custo" inputmode="decimal" value="{{ produto.custo }}" />
            </label>
          </div>
          <div style="width: 180px;">
            <label>Preço<br />
              <input name="preco" inputmode="decimal" value="{{ produto.preco }}" />
            </label>
          </div>
          <div style="width: 180px;">
            <label>Qtd. atual<br />
              <input name="quantidade_atual" inputmode="numeric" value="{{ produto.quantidade_atual }}" />
            </label>
          </div>
          <div style="width: 180px;">
            <label>Estoque mínimo<br />
              <input name="estoque_minimo" inputmode="numeric" value="{{ produto.estoque_minimo }}" />
            </label>
          </div>
        </div>

        <div class="spacer"></div>
        <button class="btn" type="submit">Salvar</button>
      </form>
    </div>
  </body>
</html>
"""

    detail_template = """
<!doctype html>
<html lang="pt-BR">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Produto - {{ produto.nome }}</title>
    {{ base_style | safe }}
  </head>
  <body>
    <div class="card">
      <div class="row">
        <a class="btn" href="{{ url_for('produtos_list') }}">Voltar</a>
        <a class="btn" href="{{ url_for('produtos_edit', produto_id=produto.id) }}">Editar</a>
        <a class="btn" href="{{ url_for('movimentacoes_por_produto', produto_id=produto.id) }}">Movimentações</a>
        <a class="btn" href="{{ url_for('movimentacoes_new', produto_id=produto.id) }}">Nova movimentação</a>
        <a class="btn" href="{{ url_for('estoque_baixo') }}">Estoque baixo</a>
      </div>

      <h1>{{ produto.nome }}</h1>
      <p><strong>SKU:</strong> <code>{{ produto.sku }}</code></p>
      <p><strong>Categoria:</strong> {{ produto.categoria or '-' }}</p>
      <p><strong>Fornecedor:</strong> {{ produto.fornecedor or '-' }}</p>
      <p><strong>Custo:</strong> {{ produto.custo }}</p>
      <p><strong>Preço:</strong> {{ produto.preco }}</p>
      <p><strong>Quantidade atual:</strong> {{ produto.quantidade_atual }}</p>
      <p><strong>Estoque mínimo:</strong> {{ produto.estoque_minimo }}</p>

      <p><strong>Última entrada:</strong> {{ ultima_entrada or '-' }}</p>
      <p><strong>Última saída:</strong> {{ ultima_saida or '-' }}</p>

      {% if low_stock %}
        <div class="error">Este produto está com <strong>estoque baixo</strong> (quantidade <= estoque mínimo).</div>
      {% else %}
        <div class="ok">Estoque OK.</div>
      {% endif %}

      <div class="spacer"></div>

      <form method="post" action="{{ url_for('produtos_delete', produto_id=produto.id) }}" onsubmit="return confirm('Excluir este produto?');">
        <button class="btn" type="submit">Excluir</button>
      </form>
    </div>
  </body>
</html>
"""

    @app.get("/produtos")
    def produtos_list():
        q = (request.args.get("q") or "").strip()
        categoria = (request.args.get("categoria") or "").strip()
        fornecedor = (request.args.get("fornecedor") or "").strip()

        where = []
        params: list[str] = []

        if q:
            where.append("(nome LIKE ? OR sku LIKE ?)")
            like = f"%{q}%"
            params.extend([like, like])
        if categoria:
            where.append("categoria = ?")
            params.append(categoria)
        if fornecedor:
            where.append("fornecedor = ?")
            params.append(fornecedor)

        sql = "SELECT * FROM produtos"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY nome ASC"

        rows = query_all(sql, tuple(params))
        produtos = []
        for r in rows:
            produtos.append(
                {
                    **dict(r),
                    "low_stock": int(r["quantidade_atual"]) <= int(r["estoque_minimo"]),
                }
            )

        return render_template_string(
            list_template,
            base_style=base_style,
            produtos=produtos,
            q=q,
            categoria=categoria,
            fornecedor=fornecedor,
            msg_ok=request.args.get("ok"),
            msg_err=request.args.get("err"),
        )

    @app.get("/produtos/novo")
    def produtos_new():
        produto = {
            "nome": "",
            "sku": "",
            "categoria": "",
            "fornecedor": "",
            "custo": "0",
            "preco": "0",
            "quantidade_atual": "0",
            "estoque_minimo": "0",
        }
        return render_template_string(
            form_template,
            base_style=base_style,
            titulo="Novo produto",
            produto=produto,
            msg_err=None,
        )

    @app.post("/produtos/novo")
    def produtos_create():
        nome = (request.form.get("nome") or "").strip()
        sku = (request.form.get("sku") or "").strip()
        categoria = (request.form.get("categoria") or "").strip() or None
        fornecedor = (request.form.get("fornecedor") or "").strip() or None
        custo = parse_float(request.form.get("custo"), 0.0)
        preco = parse_float(request.form.get("preco"), 0.0)
        quantidade_atual = parse_int(request.form.get("quantidade_atual"), 0)
        estoque_minimo = parse_int(request.form.get("estoque_minimo"), 0)

        produto = {
            "nome": nome,
            "sku": sku,
            "categoria": categoria or "",
            "fornecedor": fornecedor or "",
            "custo": request.form.get("custo") or "0",
            "preco": request.form.get("preco") or "0",
            "quantidade_atual": request.form.get("quantidade_atual") or "0",
            "estoque_minimo": request.form.get("estoque_minimo") or "0",
        }

        if not nome or not sku:
            return render_template_string(
                form_template,
                base_style=base_style,
                titulo="Novo produto",
                produto=produto,
                msg_err="Nome e SKU são obrigatórios.",
            )

        try:
            execute(
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
        except sqlite3.IntegrityError:
            return render_template_string(
                form_template,
                base_style=base_style,
                titulo="Novo produto",
                produto=produto,
                msg_err="SKU já existe. Use um SKU diferente.",
            )

        return redirect(url_for("produtos_list", ok="Produto criado."))

    @app.get("/produtos/<int:produto_id>")
    def produtos_detail(produto_id: int):
        produto = query_one("SELECT * FROM produtos WHERE id=?", (produto_id,))
        if produto is None:
            return redirect(url_for("produtos_list", err="Produto não encontrado."))

        low_stock = int(produto["quantidade_atual"]) <= int(produto["estoque_minimo"])

        ultima_entrada = query_one(
            """
            SELECT criado_em, quantidade
            FROM movimentacoes
            WHERE produto_id=? AND tipo='entrada'
            ORDER BY criado_em DESC, id DESC
            LIMIT 1
            """,
            (produto_id,),
        )
        ultima_saida = query_one(
            """
            SELECT criado_em, quantidade
            FROM movimentacoes
            WHERE produto_id=? AND tipo='saida'
            ORDER BY criado_em DESC, id DESC
            LIMIT 1
            """,
            (produto_id,),
        )

        def fmt(row):
            if not row:
                return None
            return f"{row['criado_em']} (qtd {row['quantidade']})"

        return render_template_string(
            detail_template,
            base_style=base_style,
            produto=dict(produto),
            low_stock=low_stock,
            ultima_entrada=fmt(ultima_entrada),
            ultima_saida=fmt(ultima_saida),
        )

    @app.get("/produtos/<int:produto_id>/editar")
    def produtos_edit(produto_id: int):
        produto = query_one("SELECT * FROM produtos WHERE id=?", (produto_id,))
        if produto is None:
            return redirect(url_for("produtos_list", err="Produto não encontrado."))

        return render_template_string(
            form_template,
            base_style=base_style,
            titulo="Editar produto",
            produto=dict(produto),
            msg_err=None,
        )

    @app.post("/produtos/<int:produto_id>/editar")
    def produtos_update(produto_id: int):
        nome = (request.form.get("nome") or "").strip()
        sku = (request.form.get("sku") or "").strip()
        categoria = (request.form.get("categoria") or "").strip() or None
        fornecedor = (request.form.get("fornecedor") or "").strip() or None
        custo = parse_float(request.form.get("custo"), 0.0)
        preco = parse_float(request.form.get("preco"), 0.0)
        quantidade_atual = parse_int(request.form.get("quantidade_atual"), 0)
        estoque_minimo = parse_int(request.form.get("estoque_minimo"), 0)

        if not nome or not sku:
            produto = query_one("SELECT * FROM produtos WHERE id=?", (produto_id,))
            return render_template_string(
                form_template,
                base_style=base_style,
                titulo="Editar produto",
                produto=dict(produto) if produto else {"nome": nome, "sku": sku},
                msg_err="Nome e SKU são obrigatórios.",
            )

        try:
            execute(
                """
                UPDATE produtos
                SET nome=?, sku=?, categoria=?, fornecedor=?, custo=?, preco=?,
                    quantidade_atual=?, estoque_minimo=?, atualizado_em=CURRENT_TIMESTAMP
                WHERE id=?
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
                    int(produto_id),
                ),
            )
        except sqlite3.IntegrityError:
            produto = query_one("SELECT * FROM produtos WHERE id=?", (produto_id,))
            return render_template_string(
                form_template,
                base_style=base_style,
                titulo="Editar produto",
                produto=dict(produto) if produto else {"nome": nome, "sku": sku},
                msg_err="SKU já existe. Use um SKU diferente.",
            )

        return redirect(url_for("produtos_detail", produto_id=produto_id))

    @app.post("/produtos/<int:produto_id>/excluir")
    def produtos_delete(produto_id: int):
        execute("DELETE FROM produtos WHERE id=?", (produto_id,))
        return redirect(url_for("produtos_list", ok="Produto excluído."))
