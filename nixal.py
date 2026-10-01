import json
import os
import signal
import time
from datetime import datetime


# ============================================================
# MICROETAPA 51
# PRESENÇA DA NIXAL
#
# Objetivo:
#
# 1. manter a Nixal ativa como processo contínuo
# 2. manter um estado interno simples
# 3. executar ciclos próprios
# 4. registrar heartbeat
#
# Nesta etapa:
#
# - NÃO controla hardware
# - NÃO controla RGB
# - NÃO acessa câmera
# - NÃO acessa microfone
# - NÃO altera o cristal V1
# - NÃO altera o pipeline existente
#
# É a primeira camada de presença contínua.
# ============================================================


NOME = "Nixal"

VERSAO = "0.1"

INTERVALO_CICLO = 2.0

ARQUIVO_ESTADO = (
    "estado_nixal.json"
)


# ============================================================
# CONTROLE DE EXECUÇÃO
# ============================================================

EXECUTANDO = True


def encerrar_sinal(
    sinal,
    frame,
):
    global EXECUTANDO

    print()
    print(
        f"[{NOME}] "
        "sinal de encerramento recebido."
    )

    EXECUTANDO = False


signal.signal(
    signal.SIGINT,
    encerrar_sinal,
)

signal.signal(
    signal.SIGTERM,
    encerrar_sinal,
)


# ============================================================
# TEMPO
# ============================================================

def agora_iso():
    return datetime.now().astimezone().isoformat()


# ============================================================
# ESTADO
# ============================================================

def criar_estado_inicial():
    agora = agora_iso()

    return {
        "identidade": {
            "nome": NOME,
            "versao": VERSAO,
        },

        "presenca": {
            "ativa": True,
            "iniciada_em": agora,
            "ultimo_ciclo": agora,
            "ciclos": 0,
        },

        "estado": {
            "modo": "presenca",
            "status": "ativa",
        },
    }


def salvar_estado(estado):

    temporario = (
        ARQUIVO_ESTADO
        + ".tmp"
    )

    with open(
        temporario,
        "w",
        encoding="utf-8",
    ) as arquivo:

        json.dump(
            estado,
            arquivo,
            ensure_ascii=False,
            indent=2,
        )

    os.replace(
        temporario,
        ARQUIVO_ESTADO,
    )


def carregar_estado():

    if not os.path.exists(
        ARQUIVO_ESTADO
    ):
        return (
            criar_estado_inicial()
        )

    try:

        with open(
            ARQUIVO_ESTADO,
            "r",
            encoding="utf-8",
        ) as arquivo:

            estado = json.load(
                arquivo
            )

        if not isinstance(
            estado,
            dict,
        ):
            return (
                criar_estado_inicial()
            )

        return estado

    except (
        OSError,
        json.JSONDecodeError,
    ):

        return (
            criar_estado_inicial()
        )


# ============================================================
# CICLO
# ============================================================

def executar_ciclo(
    estado,
):

    momento = agora_iso()

    estado[
        "presenca"
    ][
        "ultimo_ciclo"
    ] = momento

    estado[
        "presenca"
    ][
        "ciclos"
    ] += 1

    estado[
        "estado"
    ][
        "modo"
    ] = "presenca"

    estado[
        "estado"
    ][
        "status"
    ] = "ativa"

    salvar_estado(
        estado
    )

    ciclo = estado[
        "presenca"
    ][
        "ciclos"
    ]

    print(
        f"[{NOME}] "
        f"ativa | "
        f"ciclo {ciclo} | "
        f"{momento}"
    )


# ============================================================
# ENCERRAMENTO
# ============================================================

def finalizar(
    estado,
):

    estado[
        "presenca"
    ][
        "ativa"
    ] = False

    estado[
        "estado"
    ][
        "status"
    ] = "encerrada"

    estado[
        "estado"
    ][
        "modo"
    ] = "encerramento"

    estado[
        "presenca"
    ][
        "ultimo_ciclo"
    ] = agora_iso()

    salvar_estado(
        estado
    )

    print(
        f"[{NOME}] "
        "presença encerrada."
    )


# ============================================================
# PRINCIPAL
# ============================================================

def main():

    estado = carregar_estado()

    estado[
        "identidade"
    ][
        "nome"
    ] = NOME

    estado[
        "identidade"
    ][
        "versao"
    ] = VERSAO

    estado[
        "presenca"
    ][
        "ativa"
    ] = True

    estado[
        "presenca"
    ][
        "iniciada_em"
    ] = agora_iso()

    estado[
        "estado"
    ][
        "modo"
    ] = "presenca"

    estado[
        "estado"
    ][
        "status"
    ] = "ativa"

    salvar_estado(
        estado
    )

    print()
    print(
        "=============================================="
    )
    print(
        "NIXAL"
    )
    print(
        "MICROETAPA 51 — PRESENÇA"
    )
    print(
        "=============================================="
    )
    print()

    print(
        f"Nome: {NOME}"
    )

    print(
        f"Versão: {VERSAO}"
    )

    print(
        "Estado: ATIVA"
    )

    print(
        f"Ciclo: a cada {INTERVALO_CICLO:.1f}s"
    )

    print()

    print(
        "Nixal está ativa como processo."
    )

    print(
        "Pressione CTRL+C para encerrar."
    )

    print()

    try:

        while EXECUTANDO:

            executar_ciclo(
                estado
            )

            time.sleep(
                INTERVALO_CICLO
            )

    finally:

        finalizar(
            estado
        )


if __name__ == "__main__":
    main()
