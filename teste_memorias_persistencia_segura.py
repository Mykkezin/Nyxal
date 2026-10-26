#!/usr/bin/env python3
"""Regressões de corrupção, preservação e concorrência das memórias duráveis."""
from __future__ import annotations

import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import nixal_memoria_investigacao as modulo_investigacao
import nixal_memoria_conhecimento as modulo_conhecimento
from nixal_memoria_investigacao import MemoriaInvestigacaoNixal
from nixal_memoria_conhecimento import MemoriaConhecimentoNixal


def ciclo(hipotese: str) -> dict:
    return {
        "necessidade": "auditar persistência",
        "hipotese": hipotese,
        "estado_atual": "provisoria",
        "historico": [],
        "testes": [],
        "avaliacoes": [],
        "conhecimento_permanente": False,
    }


def candidato(texto: str) -> dict:
    return {
        "texto": texto,
        "tipo": "observacao",
        "origem": {"estado": "suportada"},
        "conhecimento_permanente": False,
        "gravado": False,
    }


class TesteMemoriasPersistenciaSegura(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_investigacao_corrompida_e_preservada_e_bloqueia_gravacao(self):
        path = self.root / "memoria_investigacao_nixal.json"
        original = '{"versao":'
        path.write_text(original, encoding="utf-8")

        memoria = MemoriaInvestigacaoNixal(path)
        estado = memoria.recarregar()
        escrita = memoria.registrar(ciclo("nova hipótese"))

        self.assertIs(estado.get("sucesso"), False)
        self.assertEqual(estado.get("estado"), "memoria_degradada")
        self.assertTrue(estado.get("arquivo_original_preservado"))
        self.assertEqual(escrita.get("estado"), "negado")
        self.assertEqual(path.read_text(encoding="utf-8"), original)

    def test_versao_desconhecida_na_investigacao_nao_e_sobrescrita(self):
        path = self.root / "memoria_investigacao_nixal.json"
        original = '{"versao":"futura","registros":[]}'
        path.write_text(original, encoding="utf-8")

        memoria = MemoriaInvestigacaoNixal(path)
        self.assertIs(memoria.recarregar().get("sucesso"), False)
        self.assertEqual(memoria.registrar(ciclo("nova hipótese")).get("estado"), "negado")
        self.assertEqual(path.read_text(encoding="utf-8"), original)

    def test_conhecimento_corrompido_e_preservado_e_bloqueia_gravacao(self):
        path = self.root / "memoria_conhecimento_nixal.json"
        original = "{malformed"
        path.write_text(original, encoding="utf-8")

        memoria = MemoriaConhecimentoNixal(path)
        estado = memoria.recarregar()
        escrita = memoria.registrar(candidato("novo candidato"))

        self.assertIs(estado.get("sucesso"), False)
        self.assertEqual(estado.get("estado"), "memoria_degradada")
        self.assertTrue(estado.get("arquivo_original_preservado"))
        self.assertEqual(escrita.get("estado"), "negado")
        self.assertEqual(path.read_text(encoding="utf-8"), original)

    def test_listar_recent_copia_apenas_o_sufixo_e_nao_altera_a_memoria(self):
        path = self.root / "memoria_investigacao_nixal.json"
        memoria = MemoriaInvestigacaoNixal(path)
        for nome in ("hipótese A", "hipótese B", "hipótese C"):
            self.assertEqual(memoria.registrar(ciclo(nome)).get("estado"), "persistido")

        recentes = memoria.listar_recent(2)
        self.assertEqual(
            [registro["ciclo"]["hipotese"] for registro in recentes],
            ["hipótese B", "hipótese C"],
        )
        recentes[0]["ciclo"]["hipotese"] = "alterada fora"
        self.assertEqual(
            memoria.listar_recent(2)[0]["ciclo"]["hipotese"],
            "hipótese B",
        )

    def test_listar_recent_rejeita_limites_invalidos(self):
        memoria = MemoriaInvestigacaoNixal(self.root / "memoria_investigacao_nixal.json")
        for limite in (0, -1, True, 5001, "2"):
            with self.subTest(limite=limite):
                with self.assertRaises(ValueError):
                    memoria.listar_recent(limite)

    def test_instancias_antigas_nao_perdem_registros_de_investigacao(self):
        path = self.root / "memoria_investigacao_nixal.json"
        primeira = MemoriaInvestigacaoNixal(path)
        segunda = MemoriaInvestigacaoNixal(path)

        self.assertEqual(primeira.registrar(ciclo("hipótese A")).get("estado"), "persistido")
        self.assertEqual(segunda.registrar(ciclo("hipótese B")).get("estado"), "persistido")

        recuperada = MemoriaInvestigacaoNixal(path)
        self.assertEqual(recuperada.quantidade(), 2)

    def test_instancias_antigas_nao_perdem_candidatos_de_conhecimento(self):
        path = self.root / "memoria_conhecimento_nixal.json"
        primeira = MemoriaConhecimentoNixal(path)
        segunda = MemoriaConhecimentoNixal(path)

        self.assertEqual(primeira.registrar(candidato("candidato A")).get("estado"), "persistido")
        self.assertEqual(segunda.registrar(candidato("candidato B")).get("estado"), "persistido")

        recuperada = MemoriaConhecimentoNixal(path)
        self.assertEqual(recuperada.quantidade(), 2)

    def test_memoria_investigacao_acima_do_teto_e_preservada(self):
        path = self.root / "memoria_investigacao_nixal.json"
        original = b" " * 65
        path.write_bytes(original)
        with patch.object(modulo_investigacao, "MAX_MEMORIA_JSON_BYTES", 64):
            memoria = MemoriaInvestigacaoNixal(path)
            estado = memoria.recarregar()
            escrita = memoria.registrar(ciclo("nova hipótese"))
        self.assertIs(estado.get("sucesso"), False)
        self.assertEqual(estado.get("estado"), "memoria_degradada")
        self.assertEqual(escrita.get("estado"), "negado")
        self.assertEqual(path.read_bytes(), original)

    def test_memoria_conhecimento_acima_do_teto_e_preservada(self):
        path = self.root / "memoria_conhecimento_nixal.json"
        original = b" " * 65
        path.write_bytes(original)
        with patch.object(modulo_conhecimento, "MAX_MEMORIA_JSON_BYTES", 64):
            memoria = MemoriaConhecimentoNixal(path)
            estado = memoria.recarregar()
            escrita = memoria.registrar(candidato("nova observação"))
        self.assertIs(estado.get("sucesso"), False)
        self.assertEqual(estado.get("estado"), "memoria_degradada")
        self.assertEqual(escrita.get("estado"), "negado")
        self.assertEqual(path.read_bytes(), original)

    def test_nova_investigacao_que_excede_teto_nao_substitui_arquivo_valido(self):
        path = self.root / "memoria_investigacao_nixal.json"
        memoria = MemoriaInvestigacaoNixal(path)
        self.assertIs(memoria.registrar(ciclo("hipótese inicial")).get("sucesso"), True)
        original = path.read_bytes()
        limite = len(original) + 120
        with patch.object(modulo_investigacao, "MAX_MEMORIA_JSON_BYTES", limite):
            resultado = memoria.registrar(ciclo("hipótese longa " + "x" * 400))
        self.assertIs(resultado.get("sucesso"), False)
        self.assertIn("memoria_excede_limite_tamanho", resultado.get("motivo", ""))
        self.assertEqual(path.read_bytes(), original)
        self.assertIs(MemoriaInvestigacaoNixal(path).recarregar().get("sucesso"), True)

    def test_novo_candidato_que_excede_teto_nao_substitui_arquivo_valido(self):
        path = self.root / "memoria_conhecimento_nixal.json"
        memoria = MemoriaConhecimentoNixal(path)
        self.assertIs(memoria.registrar(candidato("candidato inicial")).get("sucesso"), True)
        original = path.read_bytes()
        limite = len(original) + 120
        with patch.object(modulo_conhecimento, "MAX_MEMORIA_JSON_BYTES", limite):
            resultado = memoria.registrar(candidato("candidato longo " + "x" * 400))
        self.assertIs(resultado.get("sucesso"), False)
        self.assertIn("memoria_excede_limite_tamanho", resultado.get("motivo", ""))
        self.assertEqual(path.read_bytes(), original)
        self.assertIs(MemoriaConhecimentoNixal(path).recarregar().get("sucesso"), True)

    def test_arquivo_persistido_recebe_permissao_proprietario(self):
        path = self.root / "memoria_investigacao_nixal.json"
        memoria = MemoriaInvestigacaoNixal(path)
        self.assertEqual(memoria.registrar(ciclo("hipótese segura")).get("estado"), "persistido")
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        lock_path = path.with_name(path.name + ".lock")
        self.assertEqual(stat.S_IMODE(lock_path.stat().st_mode), 0o600)


if __name__ == "__main__":
    unittest.main(verbosity=2)
