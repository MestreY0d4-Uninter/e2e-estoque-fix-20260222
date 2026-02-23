import os
import sqlite3
from contextlib import closing

from flask import Flask, redirect, render_template_string, url_for

from products_ui import register_products_routes


def create_app() -> Flask:
    app = Flask(__name__)

    port = int(os.getenv("PORT", "3000"))
    db_path = os.getenv("DB_PATH", "/data/app.db")

    base_style = """
<style>
  body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 40px; background: #f6f7fb; }
  .card { max-width: 960px; background: #fff; border: 1px solid #e6e6e6; border-radius: 12px; padding: 20px; box-shadow: 0 10px 30px rgba(0,0,0,.06); }
  code { background: #f3f4f6; padding: 2px 6px; border-radius: 6px; }
  a.btn, button.btn { display: inline-block; padding: 10px 14px; border-radius: 10px; border: 1px solid #cfd3da; text-decoration: none; color: #111; background: #fafafa; cursor: pointer; }
  a.btn:hover, button.btn:hover { background: #f2f2f2; }
  .muted { color: #666; }
  .row { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
  .spacer { height: 12px; }
  input, select { padding: 10px; border-radius: 10px; border: 1px solid #cfd3da; }
  table { width: 100%; border-collapse: collapse; }
  th, td { padding: 10px; border-bottom: 1px solid #eee; text-align: left; }
  tr.low { background: #fff4f4; }
  .tag-low { display: inline-block; padding: 2px 8px; border-radius: 999px; background: #ffe5e5; color: #8a1f1f; font-size: 12px; }
  .error { background: #fff4f4; border: 1px solid #ffd0d0; padding: 10px 12px; border-radius: 12px; }
  .ok { background: #eefbf2; border: 1px solid #ccefd6; padding: 10px 12px; border-radius: 12px; }
</style>
"""

    index_template = """
<!doctype html>
<html lang="pt-BR">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Estoque - V1</title>
    {{ base_style | safe }}
  </head>
  <body>
    <div class="card">
      <h1>Sistema de Estoque (V1)</h1>
      <p>Status: <strong>no ar</strong>.</p>
      <p>Banco SQLite: <code>{{ db_path }}</code></p>

      <div class="row">
        <a class="btn" href="{{ url_for('produtos_list') }}">Produtos</a>
        <a class="btn" href="{{ url_for('incrementar') }}">Incrementar visitas (debug)</a>
      </div>

      <div class="spacer"></div>
      <p><strong>Visitas persistidas:</strong> {{ visitas }}</p>
      <p class="muted">Dica: incremente, reinicie o <code>docker compose</code> e verifique se o número se mantém.</p>
    </div>
  </body>
</html>
"""

    def init_db() -> None:
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        with closing(sqlite3.connect(db_path)) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS app_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "INSERT OR IGNORE INTO app_state(key, value) VALUES ('visitas', '0')"
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS produtos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    sku TEXT NOT NULL UNIQUE,
                    categoria TEXT,
                    fornecedor TEXT,
                    custo REAL NOT NULL DEFAULT 0,
                    preco REAL NOT NULL DEFAULT 0,
                    quantidade_atual INTEGER NOT NULL DEFAULT 0,
                    estoque_minimo INTEGER NOT NULL DEFAULT 0,
                    criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
                    atualizado_em DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()

    def get_visitas() -> int:
        with closing(sqlite3.connect(db_path)) as conn:
            row = conn.execute(
                "SELECT value FROM app_state WHERE key='visitas'"
            ).fetchone()
            return int(row[0]) if row else 0

    def set_visitas(value: int) -> None:
        with closing(sqlite3.connect(db_path)) as conn:
            conn.execute(
                "UPDATE app_state SET value=? WHERE key='visitas'",
                (str(value),),
            )
            conn.commit()

    @app.get("/health")
    def health():
        return {"ok": True}

    register_products_routes(app, db_path=db_path, base_style=base_style)

    @app.get("/")
    def index():
        return render_template_string(
            index_template,
            base_style=base_style,
            db_path=db_path,
            visitas=get_visitas(),
        )

    @app.get("/incrementar")
    def incrementar():
        atual = get_visitas()
        set_visitas(atual + 1)
        return redirect(url_for("index"))

    init_db()

    # Guardar config útil para testes
    app.config.update({"DB_PATH": db_path, "PORT": port})
    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=app.config["PORT"])
