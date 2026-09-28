from datetime import datetime, timedelta

from flask import Flask, request, jsonify, g
from sklearn.ensemble import IsolationForest

from common import get_mongo_db

app = Flask(__name__)

IPS_BLOQUEADOS = set()  # cache em memória dos IPs já marcados como anômalos


@app.before_request
def registrar_inicio():
    g._inicio_registro = {
        "ip": request.remote_addr or "desconhecido",
        "rota": request.path,
        "metodo": request.method,
        "timestamp": datetime.utcnow(),
    }

    if g._inicio_registro["ip"] in IPS_BLOQUEADOS:
        resposta = jsonify({"erro": "muitas requisições"})
        resposta.status_code = 429
        resposta.headers["Retry-After"] = "60"
        return resposta


@app.after_request
def completar_registro(response):
    registro = getattr(g, "_inicio_registro", None)
    if registro is not None:
        registro["status"] = response.status_code
        db = get_mongo_db()
        db["acessos"].insert_one(registro)
    return response


def analisar_acessos(janela_segundos=60):
    """Agrega por IP e roda IsolationForest para marcar anomalias."""
    db = get_mongo_db()
    col = db["acessos"]

    desde = datetime.utcnow() - timedelta(seconds=janela_segundos)
    pipeline = [
        {"$match": {"timestamp": {"$gte": desde}}},
        {
            "$group": {
                "_id": "$ip",
                "total_requisicoes": {"$sum": 1},
                "total_4xx": {
                    "$sum": {
                        "$cond": [
                            {"$and": [{"$gte": ["$status", 400]}, {"$lt": ["$status", 500]}]},
                            1,
                            0,
                        ]
                    }
                },
                "rotas": {"$addToSet": "$rota"},
            }
        },
    ]
    resultado = list(col.aggregate(pipeline))
    if not resultado:
        return []

    dados = []
    for r in resultado:
        req_por_min = r["total_requisicoes"] / (janela_segundos / 60)
        taxa_4xx = r["total_4xx"] / r["total_requisicoes"] if r["total_requisicoes"] else 0
        rotas_distintas = len(r["rotas"])
        dados.append(
            {
                "ip": r["_id"],
                "req_por_min": req_por_min,
                "taxa_4xx": taxa_4xx,
                "rotas_distintas": rotas_distintas,
            }
        )

    features = [[d["req_por_min"], d["taxa_4xx"], d["rotas_distintas"]] for d in dados]

    if len(features) < 2:
        # IsolationForest precisa de mais de uma amostra para comparar
        for d in dados:
            d["anomalo"] = False
        return dados

    modelo = IsolationForest(contamination=0.1, random_state=42)
    predicoes = modelo.fit_predict(features)  # -1 = anomalia

    for d, pred in zip(dados, predicoes):
        d["anomalo"] = pred == -1
        if d["anomalo"]:
            IPS_BLOQUEADOS.add(d["ip"])

    return dados


@app.route("/api/status")
def status():
    return jsonify({"ok": True}), 200


@app.route("/api/rota-que-nao-existe-x")
def rota_inexistente_exemplo():
    return jsonify({"erro": "não encontrado"}), 404


def imprimir_relatorio(dados):
    print("=== Análise de acessos ===")
    for d in dados:
        status_txt = "ANOMALIA -> bloqueado" if d["anomalo"] else "normal"
        print(
            f"{d['ip']:15s} [ {d['req_por_min']:.1f} req/min | "
            f"4xx {d['taxa_4xx']:.2f} | {d['rotas_distintas']} rotas]  -> {status_txt}"
        )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5009)
