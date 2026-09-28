from flask import Flask, request, jsonify

from common import get_mysql_connection

app = Flask(__name__)

COLUNAS = {"data": "criado_em", "sev": "severidade", "ip": "ip_origem"}
ORDEM = {"asc": "ASC", "desc": "DESC"}
TAMANHO_MAXIMO = 100
TAMANHO_PADRAO = 20


def preparar_tabela():
    conn = get_mysql_connection()
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS eventos")
    cursor.execute(
        """
        CREATE TABLE eventos (
            id INT AUTO_INCREMENT PRIMARY KEY,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            severidade VARCHAR(20),
            ip_origem VARCHAR(45)
        )
        """
    )
    severidades = ["baixa", "media", "alta", "critica"]
    for i in range(30):
        cursor.execute(
            "INSERT INTO eventos (severidade, ip_origem) VALUES (%s, %s)",
            (severidades[i % 4], f"192.168.1.{i % 255}"),
        )
    conn.commit()
    cursor.close()
    conn.close()


@app.route("/api/eventos")
def listar_eventos():
    ordenar_por = request.args.get("ordenar_por", "data")
    ordem = request.args.get("ordem", "desc")
    tamanho_raw = request.args.get("tamanho", str(TAMANHO_PADRAO))

    if ordenar_por not in COLUNAS:
        return jsonify({"erro": "campo de ordenação inválido"}), 400

    if ordem.lower() not in ORDEM:
        return jsonify({"erro": "ordem inválida"}), 400

    try:
        tamanho = int(tamanho_raw)
    except ValueError:
        return jsonify({"erro": "tamanho deve ser inteiro"}), 400

    if tamanho <= 0:
        return jsonify({"erro": "tamanho deve ser positivo"}), 400

    tamanho = min(tamanho, TAMANHO_MAXIMO)

    coluna_sql = COLUNAS[ordenar_por]
    ordem_sql = ORDEM[ordem.lower()]

    conn = get_mysql_connection()
    cursor = conn.cursor(dictionary=True)
    # `coluna_sql` e `ordem_sql` vêm SOMENTE das whitelists acima —
    # nunca do texto bruto do usuário — por isso é seguro interpolar
    # aqui. `tamanho` já foi validado como inteiro antes de entrar na
    # query (LIMIT aceita parâmetro normal via %s).
    query = f"SELECT * FROM eventos ORDER BY {coluna_sql} {ordem_sql} LIMIT %s"
    cursor.execute(query, (tamanho,))
    resultado = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify(resultado), 200


if __name__ == "__main__":
    preparar_tabela()
    app.run(debug=True, host="0.0.0.0", port=5005)
