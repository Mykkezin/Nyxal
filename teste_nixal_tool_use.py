"""Testes de integração e segurança das ferramentas operacionais."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import nixal_capacidades
import nixal_tool_use
from nixal_capacidades import GerenciadorCapacidades
from nixal_tool_use import NotasLembretesNixOS, registrar_capacidades_operacionais


FERRAMENTAS_PRIVADAS = {
    "buscar_arquivos",
    "ler_arquivo_usuario",
    "consultar_emails_google",
    "ler_email_google",
    "consultar_agenda_google",
    "consultar_home_assistant",
    "listar_notas_lembretes",
}
FERRAMENTAS_MUTAVEIS = {"salvar_nota", "criar_lembrete", "abrir_aplicativo"}


class TesteRegistroFerramentasOperacionais(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="nyxal-tools-test-")
        self.addCleanup(self.temp.cleanup)
        self.arquivo_catalogo = Path(self.temp.name) / "capacidades.json"
        self.patch_catalogo = patch.object(
            nixal_capacidades, "ARQUIVO_CAPACIDADES", self.arquivo_catalogo
        )
        self.patch_catalogo.start()
        self.addCleanup(self.patch_catalogo.stop)
        self.capacidades = GerenciadorCapacidades()
        self.store = NotasLembretesNixOS(Path(self.temp.name) / "notas.json")

    def nomes(self) -> set[str]:
        return set(self.capacidades.capacidades)

    def test_padrao_registra_apenas_ferramentas_operacionais_de_baixo_impacto(self):
        registrar_capacidades_operacionais(self.capacidades, store=self.store)
        nomes = self.nomes()
        self.assertTrue({"pesquisar_web", "consultar_metar_taf", "executar_diagnostico"} <= nomes)
        self.assertTrue(FERRAMENTAS_PRIVADAS.isdisjoint(nomes))
        self.assertTrue(FERRAMENTAS_MUTAVEIS.isdisjoint(nomes))

    def test_dados_privados_exigem_opt_in_explicito_e_nao_habilitam_acoes_mutaveis(self):
        registrar_capacidades_operacionais(
            self.capacidades,
            incluir_dados_privados=True,
            store=self.store,
        )
        nomes = self.nomes()
        self.assertTrue(FERRAMENTAS_PRIVADAS <= nomes)
        self.assertTrue(FERRAMENTAS_MUTAVEIS.isdisjoint(nomes))

    def test_registro_repetido_e_idempotente(self):
        registrar_capacidades_operacionais(self.capacidades, store=self.store)
        antes = self.nomes()
        registrar_capacidades_operacionais(self.capacidades, store=self.store)
        self.assertEqual(self.nomes(), antes)

    def test_acoes_mutaveis_falham_fechadas_sem_registro_parcial(self):
        antes = self.nomes()
        with self.assertRaisesRegex(RuntimeError, "não aplica autorização por ferramenta"):
            registrar_capacidades_operacionais(
                self.capacidades,
                incluir_acoes=True,
                store=self.store,
            )
        self.assertEqual(self.nomes(), antes)
        self.assertTrue(FERRAMENTAS_MUTAVEIS.isdisjoint(self.nomes()))

    def test_flags_precisam_ser_booleanas(self):
        with self.assertRaises(TypeError):
            registrar_capacidades_operacionais(self.capacidades, incluir_dados_privados="true")
        with self.assertRaises(TypeError):
            registrar_capacidades_operacionais(self.capacidades, incluir_acoes=1)

    def test_entradas_invalidas_nao_disparam_rede_ou_shell(self):
        busca = nixal_tool_use.pesquisar_web(" ")
        metar = nixal_tool_use.consultar_metar_taf("SB")
        self.assertEqual(busca["estado"], "consulta_invalida")
        self.assertEqual(metar["estado"], "icao_invalido")
        with patch.object(nixal_tool_use.subprocess, "run") as executar:
            resultado = nixal_tool_use.executar_diagnostico("shell livre")
        self.assertEqual(resultado["estado"], "diagnostico_nao_permitido")
        executar.assert_not_called()


class TesteIntegracaoAgenteQwen(unittest.TestCase):
    def _agente(self, privado: bool):
        from nixal_agente_qwen import AgenteNixalQwen

        with tempfile.TemporaryDirectory(prefix="nyxal-agent-tool-test-") as temp:
            with patch.object(
                nixal_capacidades,
                "ARQUIVO_CAPACIDADES",
                Path(temp) / "capacidades.json",
            ):
                valor = "1" if privado else ""
                with patch.dict(os.environ, {"NYXAL_ENABLE_PRIVATE_READ_TOOLS": valor}):
                    agente = AgenteNixalQwen()
                    return set(agente.capacidades.capacidades)

    def test_agente_registra_ferramentas_basicas_por_padrao(self):
        nomes = self._agente(privado=False)
        self.assertTrue({"pesquisar_web", "consultar_metar_taf", "executar_diagnostico"} <= nomes)
        self.assertTrue(FERRAMENTAS_PRIVADAS.isdisjoint(nomes))
        self.assertTrue(FERRAMENTAS_MUTAVEIS.isdisjoint(nomes))

    def test_agente_so_registra_ferramentas_de_dados_privados_com_opt_in(self):
        nomes = self._agente(privado=True)
        self.assertTrue(FERRAMENTAS_PRIVADAS <= nomes)
        self.assertTrue(FERRAMENTAS_MUTAVEIS.isdisjoint(nomes))


if __name__ == "__main__":
    unittest.main(verbosity=2)
