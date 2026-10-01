from pathlib import Path
import struct


# ============================================================
# MICROETAPA 41
# GERENCIADOR AUTOMÁTICO DO CRISTAL
# MEMÓRIA IDEMPOTENTE
#
# Novidade desta versão:
#
# Se uma experiência já existir exatamente no cristal,
# ela não será gravada novamente.
#
# Resultado esperado:
#
# experiência repetida
#       ↓
# DUPLICADO
#       ↓
# 0 bytes
#
# ============================================================


ARQUIVO = Path(
    "experimentos/cristal_gerenciador.bin"
)


# ============================================================
# DICIONÁRIO BASE
# ============================================================

CONCEITOS_BASE = [
    "hipótese",
    "observação",
    "experimento",
    "evidência",
    "resultado",
    "pergunta",
    "investigação",
    "dado",
    "padrão",
    "incerteza",
    "conclusão",
    "teoria",
    "explicação",
    "erro",
    "previsão",
    "nova",
    "correta",
    "incorreta",
    "provisória",
]


RELACOES_BASE = [
    "nasce_de",
    "pode_ser_testada_por",
    "pode_receber",
    "pode_ser_modificada_por",
    "pode_estar",
    "pode_gerar",
    "pode_testar",
    "pode_modificar",
    "continua_sendo",
    "precisa_lidar_com",
    "tem_caracteristica",
    "pode_ser_apoiada_por",
    "pode_ser_contradita_por",
    "pode_orientar",
    "pode_ser_revisada_por",
    "pode_conter",
    "pode_reduzir",
    "pode_explicar",
    "pode_gerar_previsao",
    "pode_conter_erro",
]


# ============================================================
# EXPERIÊNCIAS DE TESTE
# ============================================================

EXPERIENCIAS_TESTE = [
    (
        "observação",
        "pode_gerar",
        "hipótese",
    ),
    (
        "modelo",
        "pode_gerar_previsao",
        "previsão",
    ),
    (
        "evidência",
        "depende_de",
        "observação",
    ),
    (
        "simulação",
        "representa",
        "modelo",
    ),

    # Repetição exata da experiência 1
    (
        "observação",
        "pode_gerar",
        "hipótese",
    ),
]


# ============================================================
# FORMATO
# ============================================================

MAGIC = b"NXCM"
VERSAO = 1

TIPO_CONCEITO = 1
TIPO_RELACAO = 2
TIPO_BLOCO = 3


# ============================================================
# CODIFICAÇÃO
# ============================================================

def codificar_conceito(nome):
    dados = nome.encode("utf-8")

    if len(dados) > 255:
        raise ValueError(
            "Conceito excede 255 bytes."
        )

    return (
        bytes([TIPO_CONCEITO])
        + bytes([len(dados)])
        + dados
    )


def codificar_relacao(nome):
    dados = nome.encode("utf-8")

    if len(dados) > 255:
        raise ValueError(
            "Relação excede 255 bytes."
        )

    return (
        bytes([TIPO_RELACAO])
        + bytes([len(dados)])
        + dados
    )


def codificar_bloco(
    sujeito_id,
    relacao_id,
    objeto_id,
):
    if not 0 <= sujeito_id <= 255:
        raise ValueError(
            "ID de sujeito inválido."
        )

    if not 0 <= relacao_id <= 255:
        raise ValueError(
            "ID de relação inválido."
        )

    if not 0 <= objeto_id <= 255:
        raise ValueError(
            "ID de objeto inválido."
        )

    return (
        bytes([TIPO_BLOCO])
        + bytes([1])
        + struct.pack(
            "BBB",
            sujeito_id,
            relacao_id,
            objeto_id,
        )
    )


# ============================================================
# LEITURA DE STRING
# ============================================================

def ler_string(
    dados,
    posicao,
):
    if posicao >= len(dados):
        raise ValueError(
            "String ausente."
        )

    tamanho = dados[posicao]
    posicao += 1

    fim = posicao + tamanho

    if fim > len(dados):
        raise ValueError(
            "String incompleta."
        )

    texto = dados[posicao:fim].decode(
        "utf-8"
    )

    return texto, fim


# ============================================================
# LEITURA DO CRISTAL
# ============================================================

def ler_arquivo():
    dados = ARQUIVO.read_bytes()

    if len(dados) < 5:
        raise ValueError(
            "Cristal pequeno demais."
        )

    if dados[:4] != MAGIC:
        raise ValueError(
            "MAGIC inválido."
        )

    if dados[4] != VERSAO:
        raise ValueError(
            f"Versão inválida: {dados[4]}"
        )

    posicao = 5

    conceitos = {}
    relacoes = {}
    blocos = []

    while posicao < len(dados):
        tipo = dados[posicao]
        posicao += 1

        # ----------------------------------------------------
        # CONCEITO
        # ----------------------------------------------------

        if tipo == TIPO_CONCEITO:
            nome, posicao = ler_string(
                dados,
                posicao,
            )

            if nome in conceitos:
                raise ValueError(
                    f"Conceito duplicado: {nome}"
                )

            conceitos[nome] = len(conceitos)

        # ----------------------------------------------------
        # RELAÇÃO
        # ----------------------------------------------------

        elif tipo == TIPO_RELACAO:
            nome, posicao = ler_string(
                dados,
                posicao,
            )

            if nome in relacoes:
                raise ValueError(
                    f"Relação duplicada: {nome}"
                )

            relacoes[nome] = len(relacoes)

        # ----------------------------------------------------
        # BLOCO
        # ----------------------------------------------------

        elif tipo == TIPO_BLOCO:
            if posicao >= len(dados):
                raise ValueError(
                    "Quantidade do bloco ausente."
                )

            quantidade = dados[posicao]
            posicao += 1

            bloco = []

            for _ in range(quantidade):
                if posicao + 3 > len(dados):
                    raise ValueError(
                        "Bloco incompleto."
                    )

                sujeito_id = dados[posicao]
                relacao_id = dados[posicao + 1]
                objeto_id = dados[posicao + 2]

                posicao += 3

                bloco.append(
                    (
                        sujeito_id,
                        relacao_id,
                        objeto_id,
                    )
                )

            blocos.append(bloco)

        else:
            raise ValueError(
                f"Tipo desconhecido: {tipo}"
            )

    return (
        conceitos,
        relacoes,
        blocos,
    )


# ============================================================
# RECONSTRUÇÃO
# ============================================================

def reconstruir_conhecimento(
    conceitos,
    relacoes,
    blocos,
):
    conceitos_invertidos = {
        indice: nome
        for nome, indice in conceitos.items()
    }

    relacoes_invertidas = {
        indice: nome
        for nome, indice in relacoes.items()
    }

    conhecimento = []

    for bloco in blocos:
        for (
            sujeito_id,
            relacao_id,
            objeto_id,
        ) in bloco:
            conhecimento.append(
                (
                    conceitos_invertidos[
                        sujeito_id
                    ],
                    relacoes_invertidas[
                        relacao_id
                    ],
                    conceitos_invertidos[
                        objeto_id
                    ],
                )
            )

    return conhecimento


# ============================================================
# INICIALIZAÇÃO
# ============================================================

def inicializar_cristal():
    ARQUIVO.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if ARQUIVO.exists():
        ARQUIVO.unlink()

    with open(
        ARQUIVO,
        "wb",
    ) as arquivo:
        arquivo.write(
            MAGIC + bytes([VERSAO])
        )

        for conceito in CONCEITOS_BASE:
            arquivo.write(
                codificar_conceito(
                    conceito
                )
            )

        for relacao in RELACOES_BASE:
            arquivo.write(
                codificar_relacao(
                    relacao
                )
            )


# ============================================================
# REGISTRAR EXPERIÊNCIA
# ============================================================

def registrar_experiencia(
    sujeito,
    relacao,
    objeto,
):
    (
        conceitos,
        relacoes,
        blocos,
    ) = ler_arquivo()

    experiencia = (
        sujeito,
        relacao,
        objeto,
    )

    # --------------------------------------------------------
    # CONHECIMENTO EXISTENTE
    # --------------------------------------------------------

    conhecimento_existente = (
        reconstruir_conhecimento(
            conceitos,
            relacoes,
            blocos,
        )
    )

    tamanho_antes = (
        ARQUIVO.stat().st_size
    )

    # --------------------------------------------------------
    # DETECÇÃO DE DUPLICAÇÃO
    # --------------------------------------------------------

    if experiencia in conhecimento_existente:
        return {
            "classificacao": "DUPLICADO",
            "novos_conceitos": [],
            "relacao_nova": False,
            "ids_novos_conceitos": {},
            "id_nova_relacao": None,
            "tamanho_antes": tamanho_antes,
            "tamanho_depois": tamanho_antes,
            "crescimento": 0,
            "total_conhecimento": len(
                conhecimento_existente
            ),
            "passou": True,
        }

    # --------------------------------------------------------
    # DETECTAR CONCEITOS NOVOS
    # --------------------------------------------------------

    novos_conceitos = []

    if sujeito not in conceitos:
        novos_conceitos.append(
            sujeito
        )

    if (
        objeto not in conceitos
        and objeto not in novos_conceitos
    ):
        novos_conceitos.append(
            objeto
        )

    relacao_nova = (
        relacao not in relacoes
    )

    quantidade_novos_conceitos = (
        len(novos_conceitos)
    )

    # --------------------------------------------------------
    # CLASSIFICAÇÃO
    # --------------------------------------------------------

    if (
        quantidade_novos_conceitos == 0
        and not relacao_nova
    ):
        classificacao = "REUTILIZAÇÃO"

    elif (
        quantidade_novos_conceitos > 0
        and not relacao_nova
    ):
        classificacao = "CONCEITO NOVO"

    elif (
        quantidade_novos_conceitos == 0
        and relacao_nova
    ):
        classificacao = "RELAÇÃO NOVA"

    else:
        classificacao = (
            "CONCEITO + RELAÇÃO NOVOS"
        )

    # --------------------------------------------------------
    # ADICIONAR CONCEITOS
    # --------------------------------------------------------

    novos_ids_conceitos = {}

    for nome in novos_conceitos:
        novo_id = len(conceitos)

        if novo_id > 255:
            raise ValueError(
                "Limite de conceitos atingido."
            )

        conceitos[nome] = novo_id

        novos_ids_conceitos[nome] = (
            novo_id
        )

    # --------------------------------------------------------
    # ADICIONAR RELAÇÃO
    # --------------------------------------------------------

    novo_id_relacao = None

    if relacao_nova:
        novo_id_relacao = len(relacoes)

        if novo_id_relacao > 255:
            raise ValueError(
                "Limite de relações atingido."
            )

        relacoes[relacao] = (
            novo_id_relacao
        )

    # --------------------------------------------------------
    # REGISTROS
    # --------------------------------------------------------

    registros = []

    for nome in novos_conceitos:
        registros.append(
            codificar_conceito(nome)
        )

    if relacao_nova:
        registros.append(
            codificar_relacao(relacao)
        )

    bloco = codificar_bloco(
        conceitos[sujeito],
        relacoes[relacao],
        conceitos[objeto],
    )

    registros.append(
        bloco
    )

    # --------------------------------------------------------
    # APPEND
    # --------------------------------------------------------

    with open(
        ARQUIVO,
        "ab",
    ) as arquivo:
        for registro in registros:
            arquivo.write(
                registro
            )

    tamanho_depois = (
        ARQUIVO.stat().st_size
    )

    crescimento = (
        tamanho_depois
        - tamanho_antes
    )

    # --------------------------------------------------------
    # VERIFICAÇÃO
    # --------------------------------------------------------

    (
        conceitos_depois,
        relacoes_depois,
        blocos_depois,
    ) = ler_arquivo()

    conhecimento_depois = (
        reconstruir_conhecimento(
            conceitos_depois,
            relacoes_depois,
            blocos_depois,
        )
    )

    passou = (
        conhecimento_depois[-1]
        == experiencia
    )

    return {
        "classificacao": classificacao,
        "novos_conceitos": novos_conceitos,
        "relacao_nova": relacao_nova,
        "ids_novos_conceitos": (
            novos_ids_conceitos
        ),
        "id_nova_relacao": (
            novo_id_relacao
        ),
        "tamanho_antes": tamanho_antes,
        "tamanho_depois": tamanho_depois,
        "crescimento": crescimento,
        "total_conhecimento": len(
            conhecimento_depois
        ),
        "passou": passou,
    }


# ============================================================
# IDS ANTIGOS
# ============================================================

def verificar_ids_originais(
    conceitos_originais,
    relacoes_originais,
):
    (
        conceitos,
        relacoes,
        _,
    ) = ler_arquivo()

    for nome, indice in conceitos_originais.items():
        if nome not in conceitos:
            return False

        if conceitos[nome] != indice:
            return False

    for nome, indice in relacoes_originais.items():
        if nome not in relacoes:
            return False

        if relacoes[nome] != indice:
            return False

    return True


# ============================================================
# PRINCIPAL
# ============================================================

def main():
    print(
        "=== MICROETAPA 41 ==="
    )

    print(
        "MEMÓRIA IDEMPOTENTE"
    )

    print()

    # --------------------------------------------------------
    # INICIALIZAÇÃO
    # --------------------------------------------------------

    inicializar_cristal()

    (
        conceitos,
        relacoes,
        blocos,
    ) = ler_arquivo()

    conceitos_originais = dict(
        conceitos
    )

    relacoes_originais = dict(
        relacoes
    )

    print(
        "=== ESTADO INICIAL ==="
    )

    print(
        f"Conceitos: "
        f"{len(conceitos)}"
    )

    print(
        f"Relações: "
        f"{len(relacoes)}"
    )

    print(
        f"Blocos: "
        f"{len(blocos)}"
    )

    print(
        f"Tamanho: "
        f"{ARQUIVO.stat().st_size} bytes"
    )

    print()

    # --------------------------------------------------------
    # PROCESSAMENTO
    # --------------------------------------------------------

    for numero, experiencia in enumerate(
        EXPERIENCIAS_TESTE,
        start=1,
    ):
        sujeito, relacao, objeto = (
            experiencia
        )

        print(
            f"=== EXPERIÊNCIA {numero} ==="
        )

        print(
            f"{sujeito} "
            f"--{relacao}--> "
            f"{objeto}"
        )

        resultado = (
            registrar_experiencia(
                sujeito,
                relacao,
                objeto,
            )
        )

        print(
            f"Classificação: "
            f"{resultado['classificacao']}"
        )

        if resultado[
            "novos_conceitos"
        ]:
            print(
                "Novos conceitos: "
                + ", ".join(
                    resultado[
                        "novos_conceitos"
                    ]
                )
            )
        else:
            print(
                "Novos conceitos: nenhum"
            )

        print(
            "Relação nova: "
            + (
                "sim"
                if resultado["relacao_nova"]
                else "não"
            )
        )

        print(
            f"Crescimento: "
            f"{resultado['crescimento']} bytes"
        )

        print(
            f"Total de conhecimento: "
            f"{resultado['total_conhecimento']}"
        )

        print(
            "Integridade: "
            + (
                "PASSOU"
                if resultado["passou"]
                else "FALHOU"
            )
        )

        print()

    # --------------------------------------------------------
    # IDS
    # --------------------------------------------------------

    ids_ok = verificar_ids_originais(
        conceitos_originais,
        relacoes_originais,
    )

    print(
        "=== IDS ANTIGOS ==="
    )

    if ids_ok:
        print(
            "PASSOU: todos os IDs antigos "
            "permaneceram intactos."
        )
    else:
        print(
            "FALHOU: algum ID antigo mudou."
        )

    print()

    # --------------------------------------------------------
    # FINAL
    # --------------------------------------------------------

    (
        conceitos_finais,
        relacoes_finais,
        blocos_finais,
    ) = ler_arquivo()

    conhecimento_final = (
        reconstruir_conhecimento(
            conceitos_finais,
            relacoes_finais,
            blocos_finais,
        )
    )

    esperado = [
        EXPERIENCIAS_TESTE[0],
        EXPERIENCIAS_TESTE[1],
        EXPERIENCIAS_TESTE[2],
        EXPERIENCIAS_TESTE[3],
    ]

    print(
        "=== VERIFICAÇÃO FINAL ==="
    )

    if conhecimento_final == esperado:
        print(
            "PASSOU: a experiência duplicada "
            "não foi armazenada novamente."
        )
    else:
        print(
            "FALHOU: o conhecimento final "
            "possui divergência."
        )

    print()

    print(
        "=== ESTADO FINAL ==="
    )

    print(
        f"Conceitos: "
        f"{len(conceitos_finais)}"
    )

    print(
        f"Relações: "
        f"{len(relacoes_finais)}"
    )

    print(
        f"Blocos: "
        f"{len(blocos_finais)}"
    )

    print(
        f"Triplas: "
        f"{len(conhecimento_final)}"
    )

    print(
        f"Tamanho: "
        f"{ARQUIVO.stat().st_size} bytes"
    )


if __name__ == "__main__":
    main()
