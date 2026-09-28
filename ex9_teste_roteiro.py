from ex9_api_rate_limit import app, analisar_acessos, imprimir_relatorio


def simular_ips_normais(client):
    # 8 IPs legítimos, com poucas requisições cada (população de referência
    # para o IsolationForest ter com quem comparar o IP hostil)
    quantidades = [3, 4, 5, 5, 6, 6, 7, 8]
    for i, qtd in enumerate(quantidades):
        ip = f"192.168.1.{10 + i}"
        for _ in range(qtd):
            client.get("/api/status", environ_overrides={"REMOTE_ADDR": ip})


def simular_ip_hostil(client):
    for i in range(60):
        if i % 3 == 0:
            client.get("/api/rota-que-nao-existe-x", environ_overrides={"REMOTE_ADDR": "185.220.101.1"})
        else:
            client.get("/api/status", environ_overrides={"REMOTE_ADDR": "185.220.101.1"})


def main():
    client = app.test_client()

    simular_ips_normais(client)
    simular_ip_hostil(client)

    dados = analisar_acessos(janela_segundos=60)
    imprimir_relatorio(dados)

    resposta = client.get("/api/status", environ_overrides={"REMOTE_ADDR": "185.220.101.1"})
    print(f"\nPróxima requisição de 185.220.101.1 -> {resposta.status_code}", end=" ")
    if resposta.status_code == 429:
        print(f"{resposta.get_json()}  Retry-After: {resposta.headers.get('Retry-After')}")
    else:
        print()


if __name__ == "__main__":
    main()
