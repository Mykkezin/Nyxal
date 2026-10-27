"""Testes de integração e segurança das ferramentas operacionais."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import nixal_capacidades
import nixal_tool_use
from nixal_capacidades import GerenciadorCapacidades, ResultadoCapacidade
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
        self.arquivo_log = Path(self.temp.name) / "auditoria.json"
        self.patch_log = patch.object(nixal_capacidades, "ARQUIVO_LOG", self.arquivo_log)
        self.patch_log.start()
        self.addCleanup(self.patch_log.stop)
        self.patch_env = patch.dict(os.environ, {
            "NYXAL_ENABLE_PRIVATE_READ_TOOLS": "",
            "NYXAL_ENABLE_MUTABLE_TOOLS": "",
        })
        self.patch_env.start()
        self.addCleanup(self.patch_env.stop)
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

    def test_catalogo_corrompido_nao_e_sobrescrito(self):
        with tempfile.TemporaryDirectory(prefix="nyxal-corrupt-catalog-") as tmp:
            arquivo = Path(tmp) / "capacidades.json"
            original = "{catalogo inválido"
            arquivo.write_text(original, encoding="utf-8")
            with patch.object(nixal_capacidades, "ARQUIVO_CAPACIDADES", arquivo):
                manager = GerenciadorCapacidades()
            self.assertTrue(manager.capacidades)
            self.assertEqual(arquivo.read_text(encoding="utf-8"), original)

    def test_log_corrompido_nao_e_sobrescrito_apos_execucao(self):
        with tempfile.TemporaryDirectory(prefix="nyxal-corrupt-audit-") as tmp:
            arquivo = Path(tmp) / "auditoria.json"
            original = "{auditoria inválida"
            arquivo.write_text(original, encoding="utf-8")
            catalogo = Path(tmp) / "capacidades.json"
            with patch.object(nixal_capacidades, "ARQUIVO_LOG", arquivo):
                with patch.object(nixal_capacidades, "ARQUIVO_CAPACIDADES", catalogo):
                    manager = GerenciadorCapacidades()
                    resultado = manager.executar("obter_hora")
            self.assertTrue(resultado.sucesso)
            self.assertEqual(arquivo.read_text(encoding="utf-8"), original)

    def test_resultado_privado_e_redigido_do_log(self):
        with tempfile.TemporaryDirectory(prefix="nyxal-private-audit-") as tmp:
            arquivo = Path(tmp) / "auditoria.json"
            catalogo = Path(tmp) / "capacidades.json"
            with patch.object(nixal_capacidades, "ARQUIVO_LOG", arquivo):
                with patch.object(nixal_capacidades, "ARQUIVO_CAPACIDADES", catalogo):
                    manager = GerenciadorCapacidades()
                    manager._registrar_execucao(ResultadoCapacidade(
                        sucesso=True,
                        capacidade="consultar_emails_google",
                        resultado={"corpo_texto": "segredo-de-teste"},
                        timestamp=1.0,
                        duracao_ms=1.0,
                    ))
            gravado = arquivo.read_text(encoding="utf-8")
            self.assertNotIn("segredo-de-teste", gravado)
            self.assertIn("conteudo_omitido", gravado)

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


    def test_aisweb_read_tools_are_registered_by_default(self):
        registrar_capacidades_operacionais(self.capacidades, store=self.store)
        nomes = self.nomes()
        self.assertTrue({"consultar_notam_aisweb", "consultar_cartas_aisweb"} <= nomes)
        self.assertTrue(FERRAMENTAS_MUTAVEIS.isdisjoint(nomes))
        self.assertEqual(
            self.capacidades.capacidades["consultar_notam_aisweb"].funcao.__name__,
            "consultar_notam_aisweb",
        )
        self.assertEqual(
            self.capacidades.capacidades["consultar_cartas_aisweb"].funcao.__name__,
            "consultar_cartas_aisweb",
        )

    def test_aisweb_validation_blocks_invalid_queries_before_network(self):
        with patch.object(nixal_tool_use, "_aisweb_consultar") as consultar:
            notam = nixal_tool_use.consultar_notam_aisweb("SBSP;curl")
            fir = nixal_tool_use.consultar_notam_aisweb("SBSP", fir="XX")
            sem_filtro = nixal_tool_use.consultar_cartas_aisweb()
            especie_sem_tipo = nixal_tool_use.consultar_cartas_aisweb(especie="IFR")
            tipo_invalido = nixal_tool_use.consultar_cartas_aisweb(especie="VFR", tipo="IAC")
        self.assertEqual(notam["estado"], "icao_invalido")
        self.assertEqual(fir["estado"], "fir_invalida")
        self.assertEqual(sem_filtro["estado"], "filtro_obrigatorio")
        self.assertEqual(especie_sem_tipo["estado"], "tipo_obrigatorio")
        self.assertEqual(tipo_invalido["estado"], "tipo_invalido")
        consultar.assert_not_called()

    def test_aisweb_requires_credentials_without_network(self):
        with patch.dict(os.environ, {
            "NYXAL_AISWEB_API_KEY": "",
            "NYXAL_AISWEB_API_PASS": "",
        }):
            with patch.object(nixal_tool_use, "build_opener") as opener:
                notam = nixal_tool_use.consultar_notam_aisweb("SBSP")
                cartas = nixal_tool_use.consultar_cartas_aisweb(icao="SBSP")
        self.assertEqual(notam["estado"], "configuracao_pendente")
        self.assertEqual(cartas["estado"], "configuracao_pendente")
        opener.assert_not_called()

    def test_aisweb_xml_response_is_bounded_and_credentials_are_not_returned(self):
        class FakeResponse:
            status = 200

            def __init__(self, payload):
                self.payload = payload

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self, _limit):
                return self.payload

        class FakeOpener:
            def __init__(self, payload):
                self.payload = payload
                self.request = None

            def open(self, request, timeout):
                self.request = request
                self.timeout = timeout
                return FakeResponse(self.payload)

        fake = FakeOpener(
            b"<aisweb><notams><notam><icao>SBSP</icao><texto>PISTA FECHADA</texto></notam></notams></aisweb>"
        )
        with patch.dict(os.environ, {
            "NYXAL_AISWEB_API_KEY": "fake-key-for-test",
            "NYXAL_AISWEB_API_PASS": "fake-pass-for-test",
        }):
            with patch.object(nixal_tool_use, "build_opener", return_value=fake):
                resultado = nixal_tool_use.consultar_notam_aisweb("SBSP", limite=5)

        self.assertTrue(resultado["sucesso"])
        self.assertEqual(resultado["estado"], "consulta_concluida")
        self.assertEqual(resultado["area"], "notam")
        self.assertIn("PISTA FECHADA", str(resultado["dados"]))
        self.assertNotIn("fake-key-for-test", str(resultado))
        self.assertNotIn("fake-pass-for-test", str(resultado))
        self.assertIn("apiKey=fake-key-for-test", fake.request.full_url)
        self.assertEqual(fake.timeout, 10)

    def test_aisweb_rejects_xml_entity_declarations(self):
        class FakeResponse:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self, _limit):
                return b"<!DOCTYPE x [<!ENTITY e SYSTEM 'file:///etc/passwd'>]><aisweb>&e;</aisweb>"

        class FakeOpener:
            def open(self, _request, timeout):
                self.timeout = timeout
                return FakeResponse()

        with patch.dict(os.environ, {
            "NYXAL_AISWEB_API_KEY": "fake-key-for-test",
            "NYXAL_AISWEB_API_PASS": "fake-pass-for-test",
        }):
            with patch.object(nixal_tool_use, "build_opener", return_value=FakeOpener()):
                resultado = nixal_tool_use.consultar_notam_aisweb("SBSP")
        self.assertEqual(resultado["estado"], "xml_nao_permitido")

    def test_aisweb_payload_over_limit_is_rejected(self):
        class FakeResponse:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self, _limit):
                return b"x" * (nixal_tool_use.MAX_AISWEB_BYTES + 1)

        class FakeOpener:
            def open(self, _request, timeout):
                return FakeResponse()

        with patch.dict(os.environ, {
            "NYXAL_AISWEB_API_KEY": "fake-key-for-test",
            "NYXAL_AISWEB_API_PASS": "fake-pass-for-test",
        }):
            with patch.object(nixal_tool_use, "build_opener", return_value=FakeOpener()):
                resultado = nixal_tool_use.consultar_notam_aisweb("SBSP")
        self.assertEqual(resultado["estado"], "resposta_muito_grande")

    def test_qwen_exposes_aisweb_as_default_read_only_tools(self):
        source = (Path(__file__).resolve().parent / "nixal_dialogo_qwen.py").read_text(encoding="utf-8")
        start = source.index("FERRAMENTAS_LEITURA_PADRAO = frozenset({")
        end = source.index("})", start)
        allowlist = source[start:end]
        self.assertIn('"consultar_notam_aisweb"', allowlist)
        self.assertIn('"consultar_cartas_aisweb"', allowlist)
        self.assertNotIn('"salvar_nota"', allowlist)


class TesteIntegracaoAgenteQwen(unittest.TestCase):
    def _agente(self, privado: bool):
        from nixal_agente_qwen import AgenteNixalQwen

        with tempfile.TemporaryDirectory(prefix="nyxal-agent-tool-test-") as temp:
            with patch.object(
                nixal_capacidades,
                "ARQUIVO_CAPACIDADES",
                Path(temp) / "capacidades.json",
            ):
                with patch.object(nixal_capacidades, "ARQUIVO_LOG", Path(temp) / "auditoria.json"):
                    valor = "1" if privado else ""
                    with patch.dict(os.environ, {
                        "NYXAL_ENABLE_PRIVATE_READ_TOOLS": valor,
                        "NYXAL_ENABLE_MUTABLE_TOOLS": "",
                    }):
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
