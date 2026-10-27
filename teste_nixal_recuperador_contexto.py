#!/usr/bin/env python3
"""Testes da recuperação lexical sobre as memórias duráveis já existentes."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from nixal_contexto_historico_relevante import ContextoHistoricoRelevanteNixal
from nixal_memoria_conhecimento import MemoriaConhecimentoNixal
from nixal_memoria_investigacao import MemoriaInvestigacaoNixal
from nixal_recuperador_contexto import RecuperadorContextoNixal


def ciclo_runner() -> dict:
    return {
        "necessidade": "Diagnosticar o runner privado do GitHub Actions.",
        "pergunta": "Por que a CI privada termina antes do primeiro step?",
        "hipotese": "O runner privado do GitHub Actions falha antes de alocar executor.",
        "estado_atual": "provisoria",
        "historico": [{"evento": "observacao", "descricao": "runner_id=0; steps vazios"}],
        "testes": [{"nome": "runner privado", "estado": "nao_verificado"}],
        "avaliacoes": [{"criterio": "execucao_real", "estado": "inconclusivo"}],
        "conhecimento_permanente": False,
    }


def candidato(texto: str, tipo: str = "conceito", indice: int = 1) -> dict:
    return {
        "texto": texto,
        "tipo": tipo,
        "origem": {
            "estado": "suportada",
            "indice_avaliacao": indice,
            "fonte": "teste-recuperacao",
        },
        "conhecimento_permanente": False,
        "gravado": False,
    }


class TesteRecuperadorContextoNixal(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        raiz = Path(self.tempdir.name)
        self.caminho_investigacao = raiz / "memoria_investigacao.json"
        self.caminho_conhecimento = raiz / "memoria_conhecimento.json"
        self.investigacao = MemoriaInvestigacaoNixal(self.caminho_investigacao)
        self.contexto = ContextoHistoricoRelevanteNixal(self.investigacao)
        self.conhecimento = MemoriaConhecimentoNixal(self.caminho_conhecimento)
        self.recuperador = RecuperadorContextoNixal(
            self.investigacao, self.contexto, self.conhecimento
        )

    def test_recupera_candidato_relevante_com_origem_e_estado_epistemico(self) -> None:
        registro = self.conhecimento.registrar(
            candidato("A estratégia de cache do motor local usa invalidação por versão e TTL.", "arquitetura", 7)
        )
        self.assertTrue(registro["sucesso"])

        resultado = self.recuperador.consultar("Qual era a estratégia de cache do motor local?")
        self.assertTrue(resultado["sucesso"])
        candidatos = resultado["conhecimentos_candidatos"]
        self.assertEqual(len(candidatos), 1)
        item = candidatos[0]
        self.assertIn("invalidação por versão e TTL", item["texto"])
        self.assertEqual(item["origem"]["estado"], "suportada")
        self.assertEqual(item["origem"]["indice_avaliacao"], 7)
        self.assertGreater(item["relevancia_lexical"], 0)
        self.assertFalse(item["conhecimento_permanente"])
        self.assertTrue(item["estado_epistemico"]["nao_equivale_a_verdade"])
        self.assertEqual(resultado["fontes"]["conhecimento_candidato"]["estado"], "conhecimento_candidato_relevante")
        self.assertFalse(resultado["armazenamento_adicional"])

    def test_candidato_sem_sobreposicao_lexical_nao_e_recuperado(self) -> None:
        self.conhecimento.registrar(candidato("A paleta do personagem usa verde esmeralda e dourado.", "arte"))
        resultado = self.recuperador.consultar("Como funciona o roteamento de consultas SQL?")
        self.assertTrue(resultado["sucesso"])
        self.assertEqual(resultado["conhecimentos_candidatos"], [])
        self.assertEqual(resultado["fontes"]["conhecimento_candidato"]["estado"], "sem_candidatos_relevantes")

    def test_candidatos_textualmente_duplicados_sao_deduplicados_no_resultado(self) -> None:
        texto = "O agente local usa um orçamento fixo de chamadas de ferramentas."
        self.conhecimento.registrar(candidato(texto, "arquitetura", 1))
        self.conhecimento.registrar(candidato(texto, "decisao", 2))
        resultado = self.recuperador.consultar("Qual o orçamento de chamadas do agente local?")
        encontrados = resultado["conhecimentos_candidatos"]
        self.assertEqual(len(encontrados), 1)
        self.assertEqual(encontrados[0]["texto"], texto)

    def test_candidato_duplicado_em_investigacao_relevante_e_omitido(self) -> None:
        self.investigacao.registrar(ciclo_runner())
        self.conhecimento.registrar(
            candidato("Diagnosticar o runner privado do GitHub Actions.", "investigacao")
        )
        resultado = self.recuperador.consultar("Onde paramos no diagnóstico do runner privado do GitHub Actions?")
        self.assertTrue(resultado["contextos_historicos"])
        self.assertEqual(resultado["conhecimentos_candidatos"], [])

    def test_memoria_candidata_corrompida_falha_fechada_e_preserva_bytes(self) -> None:
        original = '{"versao":'
        self.caminho_conhecimento.write_text(original, encoding="utf-8")
        memoria_corrompida = MemoriaConhecimentoNixal(self.caminho_conhecimento)
        recuperador = RecuperadorContextoNixal(
            self.investigacao,
            self.contexto,
            memoria_corrompida,
        )
        resultado = recuperador.consultar("estratégia de cache do motor local")
        self.assertTrue(resultado["sucesso"])
        self.assertEqual(resultado["conhecimentos_candidatos"], [])
        self.assertEqual(resultado["fontes"]["conhecimento_candidato"]["estado"], "memoria_degradada")
        self.assertEqual(self.caminho_conhecimento.read_text(encoding="utf-8"), original)

    def test_tokens_e_segredos_de_candidatos_sao_redigidos(self) -> None:
        segredo = "TOKEN-NAO-PODE-SAIR-98765"
        bearer = "BEARER-NAO-PODE-SAIR-12345"
        auth_header = "AUTH-HEADER-NAO-PODE-SAIR-23456"
        gen_token = "TOKEN-GENERICO-NAO-PODE-SAIR-67890"
        self.conhecimento.registrar(
            candidato(
                "A estratégia de cache local inclui validação de origem; "
                f"access_token={segredo}; sessão Bearer {bearer}; "
                f"Authorization: Bearer {auth_header}; token={gen_token}",
                "arquitetura",
            )
        )
        resultado = self.recuperador.consultar("estratégia de cache local validação origem")
        candidatos = resultado["conhecimentos_candidatos"]
        self.assertEqual(len(candidatos), 1)
        texto_seguro = candidatos[0]["texto"]
        for valor in (segredo, bearer, auth_header, gen_token):
            with self.subTest(valor=valor):
                self.assertNotIn(valor, texto_seguro)
        self.assertIn("access_token=[REDACTED]", texto_seguro)
        self.assertIn("Bearer [REDACTED]", texto_seguro)
        self.assertIn("Authorization=[REDACTED]", texto_seguro)
        self.assertIn("token=[REDACTED]", texto_seguro)

    def test_consulta_vazia_e_bloqueada_e_limites_ficam_bem_delimitados(self) -> None:
        consulta = self.recuperador.consultar("   ")
        self.assertFalse(consulta["sucesso"])
        self.assertEqual(consulta["estado"], "consulta_invalida")

        self.conhecimento.registrar(candidato("A estratégia de cache do motor local usa TTL.", "arquitetura"))
        resultado = self.recuperador.consultar(
            "estratégia cache motor local",
            limite_investigacoes=10000,
            limite_conhecimento=10000,
        )
        self.assertLessEqual(len(resultado["conhecimentos_candidatos"]), 5)


if __name__ == "__main__":
    unittest.main()
