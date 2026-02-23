"""Tela de Estoque Baixo (V1).

Rota:
- GET /estoque-baixo
"""

from __future__ import annotations

import sqlite3
from contextlib import closing

from flask import Flask, render_template_string, request


def register_low_stock_routes(app: Flask, *, db_path: str, base_style: str) -> None:
    def query_all(sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        with closing(sqlite3.connect(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(sql, params)
            return list(cur.fetchall())

    template = """
<!doctype html>
<html lang="pt-BR">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Estoque baixo</title>
    {{ base_style | safe }}
  </head>
  <body>
    <div class="card">
      <div class="row">
        <a class="btn" href="{{ url_for('index') }}">Início</a>
        <a class="btn" href="{{ url_for('produtos_list') }}">Produtos</a>
        <a class="btn" href="{{ url_for('movimentacoes_list') }}">Movimentações</a>
      </div>

      <h1>Estoque baixo</h1>
      <p class="muted">Lista de itens com quantidade atual menor ou igual ao estoque mínimo.</p>

      <form method="get" class="row">
        <input name="q" value="{{ q }}" placeholder="Buscar por nome ou SKU" />
        <button class="btn" type="submit">Buscar</button>
        <a class="btn" href="{{ url_for('estoque_baixo') }}">Limpar</a>
      </form>

      <div class="spacer"></div>

      <table>
        <thead>
          <tr>
            <th>Produto</th>
            <th>SKU</th>
            <th>Qtd.</th>
            <th>Est. mín.</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {% for p in produtos %}
            <tr class="low">
              <td><a href="{{ url_for('produtos_detail', produto_id=p.id) }}">{{ p.nome }}</a></td>
              <td><code>{{ p.sku }}</code></td>
              <td>{{ p.quantidade_atual }}</td>
              <td>{{ p.estoque_minimo }}</td>
              <td class="row">
                <a class="btn" href="{{ url_for('produtos_detail', produto_id=p.id) }}">Detalhe</a>
                <a class="btn" href="{{ url_for('movimentacoes_new', produto_id=p.id) }}">Entrada/Saída</a>
              </td>
            </tr>
          {% else %}
            <tr><td colspan="5" class="muted">Nenhum item com estoque baixo.</td></tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </body>
</html>
"""

    @app.get("/estoque-baixo")
    def estoque_baixo():
        q = (request.args.get("q") or "").strip()
        where = ["quantidade_atual <= estoque_minimo"]
        params: list[str] = []
        if q:
            where.append("(nome LIKE ? OR sku LIKE ?)")
            like = f"%{q}%"
            params.extend([like, like])

        sql = "SELECT id, nome, sku, quantidade_atual, estoque_minimo FROM produtos"
        sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY (estoque_minimo - quantidade_atual) DESC, nome ASC"

        produtos = query_all(sql, tuple(params))

        return render_template_string(
            template,
            base_style=base_style,
            produtos=produtos,
            q=q,
        )
