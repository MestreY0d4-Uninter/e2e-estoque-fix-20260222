"""UI de Movimentações (V1).

Rotas:
- GET  /movimentacoes (histórico geral)
- GET  /movimentacoes/nova (formulário)
- POST /movimentacoes/nova (criar movimentação)
- GET  /produtos/<id>/movimentacoes (histórico por produto)
"""

from __future__ import annotations

import sqlite3
from contextlib import closing

from flask import Flask, redirect, render_template_string, request, url_for


def register_movements_routes(app: Flask, *, db_path: str, base_style: str) -> None:
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

    def registrar_movimentacao(
        *, produto_id: int, tipo: str, quantidade: int, observacao: str | None
    ) -> tuple[bool, str]:
        """Registra movimentação e atualiza estoque do produto.

        Retorna (ok, mensagem).
        """

        if tipo not in {"entrada", "saida"}:
            return False, "Tipo inválido."
        if quantidade <= 0:
            return False, "Quantidade deve ser maior que zero."

        with closing(sqlite3.connect(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("BEGIN")

            row = conn.execute(
                "SELECT id, quantidade_atual FROM produtos WHERE id=?",
                (produto_id,),
            ).fetchone()
            if row is None:
                conn.execute("ROLLBACK")
                return False, "Produto não encontrado."

            atual = int(row["quantidade_atual"])
            novo = atual + quantidade if tipo == "entrada" else atual - quantidade

            if novo < 0:
                conn.execute("ROLLBACK")
                return False, "Saída não permitida: estoque ficaria negativo."

            conn.execute(
                """
                INSERT INTO movimentacoes(produto_id, tipo, quantidade, observacao)
                VALUES(?, ?, ?, ?)
                """,
                (produto_id, tipo, quantidade, observacao),
            )
            conn.execute(
                """
                UPDATE produtos
                SET quantidade_atual=?, atualizado_em=CURRENT_TIMESTAMP
                WHERE id=?
                """,
                (novo, produto_id),
            )
            conn.commit()

        return True, "Movimentação registrada."

    list_template = """
<!doctype html>
<html lang="pt-BR">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Movimentações</title>
    {{ base_style | safe }}
  </head>
  <body>
    <div class="card">
      <div class="row">
        <a class="btn" href="{{ url_for('index') }}">Início</a>
        <a class="btn" href="{{ url_for('produtos_list') }}">Produtos</a>
        <a class="btn" href="{{ url_for('movimentacoes_new') }}">Nova movimentação</a>
      </div>

      <h1>Movimentações</h1>
      {% if msg_ok %}<div class="ok">{{ msg_ok }}</div>{% endif %}
      {% if msg_err %}<div class="error">{{ msg_err }}</div>{% endif %}

      <div class="spacer"></div>

      <table>
        <thead>
          <tr>
            <th>Data/hora</th>
            <th>Produto</th>
            <th>Tipo</th>
            <th>Quantidade</th>
            <th>Obs.</th>
          </tr>
        </thead>
        <tbody>
          {% for m in movimentos %}
            <tr>
              <td><code>{{ m.criado_em }}</code></td>
              <td><a href="{{ url_for('produtos_detail', produto_id=m.produto_id) }}">{{ m.produto_nome }}</a></td>
              <td>{{ 'Entrada' if m.tipo == 'entrada' else 'Saída' }}</td>
              <td>{{ m.quantidade }}</td>
              <td>{{ m.observacao or '-' }}</td>
            </tr>
          {% else %}
            <tr><td colspan="5" class="muted">Nenhuma movimentação registrada.</td></tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </body>
</html>
"""

    new_template = """
<!doctype html>
<html lang="pt-BR">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Nova movimentação</title>
    {{ base_style | safe }}
  </head>
  <body>
    <div class="card">
      <div class="row">
        <a class="btn" href="{{ url_for('movimentacoes_list') }}">Voltar</a>
      </div>

      <h1>Nova movimentação</h1>

      {% if msg_err %}<div class="error">{{ msg_err }}</div>{% endif %}
      {% if msg_ok %}<div class="ok">{{ msg_ok }}</div>{% endif %}

      <form method="post">
        <div class="row">
          <div style="flex: 1; min-width: 260px;">
            <label>Produto<br />
              <select name="produto_id" required>
                {% for p in produtos %}
                  <option value="{{ p.id }}" {% if p.id == produto_id %}selected{% endif %}>{{ p.nome }} ({{ p.sku }}) — qtd {{ p.quantidade_atual }}</option>
                {% endfor %}
              </select>
            </label>
          </div>

          <div style="width: 220px;">
            <label>Tipo<br />
              <select name="tipo" required>
                <option value="entrada" {% if tipo == 'entrada' %}selected{% endif %}>Entrada</option>
                <option value="saida" {% if tipo == 'saida' %}selected{% endif %}>Saída</option>
              </select>
            </label>
          </div>

          <div style="width: 200px;">
            <label>Quantidade<br />
              <input name="quantidade" inputmode="numeric" value="{{ quantidade }}" required />
            </label>
          </div>
        </div>

        <div class="spacer"></div>

        <label>Observação (opcional)<br />
          <input name="observacao" value="{{ observacao }}" style="width: 100%;" />
        </label>

        <div class="spacer"></div>
        <button class="btn" type="submit">Registrar</button>
      </form>
    </div>
  </body>
</html>
"""

    per_product_template = """
<!doctype html>
<html lang="pt-BR">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Movimentações - {{ produto.nome }}</title>
    {{ base_style | safe }}
  </head>
  <body>
    <div class="card">
      <div class="row">
        <a class="btn" href="{{ url_for('produtos_detail', produto_id=produto.id) }}">Voltar ao produto</a>
        <a class="btn" href="{{ url_for('movimentacoes_new', produto_id=produto.id) }}">Nova movimentação</a>
      </div>

      <h1>Movimentações — {{ produto.nome }}</h1>
      <p><strong>SKU:</strong> <code>{{ produto.sku }}</code></p>

      <table>
        <thead>
          <tr>
            <th>Data/hora</th>
            <th>Tipo</th>
            <th>Quantidade</th>
            <th>Obs.</th>
          </tr>
        </thead>
        <tbody>
          {% for m in movimentos %}
            <tr>
              <td><code>{{ m.criado_em }}</code></td>
              <td>{{ 'Entrada' if m.tipo == 'entrada' else 'Saída' }}</td>
              <td>{{ m.quantidade }}</td>
              <td>{{ m.observacao or '-' }}</td>
            </tr>
          {% else %}
            <tr><td colspan="4" class="muted">Nenhuma movimentação para este produto.</td></tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </body>
</html>
"""

    @app.get("/movimentacoes")
    def movimentacoes_list():
        rows = query_all(
            """
            SELECT m.*, p.nome AS produto_nome
            FROM movimentacoes m
            JOIN produtos p ON p.id = m.produto_id
            ORDER BY m.criado_em DESC, m.id DESC
            LIMIT 200
            """
        )
        return render_template_string(
            list_template,
            base_style=base_style,
            movimentos=rows,
            msg_ok=request.args.get("ok"),
            msg_err=request.args.get("err"),
        )

    @app.get("/movimentacoes/nova")
    def movimentacoes_new():
        produtos = query_all("SELECT * FROM produtos ORDER BY nome ASC")
        if not produtos:
            return redirect(
                url_for(
                    "produtos_list",
                    err="Cadastre pelo menos um produto antes de registrar movimentações.",
                )
            )

        produto_id = request.args.get("produto_id")
        selected = (
            int(produto_id)
            if (produto_id and produto_id.isdigit())
            else int(produtos[0]["id"])
        )

        return render_template_string(
            new_template,
            base_style=base_style,
            produtos=produtos,
            produto_id=selected,
            tipo="entrada",
            quantidade="1",
            observacao="",
            msg_err=None,
            msg_ok=None,
        )

    @app.post("/movimentacoes/nova")
    def movimentacoes_create():
        produtos = query_all("SELECT * FROM produtos ORDER BY nome ASC")
        if not produtos:
            return redirect(
                url_for(
                    "produtos_list",
                    err="Cadastre pelo menos um produto antes de registrar movimentações.",
                )
            )

        produto_id_str = (request.form.get("produto_id") or "").strip()
        tipo = (request.form.get("tipo") or "").strip()
        quantidade_str = (request.form.get("quantidade") or "").strip()
        observacao = (request.form.get("observacao") or "").strip() or None

        produto_id = int(produto_id_str) if produto_id_str.isdigit() else 0
        quantidade = int(quantidade_str) if quantidade_str.isdigit() else 0

        ok, msg = registrar_movimentacao(
            produto_id=produto_id,
            tipo=tipo,
            quantidade=quantidade,
            observacao=observacao,
        )
        if not ok:
            return render_template_string(
                new_template,
                base_style=base_style,
                produtos=produtos,
                produto_id=produto_id,
                tipo=tipo,
                quantidade=quantidade_str,
                observacao=observacao or "",
                msg_err=msg,
                msg_ok=None,
            )

        return redirect(url_for("movimentacoes_list", ok=msg))

    @app.get("/produtos/<int:produto_id>/movimentacoes")
    def movimentacoes_por_produto(produto_id: int):
        produto = query_one("SELECT * FROM produtos WHERE id=?", (produto_id,))
        if produto is None:
            return redirect(url_for("produtos_list", err="Produto não encontrado."))

        movimentos = query_all(
            """
            SELECT *
            FROM movimentacoes
            WHERE produto_id=?
            ORDER BY criado_em DESC, id DESC
            LIMIT 200
            """,
            (produto_id,),
        )

        return render_template_string(
            per_product_template,
            base_style=base_style,
            produto=dict(produto),
            movimentos=movimentos,
        )
