from flask import Flask, request, jsonify

from common import get_mysql_connection

app = Flask(__name__)

NIVEL_MINIMO_DELETE_GLOBAL = 5

analistas = [
    (1, "ana", "key-ana-001", 5),
    (2, "bruno", "key-bruno-002", 2),
]
incidentes = [
    (1, 1, "Brute force SSH", "critica", "aberto"),
    (2, 2, "Phishing no RH", "media", "aberto"),
]


def preparar_tabelas():
    conn = get_mysql_connection()
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS incidentes")
    cursor.execute("DROP TABLE IF EXISTS analistas")
    cursor.execute(
        """
        CREATE TABLE analistas (
            id INT PRIMARY KEY, nome VARCHAR(100),
            api_key VARCHAR(100) UNIQUE, nivel INT
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE incidentes (
            id INT PRIMARY KEY, dono_id INT, titulo VARCHAR(200),
            severidade VARCHAR(20), status VARCHAR(20)
        )
        """
    )
    cursor.executemany(
        "INSERT INTO analistas (id, nome, api_key, nivel) VALUES (%s, %s, %s, %s)", analistas
    )
    cursor.executemany(
        "INSERT INTO incidentes (id, dono_id, titulo, severidade, status) VALUES (%s, %s, %s, %s, %s)",
        incidentes,
    )
    conn.commit()
    cursor.close()
    conn.close()


def autenticar():
    """Retorna (analista, erro_response) — erro_response é None se autenticado."""
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        return None, (jsonify({"erro": "credencial ausente"}), 401)

    conn = get_mysql_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM analistas WHERE api_key = %s", (api_key,))
    analista = cursor.fetchone()
    cursor.close()
    conn.close()

    if analista is None:
        return None, (jsonify({"erro": "credencial inválida"}), 401)

    return analista, None


@app.route("/api/incidentes/<int:incidente_id>", methods=["GET"])
def obter_incidente(incidente_id):
    analista, erro = autenticar()
    if erro:
        return erro

    conn = get_mysql_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM incidentes WHERE id = %s", (incidente_id,))
    incidente = cursor.fetchone()
    cursor.close()
    conn.close()

    if incidente is None:
        return jsonify({"erro": "não encontrado"}), 404

    # IDOR: só o dono (ou nível >= 5) pode ver
    if incidente["dono_id"] != analista["id"] and analista["nivel"] < NIVEL_MINIMO_DELETE_GLOBAL:
        # não revela se o incidente existe ou não além do que já foi dito
        return jsonify({"erro": "acesso não permitido"}), 403

    return jsonify(incidente), 200


@app.route("/api/incidentes", methods=["GET"])
def listar_incidentes():
    analista, erro = autenticar()
    if erro:
        return erro

    conn = get_mysql_connection()
    cursor = conn.cursor(dictionary=True)
    if analista["nivel"] >= NIVEL_MINIMO_DELETE_GLOBAL:
        cursor.execute("SELECT * FROM incidentes")
    else:
        cursor.execute("SELECT * FROM incidentes WHERE dono_id = %s", (analista["id"],))
    resultado = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify(resultado), 200


@app.route("/api/incidentes/<int:incidente_id>", methods=["DELETE"])
def remover_incidente(incidente_id):
    analista, erro = autenticar()
    if erro:
        return erro

    if analista["nivel"] < NIVEL_MINIMO_DELETE_GLOBAL:
        return jsonify({"erro": "nível insuficiente"}), 403

    conn = get_mysql_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM incidentes WHERE id = %s", (incidente_id,))
    if cursor.fetchone() is None:
        cursor.close()
        conn.close()
        return jsonify({"erro": "não encontrado"}), 404

    cursor.execute("DELETE FROM incidentes WHERE id = %s", (incidente_id,))
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"removido": incidente_id}), 200


if __name__ == "__main__":
    preparar_tabelas()
    app.run(debug=True, host="0.0.0.0", port=5006)
