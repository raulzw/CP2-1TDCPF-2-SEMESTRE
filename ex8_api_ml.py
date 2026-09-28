from datetime import datetime

import numpy as np
from flask import Flask, request, jsonify
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
)

from common import get_mongo_db

app = Flask(__name__)

NUM_FEATURES = 4  # falhas_login, portas_distintas, bytes_saida, hora_do_dia

# dataset sintético de treino: perfis de risco alto (1) e baixo (0)
X_treino_completo = np.array([
    [12, 7, 90000, 3], [10, 6, 80000, 2], [15, 9, 100000, 4], [8, 5, 70000, 1],
    [0, 1, 1200, 14], [1, 1, 1500, 10], [0, 2, 900, 9], [2, 1, 2000, 15],
    [11, 8, 95000, 3], [1, 2, 1800, 11], [0, 1, 1000, 13], [14, 10, 110000, 2],
])
y_treino_completo = np.array([1, 1, 1, 1, 0, 0, 0, 0, 1, 0, 0, 1])

X_train, X_test, y_train, y_test = train_test_split(
    X_treino_completo, y_treino_completo, test_size=0.3, random_state=42
)

modelo = RandomForestClassifier(random_state=42)
modelo.fit(X_train, y_train)


def validar_features(payload):
    if not payload or "features" not in payload:
        return None, "corpo da requisição deve conter 'features'"

    features = payload["features"]
    if not isinstance(features, list) or len(features) != NUM_FEATURES:
        return None, f"esperadas {NUM_FEATURES} features, recebidas {len(features) if isinstance(features, list) else 0}"

    for f in features:
        if isinstance(f, bool) or not isinstance(f, (int, float)):
            return None, "features devem ser numéricas"

    return features, None


@app.route("/api/triagem", methods=["POST"])
def triagem():
    payload = request.get_json(silent=True)
    features, erro = validar_features(payload)
    if erro:
        return jsonify({"erro": erro}), 400

    X = np.array([features])
    pred = modelo.predict(X)[0]
    proba = modelo.predict_proba(X)[0]
    confianca = float(max(proba))
    risco = "alto" if pred == 1 else "baixo"

    db = get_mongo_db()
    db["previsoes"].insert_one(
        {
            "entrada": features,
            "saida": risco,
            "confianca": confianca,
            "timestamp": datetime.utcnow(),
        }
    )

    return jsonify({"risco": risco, "confianca": round(confianca, 2)}), 200


@app.route("/api/modelo/metricas", methods=["GET"])
def metricas():
    y_pred = modelo.predict(X_test)
    precisao = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    matriz = confusion_matrix(y_test, y_pred).tolist()

    return jsonify(
        {
            "precisao": round(float(precisao), 2),
            "recall": round(float(recall), 2),
            "f1": round(float(f1), 2),
            "matriz": matriz,
            "aviso": (
                "acurácia foi omitida de propósito: com poucas amostras de "
                "risco alto no conjunto de teste, ela mascararia falsos "
                "negativos exatamente como no Exercício 9 do CP1 — "
                "precisão/recall/F1 contam a história real do modelo"
            ),
        }
    ), 200


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5008)
