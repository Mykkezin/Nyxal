#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import nixal_tool_use as tools


class TestFerramentasNyxal(unittest.TestCase):
    def test_anotacao_persistida_e_listada(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = tools.NotasLembretesNixOS(Path(tmp) / "notas.json")
            saved = store.salvar_nota("Estudo", "Revisar navegação")
            listing = store.listar("notas")
            self.assertTrue(saved["sucesso"])
            self.assertEqual(listing["notas"][0]["conteudo"], "Revisar navegação")
            self.assertEqual(Path(saved["local"]).stat().st_mode & 0o777, 0o600)

    def test_lembrete_futuro_e_validacao_de_passado(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = tools.NotasLembretesNixOS(Path(tmp) / "notas.json")
            when = (datetime.now().astimezone() + timedelta(hours=1)).isoformat(timespec="seconds")
            scheduled = store.criar_lembrete("Estudar METAR", when)
            past = store.criar_lembrete("Não deve ser aceito", "2000-01-01T12:00:00-03:00")
            self.assertTrue(scheduled["sucesso"])
            self.assertEqual(scheduled["lembrete"]["estado"], "pendente")
            self.assertEqual(past["estado"], "data_hora_no_passado")

    def test_json_corrompido_nao_e_substituido(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "notas.json"
            original = "{json corrompido"
            file.write_text(original, encoding="utf-8")
            store = tools.NotasLembretesNixOS(file)
            with self.assertRaises(RuntimeError):
                store.salvar_nota("Título", "Conteúdo")
            self.assertEqual(file.read_text(encoding="utf-8"), original)

    def test_metar_rejeita_icao_invalido_sem_rede(self):
        result = tools.consultar_metar_taf("SB")
        self.assertFalse(result["sucesso"])
        self.assertEqual(result["estado"], "icao_invalido")

    def test_home_assistant_sem_segredos_retorna_configuracao_pendente(self):
        with patch.dict(os.environ, {
            "NYXAL_HOME_ASSISTANT_URL": "",
            "NYXAL_HOME_ASSISTANT_TOKEN": "",
        }):
            result = tools.consultar_home_assistant()
        self.assertEqual(result["estado"], "configuracao_pendente")
        self.assertFalse(result["acoes_fisicas_habilitadas"])
        self.assertNotIn("token", json.dumps(result).lower())

    def test_leitura_de_arquivo_bloqueia_traversal_e_credenciais(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.txt").write_text("documento público", encoding="utf-8")
            (root / ".env").write_text("SEGREDO=nao-expor", encoding="utf-8")
            with patch.object(tools, "BASE_DIR", root), patch.object(tools, "HOME", root):
                good = tools.ler_arquivo_usuario("README.txt")
                traversal = tools.ler_arquivo_usuario("../outside.txt")
                hidden = tools.ler_arquivo_usuario(".env")
            self.assertTrue(good["sucesso"])
            self.assertEqual(good["conteudo"], "documento público")
            self.assertEqual(traversal["estado"], "caminho_bloqueado")
            self.assertEqual(hidden["estado"], "caminho_bloqueado")

    def test_busca_de_arquivos_omite_credenciais(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "nyxal-search-test.txt").write_text("público", encoding="utf-8")
            (root / ".env.nyxal-search-test").write_text("SEGREDO=nao-expor", encoding="utf-8")
            with patch.object(tools, "BASE_DIR", root), patch.object(tools, "HOME", root):
                result = tools.buscar_arquivos("nyxal-search-test", limite=10)
            paths = [item["caminho"] for item in result["resultados"]]
            self.assertTrue(any(path.endswith("nyxal-search-test.txt") for path in paths))
            self.assertFalse(any(".env" in path for path in paths))

    def test_diagnostico_nao_aceita_comando_livre(self):
        result = tools.executar_diagnostico("rm -rf /")
        self.assertFalse(result["sucesso"])
        self.assertFalse(result["comandos_arbitrarios_habilitados"])

    def test_parser_web_extrai_apenas_titulo_e_url(self):
        parser = tools._DuckDuckGoResults()
        parser.feed('<a class="result__a" href="https://example.test/page"><span>Fonte <b>oficial</b></span></a>')
        self.assertEqual(parser.results, [{"titulo": "Fonte oficial", "url": "https://example.test/page"}])


if __name__ == "__main__":
    unittest.main(verbosity=2)
