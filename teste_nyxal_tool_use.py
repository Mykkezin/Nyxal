#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from nixal_tool_use import (
    NotasLembretesNixOS, consultar_home_assistant, consultar_metar_taf,
    ler_arquivo_usuario, buscar_arquivos, executar_diagnostico, _DuckDuckGoResults,
)


class TestFerramentasNyxal(unittest.TestCase):
    def test_anotacao_persistida_com_permissoes_restritas(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = NotasLembretesNixOS(Path(tmp) / "notas.json")
            result = store.salvar_nota("Estudo", "Revisar navegação")
            self.assertTrue(result["sucesso"])
            self.assertEqual(Path(result["local"]).stat().st_mode & 0o777, 0o600)
            self.assertEqual(store.listar("notas")["notas"][0]["conteudo"], "Revisar navegação")

    def test_json_corrompido_nao_e_sobrescrito(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "notas.json"
            original = "{json corrompido"
            path.write_text(original, encoding="utf-8")
            store = NotasLembretesNixOS(path)
            with self.assertRaises(RuntimeError):
                store.salvar_nota("Título", "Conteúdo")
            self.assertEqual(path.read_text(encoding="utf-8"), original)

    def test_metar_recusa_icao_invalido_sem_rede(self):
        result = consultar_metar_taf("SB")
        self.assertFalse(result["sucesso"])
        self.assertEqual(result["estado"], "icao_invalido")

    def test_home_assistant_sem_token_nao_expoe_segredos(self):
        with patch.dict(os.environ, {"NYXAL_HOME_ASSISTANT_URL": "", "NYXAL_HOME_ASSISTANT_TOKEN": ""}):
            result = consultar_home_assistant()
        self.assertEqual(result["estado"], "configuracao_pendente")
        self.assertFalse(result["acoes_fisicas_habilitadas"])
        self.assertNotIn("token", json.dumps(result).lower())

    def test_leitura_bloqueia_traversal_e_dotenv(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.txt").write_text("documento", encoding="utf-8")
            (root / ".env").write_text("SECRET=test", encoding="utf-8")
            with patch("nixal_tool_use.BASE_DIR", root), patch("nixal_tool_use.HOME", root):
                good = ler_arquivo_usuario("README.txt")
                traversal = ler_arquivo_usuario("../outside.txt")
                hidden = ler_arquivo_usuario(".env")
            self.assertTrue(good["sucesso"])
            self.assertEqual(traversal["estado"], "caminho_bloqueado")
            self.assertEqual(hidden["estado"], "caminho_bloqueado")

    def test_busca_omite_dotenv(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "nyxal-tool-search-test.txt").write_text("ok", encoding="utf-8")
            (root / ".env-nyxal-tool-search-test").write_text("SECRET=not-visible", encoding="utf-8")
            with patch("nixal_tool_use.BASE_DIR", root), patch("nixal_tool_use.HOME", root):
                result = buscar_arquivos("nyxal-tool-search-test")
            names = [Path(x["caminho"]).name for x in result["resultados"]]
            self.assertIn("nyxal-tool-search-test.txt", names)
            self.assertFalse(any(name.startswith(".env") for name in names))

    def test_diagnostico_nao_aceita_comando_arbitrario(self):
        result = executar_diagnostico("rm -rf /")
        self.assertFalse(result["sucesso"])
        self.assertFalse(result["comandos_arbitrarios_habilitados"])

    def test_catalogo_privado_e_mutavel_desativado_por_padrao(self):
        from nixal_capacidades import GerenciadorCapacidades
        from nixal_tool_use import registrar_capacidades_operacionais

        manager = GerenciadorCapacidades()
        registrar_capacidades_operacionais(manager)
        nomes = set(manager.capacidades)
        self.assertIn("pesquisar_web", nomes)
        self.assertIn("consultar_metar_taf", nomes)
        self.assertIn("executar_diagnostico", nomes)
        for nome in (
            "buscar_arquivos", "ler_arquivo_usuario", "consultar_emails_google",
            "ler_email_google", "consultar_agenda_google", "consultar_home_assistant",
            "listar_notas_lembretes", "salvar_nota", "criar_lembrete", "abrir_aplicativo",
        ):
            self.assertNotIn(nome, nomes)

    def test_dados_privados_exigem_opt_in_separado_de_acoes(self):
        from nixal_capacidades import GerenciadorCapacidades
        from nixal_tool_use import registrar_capacidades_operacionais

        manager = GerenciadorCapacidades()
        registrar_capacidades_operacionais(manager, incluir_dados_privados=True)
        nomes = set(manager.capacidades)
        self.assertIn("buscar_arquivos", nomes)
        self.assertIn("ler_arquivo_usuario", nomes)
        self.assertIn("consultar_emails_google", nomes)
        self.assertIn("listar_notas_lembretes", nomes)
        self.assertNotIn("salvar_nota", nomes)
        self.assertNotIn("criar_lembrete", nomes)
        self.assertNotIn("abrir_aplicativo", nomes)

    def test_acoes_so_aparecem_com_opt_in_mutavel(self):
        from nixal_capacidades import GerenciadorCapacidades
        from nixal_tool_use import registrar_capacidades_operacionais

        manager = GerenciadorCapacidades()
        registrar_capacidades_operacionais(manager, incluir_acoes=True)
        nomes = set(manager.capacidades)
        self.assertIn("salvar_nota", nomes)
        self.assertIn("criar_lembrete", nomes)
        self.assertIn("abrir_aplicativo", nomes)
        self.assertNotIn("buscar_arquivos", nomes)
        self.assertNotIn("consultar_emails_google", nomes)


    def test_parser_resultado_web(self):
        parser = _DuckDuckGoResults()
        parser.feed('<a class="result__a" href="https://example.test/doc"><span>Fonte <b>oficial</b></span></a>')
        self.assertEqual(parser.results, [{"titulo": "Fonte oficial", "url": "https://example.test/doc"}])


if __name__ == "__main__":
    unittest.main(verbosity=2)
