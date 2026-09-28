import random
from datetime import datetime, timedelta

from common import get_mongo_db

SEGUNDOS_EM_7_DIAS = 7 * 24 * 60 * 60


def gerar_eventos(qtd=200):
    agora = datetime.utcnow()
    eventos = []
    for _ in range(qtd):
        offset_horas = random.uniform(0, 24)
        timestamp = agora - timedelta(hours=offset_horas)
        tipo = random.choices(["FAIL", "OK"], weights=[0.4, 0.6])[0]
        eventos.append({"tipo": tipo, "timestamp": timestamp})
    return eventos


def criar_indice_ttl(col):
    # expira o documento 7 dias após o valor do campo `timestamp`
    col.create_index("timestamp", expireAfterSeconds=SEGUNDOS_EM_7_DIAS)


def falhas_por_hora(col):
    pipeline = [
        {"$match": {"tipo": "FAIL"}},
        {"$group": {"_id": {"$hour": "$timestamp"}, "total": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]
    return list(col.aggregate(pipeline))


def imprimir_barra(hora, total, maximo):
    largura = 40
    tamanho_barra = int((total / maximo) * largura) if maximo else 0
    barra = "█" * tamanho_barra
    marcador = "  <- pico" if total == maximo else ""
    print(f"{hora:02d}h | {barra} {total}{marcador}")


def main():
    db = get_mongo_db()
    col = db["eventos"]
    col.delete_many({})

    criar_indice_ttl(col)

    eventos = gerar_eventos(200)
    col.insert_many(eventos)

    resultado = falhas_por_hora(col)
    if not resultado:
        print("Nenhuma falha no período.")
        return

    maximo = max(r["total"] for r in resultado)

    print("=== Falhas por hora (últimas 24h) ===")
    for r in resultado:
        imprimir_barra(r["_id"], r["total"], maximo)

    pico = max(resultado, key=lambda r: r["total"])
    print(f"Hora de pico: {pico['_id']:02d}h ({pico['total']} falhas)")
    print("Índice TTL ativo: eventos com mais de 7 dias serão removidos automaticamente.")

    # Comentário: o TTL não é só limpeza de disco — é uma decisão de
    # segurança: reter log além do necessário aumenta a superfície de
    # exposição em caso de vazamento (dado antigo que ninguém mais
    # monitora, mas que ainda identifica pessoas/IPs, vira passivo).


if __name__ == "__main__":
    main()
