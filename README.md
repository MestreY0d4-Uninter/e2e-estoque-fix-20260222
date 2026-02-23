# e2e-estoque-fix-20260222 (V1)

Aplicação web simples (em português), rodando via **Docker Compose**, com persistência em **SQLite**.

> V1 (escopo): base do app + cadastro de produtos (CRUD) + persistência no SQLite.

## Requisitos

- Docker + Docker Compose (plugin `docker compose`)

## Como rodar

Na raiz do repositório:

```bash
docker compose up --build
```

Acesse:

- http://localhost:3000 (início)
- http://localhost:3000/produtos (cadastro/listagem de produtos)
- http://localhost:3000/movimentacoes (histórico de movimentações)

Para parar:

```bash
docker compose down
```

## Persistência (SQLite)

O banco é um arquivo SQLite dentro do container em `/data/app.db`.

No `docker-compose.yml`, esse diretório é mapeado para a pasta **local** `./data`:

- Arquivo no host: `./data/app.db`

Isso garante que o banco persista ao reiniciar os containers.

### Como validar rapidamente

1. Suba o app: `docker compose up --build`
2. Abra http://localhost:3000 e clique em **"Incrementar"** algumas vezes (o número de **"Visitas persistidas"** deve aumentar)
3. Pare e suba novamente: `docker compose down` e depois `docker compose up`
4. O valor de **"Visitas persistidas"** deve permanecer

## Backup

Como o banco está em um arquivo no host, basta copiar:

```bash
cp ./data/app.db ./backup-app.db
```

> Dica: pare os containers (`docker compose down`) antes de copiar o arquivo para um backup mais consistente.
