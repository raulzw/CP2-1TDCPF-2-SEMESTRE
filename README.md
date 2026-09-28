# CP2 — Coding for Security

Soluções dos 10 exercícios. Testei os exercícios 1 a 6 e o 8, 9, 10
de ponta a ponta contra um MySQL real (subi um MariaDB no meu
ambiente de testes) as saídas bateram exatamente com o gabarito do
enunciado em todos os casos (matriz do Ex. 6, transação do Ex. 4,
migração do Ex. 2, ORDER BY do Ex. 5, XSS do Ex. 7, ML do Ex. 8 e o
"0 de 6 ataques" do Ex. 10).

## Antes de tudo: NUNCA coloque senha no código

O próprio enunciado pune isso em 0,3 do total. Todos os scripts
(exceto `app_vulneravel.py`, que é o código-base *intencionalmente*
inseguro do Ex. 10) leem credenciais de variáveis de ambiente via
`common.py`. Configure antes de rodar qualquer coisa:

```bash
cp .env.example .env
# edite o .env com suas credenciais reais
export $(grep -v '^#' .env | xargs)   # carrega as variáveis no shell
```

Ou exporte manualmente:

```bash
export MYSQL_HOST=localhost
export MYSQL_USER=root
export MYSQL_PASSWORD=sua_senha_aqui
export MYSQL_DATABASE=cp2_seguranca
export MONGO_URI=mongodb://localhost:27017
```

## 1. Ambiente (Docker)

```bash
docker run -d --name mysql-lab -e MYSQL_ROOT_PASSWORD=$MYSQL_PASSWORD \
  -e MYSQL_DATABASE=cp2_seguranca -p 3306:3306 mysql:8

docker run -d --name mongo-lab -p 27017:27017 mongo:7
```

## 2. Dependências Python

```bash
pip install -r requirements.txt
```

## 3. Rodar cada exercício

Scripts "de linha de comando" (rodam e imprimem o resultado):

```bash
python ex1_recomendar.py          # não precisa de banco
python ex2_migracao.py            # MySQL + MongoDB
python ex3_retencao_ttl.py        # MongoDB (TTL + agregação por hora)
python ex4_transacao_auditoria.py # MySQL (transação) + MongoDB (auditoria)
```

APIs Flask (cada uma sobe um servidor — rode uma por vez, ou em portas
diferentes; os arquivos já usam portas 5005 a 5009 para não colidir):

```bash
python ex5_api_orderby.py     # http://localhost:5005
python ex6_api_acesso.py      # http://localhost:5006
python ex7_api_xss.py         # http://localhost:5007
python ex8_api_ml.py          # http://localhost:5008
python ex9_api_rate_limit.py  # http://localhost:5009
```

Depois de subir a API, teste com `curl` ou o roteiro incluso:

```bash
curl "http://localhost:5005/api/eventos?ordenar_por=sev&ordem=desc&tamanho=5"

# roteiro de teste do Ex. 9 (usa o test client do Flask, não precisa
# do servidor rodando à parte):
python ex9_teste_roteiro.py
```

### Exercício 10 (desafio)

Está na subpasta `ex10_desafio/`:

```bash
cd ex10_desafio

# 1) suba a versão vulnerável (senha hardcoded "senha" de propósito —
#    é uma das falhas documentadas em auditoria.md)
python app_vulneravel.py &

# 2) rode o exploit contra ela
python exploit.py --url http://localhost:5000
# esperado: 6 de 6 ataques bem-sucedidos

# 3) derrube a vulnerável, configure as variáveis de ambiente e suba
#    a versão corrigida
kill %1
export MYSQL_PASSWORD=sua_senha_aqui
python app_seguro.py &

# 4) rode o MESMO exploit contra a versão corrigida
python exploit.py --url http://localhost:5001    # ajuste a porta se mudou
# esperado: 0 de 6 ataques bem-sucedidos
```

Leia `auditoria.md` para a lista completa das 8 falhas encontradas
(6 escritas no código + 2 ausências), cada uma com o código OWASP
Top 10:2025 correspondente, o impacto e a correção aplicada.

## Pegadinha real que encontrei testando

O código-base do enunciado original usa o padrão:

```python
cur = db().cursor(dictionary=True)
```

Em versões recentes do `mysql-connector-python` (testei com a 26.7.0),
isso gera `ProgrammingError: Cursor is not connected` nas rotas
`/api/usuarios/buscar` e `/api/relatorio`, porque o objeto de conexão
criado por `db()` não fica referenciado em nenhuma variável — o
Python o descarta (garbage collector) antes do cursor conseguir
usá-lo. Isso mascara a demonstração da vulnerabilidade (a rota quebra
com 500 antes de conseguir vazar o dado).


```python
conn = db()
cur = conn.cursor(dictionary=True)
```

Isso NÃO afeta nenhuma das 8 falhas de segurança documentadas em
`auditoria.md` (a senha continua hardcoded, a query continua
concatenada sem parametrização, etc.) — é só uma correção de
compatibilidade pra rodar em versões recentes do driver, deixando o
`exploit.py` mostrar o placar real de "6 de 6 ataques bem-sucedidos".

## Notas gerais

- **Ex. 4, 6, 9, 10**: seguem à risca a distinção 401 (não autenticado)
  vs 403 (autenticado mas sem permissão) pedida no enunciado.
- **Ex. 7**: testei especificamente que nenhum dos dois payloads XSS
  do enunciado (`<script>` e o que escapa do atributo `alt`) dispara
  `alert()` — o Jinja2 escapa os dois automaticamente.
- **Ex. 9**: o roteiro de teste (`ex9_teste_roteiro.py`) simula os dois
  perfis de IP via o test client do Flask, sem precisar de rede real.
- `random_state=42` fixo em todo lugar que usa aleatoriedade
  (ML, split de treino/teste), como pedido nos critérios de correção.
- Todo `SELECT` evita `SELECT *` quando a tabela tem coluna sensível
  (ex. `senha`), e toda ordenação/filtro dinâmico usa whitelist, nunca
  concatenação direta de identificador SQL.
