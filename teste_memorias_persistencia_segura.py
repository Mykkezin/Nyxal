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

    def test_investigacao_nao_sobrescreve_memoria_quando_exists_reporta_falso(self):
        path = self.root / "memoria_investigacao_nixal.json"
        original = b'{"versao":"futura","registros":[]}'
        path.write_bytes(original)
        exists_real = Path.exists

        def exists_falso_apenas_para_store(caminho):
            return False if caminho == path else exists_real(caminho)

        with patch.object(Path, "exists", new=exists_falso_apenas_para_store):
            memoria = MemoriaInvestigacaoNixal(path)
            estado = memoria.recarregar()
            escrita = memoria.registrar(ciclo("nova hipótese"))

        self.assertIs(estado.get("sucesso"), False)
        self.assertEqual(estado.get("estado"), "memoria_degradada")
        self.assertEqual(escrita.get("estado"), "negado")
        self.assertEqual(path.read_bytes(), original)

    def test_conhecimento_nao_sobrescreve_memoria_quando_exists_reporta_falso(self):
        path = self.root / "memoria_conhecimento_nixal.json"
        original = b'{"versao":"futura","registros":[]}'
        path.write_bytes(original)
        exists_real = Path.exists

        def exists_falso_apenas_para_store(caminho):
            return False if caminho == path else exists_real(caminho)

        with patch.object(Path, "exists", new=exists_falso_apenas_para_store):
            memoria = MemoriaConhecimentoNixal(path)
            estado = memoria.recarregar()
            escrita = memoria.registrar(candidato("nova observação"))

        self.assertIs(estado.get("sucesso"), False)
        self.assertEqual(estado.get("estado"), "memoria_degradada")
        self.assertEqual(escrita.get("estado"), "negado")
        self.assertEqual(path.read_bytes(), original)

    def _store_por_tipo(self, tipo, caminho):
        if tipo == "investigacao":
            return MemoriaInvestigacaoNixal(caminho)
        return MemoriaConhecimentoNixal(caminho)

    def _registrar_por_tipo(self, tipo, memoria):
        if tipo == "investigacao":
            return memoria.registrar(ciclo("hipótese de persistência"))
        return memoria.registrar(candidato("observação de persistência"))

    def test_ancestrais_simbolicos_sao_rejeitados_antes_de_criar_diretorios(self):
        destino = self.root / "destino-real"
        destino.mkdir(mode=0o700)
        link = self.root / "atalho"
        link.symlink_to(destino, target_is_directory=True)

        for tipo in ("investigacao", "conhecimento"):
            with self.subTest(tipo=tipo):
                caminho = link / "nao-criar" / f"{tipo}.json"
                memoria = self._store_por_tipo(tipo, caminho)

                estado = memoria.recarregar()
                resultado = self._registrar_por_tipo(tipo, memoria)

                self.assertEqual(estado.get("estado"), "memoria_degradada")
                self.assertIn("link_simbolico", estado.get("motivo", ""))
                self.assertEqual(resultado.get("estado"), "negado")
                self.assertFalse((destino / "nao-criar").exists())
                self.assertFalse(caminho.exists())
                self.assertFalse(caminho.with_name(caminho.name + ".lock").exists())

    def test_arquivo_de_memoria_simbolico_nao_e_lido_nem_substituido(self):
        alvo = self.root / "memoria-real.json"
        original = b'{"dados":"nao tocar"}'
        alvo.write_bytes(original)

        for tipo in ("investigacao", "conhecimento"):
            with self.subTest(tipo=tipo):
                caminho = self.root / f"{tipo}.json"
                caminho.symlink_to(alvo)
                memoria = self._store_por_tipo(tipo, caminho)

                estado = memoria.recarregar()
                resultado = self._registrar_por_tipo(tipo, memoria)

                self.assertEqual(estado.get("estado"), "memoria_degradada")
                self.assertIn("link_simbolico", estado.get("motivo", ""))
                self.assertEqual(resultado.get("estado"), "negado")
                self.assertTrue(caminho.is_symlink())
                self.assertEqual(alvo.read_bytes(), original)
                self.assertFalse(caminho.with_name(caminho.name + ".lock").exists())
                caminho.unlink()

    def test_lock_simbolico_e_rejeitado_sem_alterar_o_alvo(self):
        for tipo in ("investigacao", "conhecimento"):
            with self.subTest(tipo=tipo):
                caminho = self.root / f"{tipo}.json"
                lock_alvo = self.root / f"{tipo}-lock-real"
                original = b"lock externo preservado"
                lock_alvo.write_bytes(original)
                lock_path = caminho.with_name(caminho.name + ".lock")
                lock_path.symlink_to(lock_alvo)

                memoria = self._store_por_tipo(tipo, caminho)
                resultado = self._registrar_por_tipo(tipo, memoria)

                self.assertEqual(resultado.get("estado"), "negado")
                self.assertFalse(caminho.exists())
                self.assertTrue(lock_path.is_symlink())
                self.assertEqual(lock_alvo.read_bytes(), original)
                lock_path.unlink()

    def test_arquivo_persistido_recebe_permissao_proprietario(self):
        path = self.root / "memoria_investigacao_nixal.json"
        memoria = MemoriaInvestigacaoNixal(path)
        self.assertEqual(memoria.registrar(ciclo("hipótese segura")).get("estado"), "persistido")
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        lock_path = path.with_name(path.name + ".lock")
        self.assertEqual(stat.S_IMODE(lock_path.stat().st_mode), 0o600)


if __name__ == "__main__":
    unittest.main(verbosity=2)
