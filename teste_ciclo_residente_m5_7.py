#!/usr/bin/env python3
"""
NYXOS — TESTE M5.7
Ciclo operacional residente.
"""

from __future__ import annotations

import ast
from pathlib import Path

from nixal_ciclo_residente import CicloResidenteNixOS


BASE_DIR = Path(__file__).resolve().parent
MODULO = BASE_DIR / "nixal_ciclo_residente.py"
LAUNCHER = BASE_DIR / "executar_nyxos_residente.py"
RUNTIME = BASE_DIR / "nixal_runtime.py"

TESTES = 0
FALHAS = 0


def verificar(condicao: bool, mensagem: str) -> None:
    global TESTES, FALHAS
    TESTES += 1
    print(f"[{'PASS' if condicao else 'FAIL'}] {TESTES}. {mensagem}")
    if not condicao:
        FALHAS += 1


class RuntimeFalso:
    def __init__(self) -> None:
        self.quantidade = 0
        self.owner = None

    def executar_ciclo(self) -> dict:
        self.quantidade += 1
        resultado = {
            "sucesso": True,
            "estado": "ciclo_concluido",
            "ciclo_id": f"falso-{self.quantidade}",
        }

        if self.quantidade == 1 and self.owner is not None:
            self.owner.parar()

        return resultado


class PersistenciaFalsa:
    def __init__(self) -> None:
        self.registros = []

    def registrar(self, *, ciclo=None, estado=None, **_kwargs):
        self.registros.append(
            {
                "ciclo": ciclo.get("ciclo_id") if isinstance(ciclo, dict) else None,
                "estado": estado,
            }
        )
        return {"sucesso": True}


class RuntimeComErro:
    def executar_ciclo(self) -> dict:
        return {
            "sucesso": False,
            "estado": "erro",
            "motivo": "falha-controlada",
        }


def main() -> None:
    verificar(MODULO.exists(), "módulo do ciclo residente existe")
    verificar(LAUNCHER.exists(), "launcher explícito existe")
    verificar(RUNTIME.exists(), "Runtime existe")

    texto_modulo = MODULO.read_text(encoding="utf-8")
    texto_launcher = LAUNCHER.read_text(encoding="utf-8")

    try:
        ast.parse(texto_modulo)
        verificar(True, "nixal_ciclo_residente.py possui sintaxe válida")
    except SyntaxError as erro:
        verificar(False, f"nixal_ciclo_residente.py possui sintaxe válida: {erro}")

    verificar(
        "NyxalRuntime" in texto_launcher
        and "CicloResidenteNixOS" in texto_launcher,
        "launcher conecta o Runtime ao ciclo residente",
    )

    verificar(
        "SolicitacaoEvolucaoNixal" in texto_launcher
        and "solicitacao_evolucao=solicitacao_evolucao" in texto_launcher,
        "launcher injeta a solicitação formal no Runtime antes da AE2",
    )

    verificar(
        'auto_evolution_habilitada": False' in texto_modulo,
        "ciclo residente declara auto-evolution desabilitada",
    )

    verificar(
        all(
            proibido not in texto_modulo
            for proibido in (
                "subprocess.",
                "os.system(",
                "Popen(",
                "git ",
            )
        ),
        "ciclo residente não executa comandos externos",
    )

    runtime = RuntimeFalso()
    persistencia = PersistenciaFalsa()
    residente = CicloResidenteNixOS(
        runtime,
        persistencia,
        intervalo_segundos=0,
    )
    runtime.owner = residente

    resultados = residente.executar(max_ciclos=10)

    verificar(
        len(resultados) == 1
        and residente.contexto().get("estado_residente") == "interrompido",
        "interrupção explícita encerra a residência",
    )

    verificar(
        residente.contexto().get("ciclos_executados") == 1,
        "ciclo interrompido preserva contagem total correta",
    )

    runtime2 = RuntimeFalso()
    persistencia2 = PersistenciaFalsa()
    residente2 = CicloResidenteNixOS(
        runtime2,
        persistencia2,
        intervalo_segundos=0,
    )
    runtime2.owner = residente2
    resultados2 = residente2.executar(max_ciclos=2)

    verificar(
        len(resultados2) == 1,
        "residência respeita a interrupção durante a sessão",
    )

    runtime3 = RuntimeFalso()
    persistencia3 = PersistenciaFalsa()
    residente3 = CicloResidenteNixOS(
        runtime3,
        persistencia3,
        intervalo_segundos=0,
    )
    runtime3.owner = None
    resultados3 = residente3.executar(max_ciclos=2)

    verificar(
        len(resultados3) == 2
        and residente3.contexto().get("estado_residente") == "concluido",
        "residência limitada conclui o número solicitado de ciclos",
    )

    resultados4 = residente3.executar(max_ciclos=1)
    verificar(
        len(resultados4) == 1
        and residente3.contexto().get("ciclos_executados") == 3,
        "nova sessão residente é possível sem resetar contagem total",
    )

    residente_erro = CicloResidenteNixOS(
        RuntimeComErro(),
        PersistenciaFalsa(),
        intervalo_segundos=0,
        parar_em_erro=True,
    )
    resultados_erro = residente_erro.executar(max_ciclos=5)

    verificar(
        len(resultados_erro) == 1
        and residente_erro.contexto().get("estado_residente") == "erro",
        "falha do Runtime encerra a residência segundo a política",
    )

    verificar(
        all(
            registro.get("estado")
            for registro in persistencia.registros
        ),
        "persistência recebe estados da residência",
    )

    runtime_ae5 = RuntimeFalso()
    persistencia_ae5 = PersistenciaFalsa()

    class EvolucaoFalsa:
        habilitada = True
        FONTE = "ae4_falsa"

        def processar_ciclo(self, ciclo: dict) -> dict:
            return {
                "sucesso": True,
                "estado": "ae4_ciclo_observado",
                "ciclo_id": ciclo["ciclo_id"],
                "ae1": {"valor": {
                    "oportunidade_id": "op-falsa",
                    "limitacao": "limitação de teste",
                    "hipotese": "hipótese de teste",
                }},
            }

    class DescobertaFalsa:
        habilitada = True
        FONTE = "ae5_falsa"

        def __init__(self):
            self.argumento = None

        def processar(self, resultado: dict) -> dict:
            self.argumento = resultado
            return {
                "sucesso": True,
                "estado": "sinal_em_observacao",
                "autorizacao_explicita": False,
                "integracao_executada": False,
                "stable_modificada": False,
                "arquitetura_modificada": False,
                "conhecimento_permanente": False,
            }

    ae4_falsa = EvolucaoFalsa()
    ae5_falsa = DescobertaFalsa()
    residente_ae5 = CicloResidenteNixOS(
        runtime_ae5,
        persistencia_ae5,
        ciclo_evolucao_ae4=ae4_falsa,
        descoberta_continua_ae5=ae5_falsa,
        intervalo_segundos=0,
    )
    resultados_ae5 = residente_ae5.executar(max_ciclos=1)

    verificar(
        len(resultados_ae5) == 1
        and ae5_falsa.argumento.get("estado") == "ae4_ciclo_observado",
        "AE5 recebe o resultado produzido pela AE4 no ciclo residente",
    )
    verificar(
        resultados_ae5[0].get("auto_descoberta_ae5", {}).get("sucesso") is True,
        "resultado AE5 é exposto no resultado do ciclo",
    )

    print()
    print("=" * 64)
    print("TESTE — CICLO OPERACIONAL RESIDENTE NYXOS M5.7")
    print("=" * 64)
    print(f"TESTES EXECUTADOS: {TESTES}")
    print(f"FALHAS: {FALHAS}")
    print(f"PASSOU: {FALHAS == 0}")
    print("=" * 64)

    if FALHAS:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
