import json
import re

import gerenciador_cristal

from gerenciador_cristal import (
    CONCEITOS_BASE,
    RELACOES_BASE,
    abrir_ou_criar_cristal,
    ler_arquivo,
    registrar_experiencia,
)


def caminho_do_cristal():
    """Caminho canônico consultado no momento do uso.

    Importar o Path por valor deixaria este módulo apontando para uma
    cópia antiga sempre que o gerenciador resolver outro destino.
    """

    return gerenciador_cristal.ARQUIVO


# ============================================================
# MICROETAPA 42.1
# EXPERIÊNCIA -> QWEN -> NORMALIZAÇÃO -> VERIFICAÇÃO -> CRISTAL
#
# O Qwen pode retornar variações linguísticas naturais.
#
# Exemplos:
#
# "uma observação"
# "uma hipótese"
# "pode gerar"
#
# O normalizador transforma isso em uma forma canônica.
#
# IMPORTANTE:
#
# A normalização NÃO cria conhecimento.
# Ela somente coloca uma expressão reconhecida
# no formato do vocabulário estrutural.
# ============================================================


MODELO = "qwen2:7b"


# ============================================================
# VOCABULÁRIOS PERMITIDOS
# ============================================================

CONCEITOS_PERMITIDOS = set(
    CONCEITOS_BASE
)

RELACOES_PERMITIDAS = set(
    RELACOES_BASE
)


# ============================================================
# EXPERIÊNCIAS DE TESTE
# ============================================================

EXPERIENCIAS_TESTE = [
    "Uma observação pode gerar uma hipótese.",
    "Um experimento pode testar uma hipótese.",
    "Uma hipótese pode gerar uma previsão.",
    "Uma observação pode gerar uma hipótese.",
]


# ============================================================
# PROMPT
# ============================================================

def criar_prompt(texto):
    conceitos = ", ".join(
        CONCEITOS_BASE
    )

    relacoes = ", ".join(
        RELACOES_BASE
    )

    return f"""
Você é um interpretador estrutural.

Sua única tarefa é transformar a frase fornecida em
uma única relação no formato JSON.

Formato:

{{
  "sujeito": "...",
  "relacao": "...",
  "objeto": "..."
}}

REGRAS:

1. Responda somente com JSON válido.
2. Não escreva explicações.
3. Use somente conceitos presentes na lista permitida.
4. Use somente relações presentes na lista permitida.
5. Não invente conceitos.
6. Não invente relações.
7. Para conceitos, não use artigos como "um", "uma", "o", "a".
8. Para relações, use exatamente a grafia da lista permitida.
9. Relações usam underscore, por exemplo: "pode_gerar".
10. Preserve o sentido principal da frase.

CONCEITOS PERMITIDOS:

{conceitos}

RELAÇÕES PERMITIDAS:

{relacoes}

FRASE:

{texto}
""".strip()


# ============================================================
# QWEN
# ============================================================

def interpretar(texto):
    # Dependência opcional: o import pesável acontece só quando o modelo
    # é de fato chamado, nunca ao carregar o módulo.
    import ollama

    resposta = ollama.chat(
        model=MODELO,
        format="json",
        messages=[
            {
                "role": "system",
                "content": (
                    "Você transforma linguagem natural "
                    "em uma relação estrutural JSON. "
                    "Nunca invente conceitos ou relações."
                ),
            },
            {
                "role": "user",
                "content": criar_prompt(texto),
            },
        ],
    )

    conteudo = (
        resposta["message"]["content"]
        .strip()
    )

    try:
        candidato = json.loads(
            conteudo
        )
    except json.JSONDecodeError as erro:
        raise ValueError(
            "Qwen retornou JSON inválido.\n"
            f"Resposta recebida: {conteudo}"
        ) from erro

    return candidato


# ============================================================
# NORMALIZAR CONCEITO
#
# Remove artigos no início.
#
# Exemplos:
#
# "uma observação" -> "observação"
# "um experimento" -> "experimento"
# "a hipótese"     -> "hipótese"
# ============================================================

def normalizar_conceito(valor):
    if not isinstance(valor, str):
        return valor

    valor = valor.strip()

    valor = re.sub(
        r"^(um|uma|o|a|os|as)\s+",
        "",
        valor,
        flags=re.IGNORECASE,
    )

    return valor.strip()


# ============================================================
# NORMALIZAR RELAÇÃO
#
# "pode gerar" -> "pode_gerar"
#
# Não aceitamos automaticamente qualquer relação nova.
# Depois da normalização, o verificador ainda precisa
# encontrar a relação dentro de RELACOES_PERMITIDAS.
# ============================================================

def normalizar_relacao(valor):
    if not isinstance(valor, str):
        return valor

    valor = valor.strip()

    valor = re.sub(
        r"\s+",
        "_",
        valor,
    )

    return valor


# ============================================================
# NORMALIZAR CANDIDATO
# ============================================================

def normalizar_candidato(candidato):
    if not isinstance(
        candidato,
        dict,
    ):
        return candidato

    normalizado = dict(
        candidato
    )

    if "sujeito" in normalizado:
        normalizado["sujeito"] = (
            normalizar_conceito(
                normalizado["sujeito"]
            )
        )

    if "relacao" in normalizado:
        normalizado["relacao"] = (
            normalizar_relacao(
                normalizado["relacao"]
            )
        )

    if "objeto" in normalizado:
        normalizado["objeto"] = (
            normalizar_conceito(
                normalizado["objeto"]
            )
        )

    return normalizado


# ============================================================
# VALIDAÇÃO ESTRUTURAL
# ============================================================

def validar_candidato(candidato):
    if not isinstance(
        candidato,
        dict,
    ):
        return (
            False,
            "O candidato não é um objeto JSON.",
        )

    chaves_esperadas = {
        "sujeito",
        "relacao",
        "objeto",
    }

    chaves_recebidas = set(
        candidato.keys()
    )

    if chaves_recebidas != chaves_esperadas:
        return (
            False,
            "As chaves do JSON estão incorretas.",
        )

    sujeito = candidato["sujeito"]
    relacao = candidato["relacao"]
    objeto = candidato["objeto"]

    if not isinstance(
        sujeito,
        str,
    ):
        return (
            False,
            "O sujeito não é texto.",
        )

    if not isinstance(
        relacao,
        str,
    ):
        return (
            False,
            "A relação não é texto.",
        )

    if not isinstance(
        objeto,
        str,
    ):
        return (
            False,
            "O objeto não é texto.",
        )

    if sujeito not in CONCEITOS_PERMITIDOS:
        return (
            False,
            f"Sujeito não permitido: {sujeito}",
        )

    if objeto not in CONCEITOS_PERMITIDOS:
        return (
            False,
            f"Objeto não permitido: {objeto}",
        )

    if relacao not in RELACOES_PERMITIDAS:
        return (
            False,
            f"Relação não permitida: {relacao}",
        )

    return (
        True,
        "Candidato estrutural válido.",
    )


# ============================================================
# CANDIDATO -> TRIPLA
# ============================================================

def candidato_para_tripla(candidato):
    return (
        candidato["sujeito"],
        candidato["relacao"],
        candidato["objeto"],
    )


# ============================================================
# PRINCIPAL
# ============================================================

def main():
    print(
        "=== MICROETAPA 42.1 ==="
    )

    print(
        "QWEN -> NORMALIZAÇÃO -> VERIFICAÇÃO -> CRISTAL"
    )

    print()

    # --------------------------------------------------------
    # ABERTURA NÃO DESTRUTIVA
    #
    # O cristal nunca é apagado aqui. Se já existe, o conteúdo anterior
    # é preservado e esta execução apenas acrescenta.
    # --------------------------------------------------------

    (
        conceitos,
        relacoes,
        blocos,
    ) = abrir_ou_criar_cristal()

    arquivo = caminho_do_cristal()

    print(
        "=== CRISTAL INICIAL ==="
    )

    print(
        f"Arquivo: {arquivo}"
    )

    print(
        f"Conceitos: {len(conceitos)}"
    )

    print(
        f"Relações: {len(relacoes)}"
    )

    print(
        f"Blocos: {len(blocos)}"
    )

    print()

    # --------------------------------------------------------
    # PROCESSAR EXPERIÊNCIAS
    # --------------------------------------------------------

    for numero, texto in enumerate(
        EXPERIENCIAS_TESTE,
        start=1,
    ):
        print(
            f"=== EXPERIÊNCIA {numero} ==="
        )

        print(
            f"Texto: {texto}"
        )

        tamanho_antes = (
            arquivo.stat().st_size
        )

        # ----------------------------------------------------
        # QWEN
        # ----------------------------------------------------

        try:
            candidato_bruto = interpretar(
                texto
            )

        except Exception as erro:
            print(
                "QWEN: FALHOU"
            )

            print(
                f"Erro: {erro}"
            )

            print()

            continue

        print(
            "=== CANDIDATO BRUTO ==="
        )

        print(
            json.dumps(
                candidato_bruto,
                ensure_ascii=False,
                indent=2,
            )
        )

        print()

        # ----------------------------------------------------
        # NORMALIZAÇÃO
        # ----------------------------------------------------

        candidato = (
            normalizar_candidato(
                candidato_bruto
            )
        )

        print(
            "=== CANDIDATO NORMALIZADO ==="
        )

        print(
            json.dumps(
                candidato,
                ensure_ascii=False,
                indent=2,
            )
        )

        print()

        # ----------------------------------------------------
        # VERIFICADOR
        # ----------------------------------------------------

        valido, motivo = (
            validar_candidato(
                candidato
            )
        )

        print(
            "=== VERIFICADOR ==="
        )

        if valido:
            print(
                f"PASSOU: {motivo}"
            )
        else:
            print(
                f"FALHOU: {motivo}"
            )

        if not valido:
            print()
            continue

        # ----------------------------------------------------
        # CONVERTER
        # ----------------------------------------------------

        sujeito, relacao, objeto = (
            candidato_para_tripla(
                candidato
            )
        )

        # ----------------------------------------------------
        # CRISTAL
        # ----------------------------------------------------

        try:
            resultado = (
                registrar_experiencia(
                    sujeito,
                    relacao,
                    objeto,
                )
            )

        except Exception as erro:
            print(
                "CRISTAL: FALHOU"
            )

            print(
                f"Erro: {erro}"
            )

            print()

            continue

        tamanho_depois = (
            arquivo.stat().st_size
        )

        crescimento_observado = (
            tamanho_depois
            - tamanho_antes
        )

        print(
            "=== CRISTAL ==="
        )

        print(
            f"Classificação: "
            f"{resultado['classificacao']}"
        )

        print(
            f"Crescimento relatado: "
            f"{resultado['crescimento']} bytes"
        )

        print(
            f"Crescimento observado: "
            f"{crescimento_observado} bytes"
        )

        print(
            f"Conhecimento armazenado: "
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
    # ESTADO FINAL
    # --------------------------------------------------------

    (
        conceitos_finais,
        relacoes_finais,
        blocos_finais,
    ) = ler_arquivo()

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
        f"Tamanho: "
        f"{arquivo.stat().st_size} bytes"
    )


if __name__ == "__main__":
    main()
