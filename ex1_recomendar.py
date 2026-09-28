def recomendar(perfil):
    schema_fixo = perfil["schema_fixo"]
    precisa_acid = perfil["precisa_acid"]
    escala_horizontal = perfil["escala_horizontal"]
    tolera_atraso = perfil["tolera_atraso_de_consistencia"]
    dado_sensivel = perfil["dado_sensivel"]

    if schema_fixo and precisa_acid:
        banco = "MySQL"
        cap = "CP"
        justificativa = (
            "autenticar/cobrar errado (dado inconsistente) é pior do que "
            "recusar a operação e ficar temporariamente indisponível"
        )
        risco_owasp = "A07"  # falha de autenticação, se o cenário for de credenciais
        if not _tem_relacao_com_autenticacao(perfil):
            risco_owasp = "A08"  # integridade de dados: registro inconsistente sem detectar

    elif schema_fixo and not precisa_acid and dado_sensivel:
        # cenário tipo "cache de sessão": o schema é fixo (chave/valor previsível),
        # não exige ACID, mas guarda dado sensível — o erro inaceitável aqui é
        # de CONTROLE DE ACESSO, não de disponibilidade ou consistência
        banco = "MongoDB" if escala_horizontal else "MySQL"
        cap = "AP" if escala_horizontal and tolera_atraso else "CP"
        justificativa = (
            "uma sessão sequestrada por falha de controle de acesso "
            "compromete a conta inteira; disponibilidade sem controle "
            "de acesso correto é uma falsa economia"
        )
        risco_owasp = "A01"  # quebra de controle de acesso

    elif not precisa_acid and not tolera_atraso and dado_sensivel:
        banco = "MongoDB"
        cap = "CP"
        justificativa = (
            "um registro de auditoria fora de ordem ou duplicado não serve "
            "como prova; é melhor recusar a escrita do que aceitar um "
            "evento divergente da realidade"
        )
        risco_owasp = "A08"  # integridade de software e dados

    elif not precisa_acid and escala_horizontal and tolera_atraso:
        banco = "MongoDB"
        cap = "AP"
        justificativa = (
            "perder alguns segundos de atualização (consistência) é aceitável, "
            "mas parar de aceitar escrita (indisponibilidade) descarta dado "
            "que nunca mais existirá"
        )
        risco_owasp = "A09"  # se o dado é telemetria/log, indisponibilidade = ponto cego

    else:
        banco = "MongoDB" if escala_horizontal else "MySQL"
        cap = "AP" if tolera_atraso else "CP"
        justificativa = (
            "sem exigência forte de ACID nem de consistência imediata, o "
            "maior risco é o serviço parar de responder sob carga"
        )
        risco_owasp = "A09"

    return {
        "banco": banco,
        "cap": cap,
        "justificativa": justificativa,
        "risco_owasp": risco_owasp,
    }


def _tem_relacao_com_autenticacao(perfil):
    # heurística simples só para nomear o risco corretamente nos exemplos
    return perfil.get("dado_sensivel") and not perfil.get("escala_horizontal")


perfis = {
    "credenciais_do_SOC": {"schema_fixo": True, "precisa_acid": True, "escala_horizontal": False, "tolera_atraso_de_consistencia": False, "dado_sensivel": True},
    "telemetria_de_sensores": {"schema_fixo": False, "precisa_acid": False, "escala_horizontal": True, "tolera_atraso_de_consistencia": True, "dado_sensivel": False},
    "trilha_de_auditoria": {"schema_fixo": False, "precisa_acid": False, "escala_horizontal": True, "tolera_atraso_de_consistencia": False, "dado_sensivel": True},
    "carrinho_de_licencas": {"schema_fixo": True, "precisa_acid": True, "escala_horizontal": False, "tolera_atraso_de_consistencia": False, "dado_sensivel": False},
    "cache_de_sessoes": {"schema_fixo": True, "precisa_acid": False, "escala_horizontal": True, "tolera_atraso_de_consistencia": True, "dado_sensivel": True},
}


def main():
    for nome, perfil in perfis.items():
        r = recomendar(perfil)
        print(f"{nome:24s} -> {r['banco']:7s} | {r['cap']} | \"{r['justificativa']}\" | {r['risco_owasp']}")


if __name__ == "__main__":
    main()
