#!/usr/bin/env python3
"""Regressões do autoreparo limitado e sua integração com o residente."""
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from nixal_autoreparo_residente import AutoreparoResidenteNixOS
from nixal_ciclo_residente import CicloResidenteNixOS


class RelogioFalso:
    def __init__(self) -> None:
        self.agora = 1000.0

    def __call__(self) -> float:
        return self.agora

    def avancar(self, segundos: float) -> None:
        self.agora += segundos


class SistemaFalso:
    def __init__(self, *, grafico_ativo: bool = False, interface_ativa: bool = False) -> None:
        self.grafico_ativo = grafico_ativo
        self.interface_ativa = interface_ativa
        self.reinicios: list[list[str]] = []

    def __call__(self, argumentos, **_kwargs):
        if argumentos[:3] == ["systemctl", "--user", "is-active"]:
            unidade = argumentos[-1]
            ativo = (
                self.grafico_ativo
                if unidade == "graphical-session.target"
                else self.interface_ativa
                if unidade == "nyxos-interface.service"
                else False
            )
            return subprocess.CompletedProcess(argumentos, 0 if ativo else 3)
        if argumentos[:3] == ["systemctl", "--user", "restart"]:
            self.reinicios.append(list(argumentos))
            return subprocess.CompletedProcess(argumentos, 0)
        return subprocess.CompletedProcess(argumentos, 1)


class RuntimeFalso:
    def __init__(self) -> None:
        self.residente = None

    def executar_ciclo(self):
        if self.residente is not None:
            self.residente.parar()
        return {"sucesso": True, "estado": "ciclo_teste"}


class AutoreparoResidenteTests(unittest.TestCase):
    def test_api_so_reinicia_apos_tres_falhas_consecutivas(self):
        with tempfile.TemporaryDirectory() as diretorio:
            sistema = SistemaFalso(grafico_ativo=False)
            reparo = AutoreparoResidenteNixOS(
                health_checker=lambda: False,
                command_runner=sistema,
                clock=RelogioFalso(),
                arquivo_auditoria=Path(diretorio) / "autoreparo.jsonl",
            )

            primeiro = reparo.verificar_e_reparar()
            segundo = reparo.verificar_e_reparar()
            terceiro = reparo.verificar_e_reparar()

            self.assertEqual(primeiro["api"]["reparo"]["estado"], "confirmando_falha")
            self.assertEqual(segundo["api"]["reparo"]["estado"], "confirmando_falha")
            self.assertEqual(terceiro["api"]["reparo"]["estado"], "reinicio_solicitado")
            self.assertEqual(
                sistema.reinicios,
                [["systemctl", "--user", "restart", "nyxal-api.service"]],
            )

    def test_sucesso_reinicia_a_contagem_de_falhas(self):
        with tempfile.TemporaryDirectory() as diretorio:
            sistema = SistemaFalso()
            respostas = iter([False, False, True, False, False])
            reparo = AutoreparoResidenteNixOS(
                health_checker=lambda: next(respostas),
                command_runner=sistema,
                clock=RelogioFalso(),
                arquivo_auditoria=Path(diretorio) / "autoreparo.jsonl",
            )

            resultados = [reparo.verificar_e_reparar() for _ in range(5)]
            self.assertEqual(resultados[2]["api"]["estado"], "saudavel")
            self.assertEqual(resultados[4]["api"]["reparo"]["estado"], "confirmando_falha")
            self.assertEqual(sistema.reinicios, [])

    def test_circuito_abre_apos_limite_de_tres_reinicios_na_janela(self):
        with tempfile.TemporaryDirectory() as diretorio:
            relogio = RelogioFalso()
            sistema = SistemaFalso()
            reparo = AutoreparoResidenteNixOS(
                health_checker=lambda: False,
                command_runner=sistema,
                clock=relogio,
                arquivo_auditoria=Path(diretorio) / "autoreparo.jsonl",
            )

            for _ in range(3):
                resultado = reparo.verificar_e_reparar()
            self.assertEqual(resultado["api"]["reparo"]["estado"], "reinicio_solicitado")

            for _ in range(3):
                relogio.avancar(AutoreparoResidenteNixOS.COOLDOWN_REINICIO_SEGUNDOS)
                resultado = reparo.verificar_e_reparar()
            self.assertEqual(len(sistema.reinicios), 3)
            self.assertEqual(
                resultado["api"]["reparo"]["estado"],
                "circuito_aberto_limite_reinicios",
            )
            arquivo = Path(diretorio) / "autoreparo.jsonl"
            linhas_antes = arquivo.read_text(encoding="utf-8").splitlines()
            repetida = reparo.verificar_e_reparar()
            linhas_depois = arquivo.read_text(encoding="utf-8").splitlines()
            self.assertEqual(
                repetida["api"]["reparo"]["estado"],
                "circuito_aberto_limite_reinicios",
            )
            self.assertEqual(linhas_depois, linhas_antes)

    def test_nao_reinicia_interface_sem_sessao_grafica(self):
        with tempfile.TemporaryDirectory() as diretorio:
            sistema = SistemaFalso(grafico_ativo=False)
            reparo = AutoreparoResidenteNixOS(
                health_checker=lambda: True,
                command_runner=sistema,
                clock=RelogioFalso(),
                arquivo_auditoria=Path(diretorio) / "autoreparo.jsonl",
            )
            resultado = reparo.verificar_e_reparar()
            self.assertEqual(resultado["interface"]["estado"], "aguardando_sessao_grafica")
            self.assertEqual(sistema.reinicios, [])

    def test_reinicia_interface_apenas_se_sessao_grafica_esta_ativa(self):
        with tempfile.TemporaryDirectory() as diretorio:
            sistema = SistemaFalso(grafico_ativo=True, interface_ativa=False)
            reparo = AutoreparoResidenteNixOS(
                health_checker=lambda: True,
                command_runner=sistema,
                clock=RelogioFalso(),
                arquivo_auditoria=Path(diretorio) / "autoreparo.jsonl",
            )
            for _ in range(3):
                resultado = reparo.verificar_e_reparar()
            self.assertEqual(resultado["interface"]["reparo"]["estado"], "reinicio_solicitado")
            self.assertEqual(
                sistema.reinicios,
                [["systemctl", "--user", "restart", "nyxos-interface.service"]],
            )

    def test_auditoria_nao_grava_detalhes_de_segredos(self):
        with tempfile.TemporaryDirectory() as diretorio:
            caminho = Path(diretorio) / "autoreparo.jsonl"
            sistema = SistemaFalso()
            reparo = AutoreparoResidenteNixOS(
                health_checker=lambda: False,
                command_runner=sistema,
                clock=RelogioFalso(),
                arquivo_auditoria=caminho,
            )
            for _ in range(3):
                reparo.verificar_e_reparar()
            texto = caminho.read_text(encoding="utf-8")
            self.assertIn("reinicio_solicitado", texto)
            self.assertNotIn("Bearer", texto)
            self.assertNotIn("token", texto.lower())

    def test_ciclo_residente_publica_resultado_do_autoreparo(self):
        class AutoreparoFalso:
            def __init__(self):
                self.chamadas = 0

            def verificar_e_reparar(self):
                self.chamadas += 1
                return {
                    "sucesso": True,
                    "estado": "saudavel",
                    "origem": "autoreparo_teste",
                    "autorizacao_explicita": False,
                }

        runtime = RuntimeFalso()
        autoreparo = AutoreparoFalso()
        residente = CicloResidenteNixOS(
            runtime,
            autoreparo_residente=autoreparo,
            intervalo_segundos=0,
        )
        runtime.residente = residente

        resultados = residente.executar(max_ciclos=1)
        self.assertEqual(autoreparo.chamadas, 1)
        self.assertEqual(
            resultados[0]["autoreparo_residente"]["estado"],
            "saudavel",
        )
        self.assertTrue(residente.contexto()["autoreparo_residente_habilitado"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
