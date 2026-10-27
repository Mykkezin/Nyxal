#!/usr/bin/env python3
"""Regressões da memória conversacional volátil/persistente da Nyxal."""
from __future__ import annotations

import json
import os
import stat
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from nixal_memoria_conversacional import MemoriaConversacionalNixal


class TesteMemoriaConversacionalNixal(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.raiz = Path(self.tmp.name)
        self.caminho = self.raiz / "privado" / "conversas.json"

    def test_modo_volatil_preserva_o_contrato_legado(self) -> None:
        with patch.dict(os.environ, {"NYXAL_CONVERSATION_MEMORY_PATH": ""}):
            memoria = MemoriaConversacionalNixal()
        gravado = memoria.registrar("sessao-volatil", "user", "Olá")
        self.assertTrue(gravado["sucesso"])
        self.assertFalse(gravado["persistido"])
        self.assertEqual(memoria.obter("sessao-volatil")["mensagens"][0]["texto"], "Olá")
        self.assertEqual(memoria.estado()["estado"], "memoria_volatil")

    def test_persistencia_sobrevive_ao_reinicio_da_instancia(self) -> None:
        primeira = MemoriaConversacionalNixal(caminho=self.caminho)
        primeira.registrar("sessao-a", "user", "Lembre-se do contexto")
        primeira.registrar("sessao-a", "assistant", "Contexto recebido")

        segunda = MemoriaConversacionalNixal(caminho=self.caminho)
        resultado = segunda.obter("sessao-a")
        self.assertTrue(resultado["sucesso"])
        self.assertEqual(
            [(x["papel"], x["texto"]) for x in resultado["mensagens"]],
            [("user", "Lembre-se do contexto"), ("assistant", "Contexto recebido")],
        )
        self.assertEqual(segunda.estado()["estado"], "persistencia_ativa")

    def test_persistencia_respeita_janela_de_mensagens(self) -> None:
        memoria = MemoriaConversacionalNixal(max_mensagens=3, caminho=self.caminho)
        for numero in range(5):
            memoria.registrar("sessao-a", "user", f"mensagem-{numero}")
        obtida = MemoriaConversacionalNixal(max_mensagens=3, caminho=self.caminho).obter("sessao-a")
        self.assertEqual([x["texto"] for x in obtida["mensagens"]], ["mensagem-2", "mensagem-3", "mensagem-4"])

    def test_arquivo_e_diretorio_de_memoria_ficam_privados(self) -> None:
        memoria = MemoriaConversacionalNixal(caminho=self.caminho)
        self.assertTrue(memoria.registrar("sessao-a", "user", "conteúdo privado")["sucesso"])
        self.assertEqual(stat.S_IMODE(self.caminho.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.caminho.parent.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(self.caminho.with_name(self.caminho.name + ".lock").stat().st_mode), 0o600)

    def test_json_corrompido_falha_fechado_e_preserva_bytes_originais(self) -> None:
        self.caminho.parent.mkdir(parents=True)
        original = b'{"versao":'
        self.caminho.write_bytes(original)
        memoria = MemoriaConversacionalNixal(caminho=self.caminho)

        estado = memoria.estado()
        resultado = memoria.registrar("sessao-a", "user", "não sobrescrever")
        leitura = memoria.obter("sessao-a")

        self.assertFalse(estado["sucesso"])
        self.assertEqual(estado["estado"], "memoria_degradada")
        self.assertFalse(resultado["sucesso"])
        self.assertEqual(resultado["estado"], "memoria_degradada")
        self.assertFalse(leitura["sucesso"])
        self.assertEqual(self.caminho.read_bytes(), original)

    def test_schema_desconhecido_falha_fechado_e_preserva_arquivo(self) -> None:
        self.caminho.parent.mkdir(parents=True)
        original = json.dumps({"versao": 999, "sessoes": {}}).encode()
        self.caminho.write_bytes(original)
        memoria = MemoriaConversacionalNixal(caminho=self.caminho)
        resultado = memoria.limpar("sessao-a")
        self.assertFalse(resultado["sucesso"])
        self.assertEqual(resultado["estado"], "memoria_degradada")
        self.assertEqual(self.caminho.read_bytes(), original)

    def test_limpar_remove_a_sessao_de_forma_persistente(self) -> None:
        memoria = MemoriaConversacionalNixal(caminho=self.caminho)
        memoria.registrar("sessao-a", "user", "remover")
        removido = memoria.limpar("sessao-a")
        nova_instancia = MemoriaConversacionalNixal(caminho=self.caminho)
        self.assertEqual(removido["estado"], "contexto_limpo")
        self.assertFalse(nova_instancia.possui_sessao("sessao-a"))

    def test_instancias_concorrentes_nao_sobrescrevem_sessoes(self) -> None:
        quantidade = 10
        barreira = threading.Barrier(quantidade)
        erros: list[str] = []

        def escrever(indice: int) -> None:
            try:
                memoria = MemoriaConversacionalNixal(caminho=self.caminho)
                barreira.wait(timeout=5)
                resultado = memoria.registrar(f"sessao-{indice}", "user", f"mensagem-{indice}")
                if resultado.get("sucesso") is not True:
                    erros.append(f"sessao-{indice}:{resultado.get('estado')}")
            except Exception as exc:
                erros.append(type(exc).__name__)

        threads = [threading.Thread(target=escrever, args=(i,)) for i in range(quantidade)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
        self.assertFalse(any(thread.is_alive() for thread in threads), "threads presas na persistência")
        self.assertEqual(erros, [])
        recuperada = MemoriaConversacionalNixal(caminho=self.caminho)
        for indice in range(quantidade):
            com = recuperada.obter(f"sessao-{indice}")
            self.assertTrue(com["sucesso"])
            self.assertEqual(com["mensagens"][0]["texto"], f"mensagem-{indice}")

    def test_validacao_de_entrada_e_limites(self) -> None:
        memoria = MemoriaConversacionalNixal(caminho=self.caminho)
        self.assertFalse(memoria.registrar("", "user", "x")["sucesso"])
        self.assertFalse(memoria.registrar("s", "system", "x")["sucesso"])
        self.assertFalse(memoria.registrar("s", "user", "x" * (memoria.MAX_CARACTERES_MENSAGEM + 1))["sucesso"])
        self.assertFalse(memoria.obter("s", limite=True)["sucesso"])
        self.assertFalse(memoria.registrar("s" * (memoria.MAX_CARACTERES_SESSAO + 1), "user", "x")["sucesso"])


if __name__ == "__main__":
    unittest.main()
