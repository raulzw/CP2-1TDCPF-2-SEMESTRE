from common import get_mysql_connection, get_mongo_db

ativos = [
    (1, "SRV-WEB01", "192.168.1.10", "alta"),
    (2, "PC-RH03", "192.168.1.45", "baixa"),
]
alertas = [
    (1, 1, "BRUTE_FORCE", "critica"),
    (2, 1, "PORT_SCAN", "alta"),
    (3, 2, "XSS", "media"),
]


def preparar_mysql(conn, cursor):
    cursor.execute("DROP TABLE IF EXISTS alertas")
    cursor.execute("DROP TABLE IF EXISTS ativos")
    cursor.execute(
        """
        CREATE TABLE ativos (
            id INT PRIMARY KEY,
            nome VARCHAR(100),
            ip VARCHAR(45) UNIQUE,
            criticidade ENUM('baixa', 'media', 'alta')
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE alertas (
            id INT PRIMARY KEY,
            ativo_id INT,
            tipo VARCHAR(50),
            severidade VARCHAR(20),
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ativo_id) REFERENCES ativos(id)
        )
        """
    )
    cursor.executemany(
        "INSERT INTO ativos (id, nome, ip, criticidade) VALUES (%s, %s, %s, %s)", ativos
    )
    cursor.executemany(
        "INSERT INTO alertas (id, ativo_id, tipo, severidade) VALUES (%s, %s, %s, %s)", alertas
    )
    conn.commit()


def ler_com_join(cursor):
    # query parametrizada mesmo sem parâmetros externos aqui — mantém o
    # padrão seguro em todo o CP
    cursor.execute(
        """
        SELECT al.tipo, al.severidade, at.nome, at.ip, at.criticidade
        FROM alertas al
        JOIN ativos at ON at.id = al.ativo_id
        """
    )
    return cursor.fetchall()


def montar_documentos(linhas):
    documentos = []
    for tipo, severidade, nome, ip, criticidade in linhas:
        documentos.append(
            {
                "tipo": tipo,
                "severidade": severidade,
                "ativo": {"nome": nome, "ip": ip, "criticidade": criticidade},
            }
        )
    return documentos


def main():
    conn = get_mysql_connection()
    cursor = conn.cursor()
    preparar_mysql(conn, cursor)

    linhas = ler_com_join(cursor)
    documentos = montar_documentos(linhas)

    db = get_mongo_db()
    col = db["alertas_migrados"]
    col.delete_many({})
    col.insert_many(documentos)

    # verificação: conta nos dois lados
    cursor.execute("SELECT COUNT(*) FROM alertas")
    total_mysql = cursor.fetchone()[0]
    total_mongo = col.count_documents({})

    status = "MIGRAÇÃO ÍNTEGRA" if total_mysql == total_mongo else "DIVERGÊNCIA! revisar"
    print(f"MySQL: {total_mysql} alertas | MongoDB: {total_mongo} documentos -> {status}")

    alta_criticidade = col.count_documents({"ativo.criticidade": "alta"})
    print(f'Consulta sem JOIN: db.alertas.find({{"ativo.criticidade":"alta"}}) -> {alta_criticidade} documentos')

    # Comentário:
    # Ganha-se leitura direta sem JOIN (o dado do ativo já vem junto no
    # documento do alerta, ótimo para consultas de leitura frequentes).
    # Perde-se em duplicação: se o nome/IP do ativo mudar, é preciso um
    # update_many em todos os alertas que o referenciam, e não um UPDATE
    # único como no relacional.

    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()
