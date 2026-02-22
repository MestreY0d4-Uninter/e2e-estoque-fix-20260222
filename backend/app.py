import os
import sqlite3
from contextlib import closing

from flask import Flask, redirect, render_template_string, url_for


def create_app() -> Flask:
    app = Flask(__name__)

    port = int(os.getenv("PORT", "3000"))
    db_path = os.getenv("DB_PATH", "/data/app.db")

    index_template = """
<!doctype html>
<html lang="pt-BR">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Estoque - V1</title>
    <style>
      body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 40px; background: #f6f7fb; }
      .card { max-width: 760px; background: #fff; border: 1px solid #e6e6e6; border-radius: 12px; padding: 20px; box-shadow: 0 10px 30px rgba(0,0,0,.06); }
      code { background: #f3f4f6; padding: 2px 6px; border-radius: 6px; }
      a.btn { display: inline-block; margin-top: 10px; padding: 10px 14px; border-radius: 10px; border: 1px solid #cfd3da; text-decoration: none; color: #111; background: #fafafa; }
      a.btn:hover { background: #f2f2f2; }
      .muted { color: #666; }
    </style>
  </head>
  <body>
    <div class="card">
      <h1>Sistema de Estoque (V1)</h1>
      <p>Status: <strong>no ar</strong>.</p>
      <p>Banco SQLite: <code>{{ db_path }}</code></p>
      <p><strong>Visitas persistidas:</strong> {{ visitas }}</p>
      <a class="btn" href="{{ url_for('incrementar') }}">Incrementar</a>
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

    @app.get("/")
    def index():
        return render_template_string(
            index_template, db_path=db_path, visitas=get_visitas()
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
