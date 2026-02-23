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
- http://localhost:3000/csv (importar/exportar CSV)

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

## CSV (importar/exportar)

Acesse a tela de CSV em:

- http://localhost:3000/csv

### Template de produtos

Baixe um template com as colunas esperadas:

- `GET /csv/template/produtos.csv`

Colunas (produtos):

- `sku` (obrigatório)
- `nome` (obrigatório)
- `categoria`
- `fornecedor`
- `custo`
- `preco`
- `quantidade_atual`
- `estoque_minimo`

### Importação de produtos

- Cria um novo produto quando o `sku` ainda não existe
- Atualiza o produto quando o `sku` já existe
- Relata erros por linha (ex.: campos obrigatórios ausentes ou números inválidos) sem derrubar a aplicação

### Exportação

- Produtos: `GET /csv/export/produtos.csv`
- Movimentações (opcional): `GET /csv/export/movimentacoes.csv`
