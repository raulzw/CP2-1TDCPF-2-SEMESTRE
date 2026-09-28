from datetime import datetime

from common import get_mysql_connection, get_mongo_db

usuarios = [
    (1, "ana", "ana@x.com", 5),
    (2, "bruno", "bruno@x.com", 2),
    (3, "caio", "caio@x.com", 1),
]

NIVEL_MINIMO_ADMIN = 5


def preparar_mysql(conn, cursor):
    cursor.execute("DROP TABLE IF EXISTS usuarios")
    cursor.execute(
        """
        CREATE TABLE usuarios (
            id INT PRIMARY KEY,
            nome VARCHAR(100),
            email VARCHAR(100),
            nivel_acesso INT
        )
        """
    )
    cursor.executemany(
        "INSERT INTO usuarios (id, nome, email, nivel_acesso) VALUES (%s, %s, %s, %s)",
        usuarios,
    )
    conn.commit()


def _buscar_nivel(cursor, user_id):
    cursor.execute("SELECT nivel_acesso FROM usuarios WHERE id = %s", (user_id,))
    row = cursor.fetchone()
    return row[0] if row else None


def _registrar_auditoria(auditoria_col, quem, alvo, nivel_anterior, nivel_novo, resultado):
    auditoria_col.insert_one(
        {
            "quem": quem,
            "alvo": alvo,
            "nivel_anterior": nivel_anterior,
            "nivel_novo": nivel_novo,
            "resultado": resultado,
            "timestamp": datetime.utcnow(),
        }
    )


def alterar_nivel(conn, cursor, auditoria_col, admin_id, alvo_id, novo_nivel):
    nivel_admin = _buscar_nivel(cursor, admin_id)

    if admin_id == alvo_id:
        _registrar_auditoria(auditoria_col, admin_id, alvo_id, nivel_admin, novo_nivel, "RECUSADO")
        return False, "auto-promoção não permitida"

    if nivel_admin is None or nivel_admin < NIVEL_MINIMO_ADMIN:
        nivel_alvo_atual = _buscar_nivel(cursor, alvo_id)
        _registrar_auditoria(auditoria_col, admin_id, alvo_id, nivel_alvo_atual, novo_nivel, "RECUSADO")
        return False, "admin sem privilégio"

    nivel_alvo_atual = _buscar_nivel(cursor, alvo_id)
    if nivel_alvo_atual is None:
        _registrar_auditoria(auditoria_col, admin_id, alvo_id, None, novo_nivel, "RECUSADO")
        return False, "alvo inexistente"

    try:
        cursor.execute(
            "UPDATE usuarios SET nivel_acesso = %s WHERE id = %s", (novo_nivel, alvo_id)
        )
        conn.commit()
    except Exception:
        conn.rollback()
        _registrar_auditoria(auditoria_col, admin_id, alvo_id, nivel_alvo_atual, novo_nivel, "RECUSADO")
        return False, "erro de banco"

    _registrar_auditoria(auditoria_col, admin_id, alvo_id, nivel_alvo_atual, novo_nivel, "OK")
    return True, None


def _nome(cursor, user_id):
    cursor.execute("SELECT nome, nivel_acesso FROM usuarios WHERE id = %s", (user_id,))
    row = cursor.fetchone()
    return row if row else (f"id{user_id}", None)


def main():
    conn = get_mysql_connection()
    conn.autocommit = False
    cursor = conn.cursor()
    preparar_mysql(conn, cursor)

    db = get_mongo_db()
    auditoria_col = db["auditoria"]
    auditoria_col.delete_many({})

    testes = [
        (1, 2, 4),
        (2, 3, 5),
        (1, 1, 9),
        (1, 99, 3),
    ]

    for admin_id, alvo_id, novo_nivel in testes:
        ok, motivo = alterar_nivel(conn, cursor, auditoria_col, admin_id, alvo_id, novo_nivel)
        nome_alvo, nivel_atual = _nome(cursor, alvo_id)
        if ok:
            print(f"alterar_nivel({admin_id}, {alvo_id}, {novo_nivel}) -> OK. commit. {nome_alvo}: -> {nivel_atual}")
        else:
            print(f"alterar_nivel({admin_id}, {alvo_id}, {novo_nivel}) -> RECUSADO ({motivo}). rollback. {nome_alvo}: {nivel_atual}")

    total_auditoria = auditoria_col.count_documents({})
    recusados = auditoria_col.count_documents({"resultado": "RECUSADO"})
    print(f"\nTrilha de auditoria ao final: {total_auditoria} documentos")
    print(f'db.auditoria.count_documents({{"resultado":"RECUSADO"}}) -> {recusados}')

    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()
