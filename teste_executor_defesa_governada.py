#!/usr/bin/env python3
"""Regressões do gate de preparação dry-run para defesa governada."""
from __future__ import annotations

import json
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from nixal_executor_defesa_governada import (
    ExecutorDefesaGovernada,
    TIPOS_RECOMENDACAO,
)


class RelogioFalso:
    def __init__(self) -> None:
        self.valor = 1000.0

    def __call__(self) -> float:
        return self.valor

    def avancar(self, segundos: float) -> None:
        self.valor += segundos


def recomendacao(tipo: str = "bloqueio_temporario_origem", **kwargs):
    base = {
        "tipo": tipo,
        "escopo": "203.0.113.10",
        "motivo": "limiar de teste observado",
        "duracao_segundos": 300,
        "exige_aprovacao_humana": False,
        # Esses campos recebidos não podem autorizar efeitos.
        "executor_autorizado": True,
        "efeito_executado": True,
    }
    base.update(kwargs)
    return base


class TesteExecutorDefesaGovernada(unittest.TestCase):
    def setUp(self) -> None:
        self.relogio = RelogioFalso()
        self.executor = ExecutorDefesaGovernada(
            ttl_segundos=30,
            janela_idempotencia_segundos=30,
            relogio=self.relogio,
        )

    def test_plano_de_contemporalidade_exige_aprovacao_e_nunca_executa(self) -> None:
        resultado = self.executor.preparar(recomendacao())
        self.assertEqual(resultado["estado"], "aguardando_aprovacao")
        self.assertFalse(resultado["executor_ativo"])
        self.assertFalse(resultado["executor_autorizado"])
        self.assertFalse(resultado["efeito_executado"])
        plano = resultado["plano"]
        self.assertEqual(plano["modo"], "dry_run")
        self.assertTrue(plano["exige_aprovacao_humana"])
        self.assertFalse(plano["aprovacao_verificada"])

    def test_aprovacao_verificada_apenas_prepara_simulacao(self) -> None:
        executor = ExecutorDefesaGovernada(
            relogio=self.relogio,
            verificador_aprovacao=lambda comprovante: comprovante.get("assinatura") == "valida",
        )
        resultado = executor.preparar(
            recomendacao(),
            aprovacao={"assinatura": "valida", "aprovador": "operador-teste"},
        )
        self.assertEqual(resultado["estado"], "simulacao_preparada")
        self.assertTrue(resultado["plano"]["aprovacao_verificada"])
        # Aprovação é registrada como verificada; nunca é autoridade de execução.
        self.assertFalse(resultado["executor_ativo"])
        self.assertFalse(resultado["executor_autorizado"])
        self.assertFalse(resultado["efeito_executado"])

    def test_recomendacao_nao_pode_rebaixar_gate_humano(self) -> None:
        for tipo in (
            "preservar_evidencia",
            "solicitar_revisao_de_incidente",
            "limitar_taxa_origem",
            "bloqueio_temporario_origem",
            "isolar_servico",
            "propor_reinicio_controlado",
            "revogar_credencial",
            "quarentenar_artefato",
            "encaminhar_para_enganacao_isolada",
        ):
            with self.subTest(tipo=tipo):
                item = recomendacao(tipo)
                if tipo in {"preservar_evidencia", "solicitar_revisao_de_incidente"}:
                    item.update(escopo="evt-1")
                    item.pop("duracao_segundos", None)
                elif tipo in {"isolar_servico", "propor_reinicio_controlado"}:
                    item.update(escopo="nyxal-api")
                    item.pop("duracao_segundos", None)
                elif tipo == "revogar_credencial":
                    item.update(escopo="cred-1")
                    item.pop("duracao_segundos", None)
                elif tipo == "quarentenar_artefato":
                    item.update(escopo="sha256:abc")
                    item.pop("duracao_segundos", None)
                elif tipo == "encaminhar_para_enganacao_isolada":
                    item.update(escopo="decoy-service-interno")
                resultado = self.executor.preparar(item)
                self.assertEqual(resultado["estado"], "aguardando_aprovacao")
                self.assertTrue(resultado["plano"]["exige_aprovacao_humana"])
                self.assertFalse(resultado["efeito_executado"])

    def test_alerta_operacional_pode_ser_preparado_sem_aprovacao(self) -> None:
        resultado = self.executor.preparar(recomendacao(
            "alertar_operador",
            escopo="defesa-nyxal",
            motivo="Alerta sem efeito de estado.",
            exige_aprovacao_humana=False,
        ))
        self.assertEqual(resultado["estado"], "simulacao_preparada")
        self.assertFalse(resultado["executor_ativo"])
        self.assertFalse(resultado["efeito_executado"])

    def test_allowlist_aceita_tipos_conhecidos_e_rejeita_tipo_desconhecido(self) -> None:
        self.assertEqual(len(TIPOS_RECOMENDACAO), 10)
        rejeitada = self.executor.preparar(recomendacao("shell_command", escopo="rm -rf /"))
        self.assertFalse(rejeitada["sucesso"])
        self.assertEqual(rejeitada["estado"], "recomendacao_rejeitada")
        self.assertFalse(rejeitada["efeito_executado"])

    def test_loopback_nao_gera_plano_de_contencao(self) -> None:
        for ip in ("127.0.0.1", "::1", "0.0.0.0", "224.0.0.1", "255.255.255.255"):
            with self.subTest(ip=ip):
                resultado = self.executor.preparar(recomendacao(escopo=ip))
                self.assertEqual(resultado["estado"], "recomendacao_rejeitada")
                self.assertFalse(resultado["efeito_executado"])

    def test_servico_fora_da_allowlist_e_rejeitado(self) -> None:
        resultado = self.executor.preparar(recomendacao(
            "isolar_servico",
            escopo="ssh; curl attacker.example",
            motivo="teste de escopo",
        ))
        self.assertEqual(resultado["estado"], "recomendacao_rejeitada")

    def test_identificador_de_credencial_ou_artefato_nao_aceita_caminho(self) -> None:
        casos = (
            recomendacao("revogar_credencial", escopo="../../etc/passwd", motivo="id inválido"),
            recomendacao("quarentenar_artefato", escopo="../../tmp/malware", motivo="id inválido"),
        )
        for item in casos:
            with self.subTest(tipo=item["tipo"]):
                self.assertEqual(
                    self.executor.preparar(item)["estado"],
                    "recomendacao_rejeitada",
                )

    def test_duracao_invalida_e_rejeitada(self) -> None:
        for duracao in (0, -1, 3601, True, 2.5, "300"):
            with self.subTest(duracao=duracao):
                resultado = self.executor.preparar(recomendacao(duracao_segundos=duracao))
                self.assertEqual(resultado["estado"], "recomendacao_rejeitada")

    def test_idempotencia_impede_planos_repetidos_na_janela(self) -> None:
        primeira = self.executor.preparar(recomendacao())
        segunda = self.executor.preparar(recomendacao())
        self.assertEqual(primeira["estado"], "aguardando_aprovacao")
        self.assertEqual(segunda["estado"], "duplicado_idempotente")
        self.assertEqual(primeira["plano_id"], segunda["plano_id"])
        self.assertEqual(len(self.executor.listar_registros()), 1)

    def test_idempotencia_expira_e_permite_novo_plano(self) -> None:
        primeira = self.executor.preparar(recomendacao())
        self.relogio.avancar(31)
        segunda = self.executor.preparar(recomendacao())
        self.assertEqual(segunda["estado"], "aguardando_aprovacao")
        self.assertNotEqual(primeira["plano_id"], segunda["plano_id"])
        self.assertEqual(len(self.executor.listar_registros()), 2)

    def test_verificador_de_aprovacao_com_falha_fecha_por_padrao(self) -> None:
        def falhar(_comprovante):
            raise RuntimeError("erro interno que não deve sair")

        executor = ExecutorDefesaGovernada(
            relogio=self.relogio,
            verificador_aprovacao=falhar,
        )
        resultado = executor.preparar(
            recomendacao(),
            aprovacao={"assinatura": "desconhecida"},
        )
        self.assertEqual(resultado["estado"], "aguardando_aprovacao")
        self.assertFalse(resultado["plano"]["aprovacao_verificada"])
        self.assertNotIn("erro interno", json.dumps(resultado))

    def test_campos_arbitrarios_e_segredos_nao_sao_copiados_para_o_plano(self) -> None:
        entrada = recomendacao(
            motivo="Bearer TOPSECRET123; token=TOPSECRET456; decisão observada",
            token="TOPSECRET789",
            payload={"corpo": "DADO-PRIVADO"},
            fonte_sinal="cliente-nao-confiavel",
        )
        resultado = self.executor.preparar(entrada)
        texto = json.dumps(resultado, ensure_ascii=False)
        self.assertNotIn("TOPSECRET123", texto)
        self.assertNotIn("TOPSECRET456", texto)
        self.assertNotIn("TOPSECRET789", texto)
        self.assertNotIn("DADO-PRIVADO", texto)
        self.assertNotIn("fonte_sinal", texto)
        self.assertIn("[redigido]", texto)
        self.assertFalse(resultado["efeito_executado"])

    def test_registros_em_memoria_tem_limite(self) -> None:
        executor = ExecutorDefesaGovernada(
            relogio=self.relogio,
            ttl_segundos=60,
            janela_idempotencia_segundos=60,
            max_registros=2,
        )
        for n in range(3):
            executor.preparar(recomendacao(motivo=f"motivo distinto {n}"))
        registros = executor.listar_registros(20)
        self.assertEqual(len(registros), 2)
        self.assertEqual(executor.contexto()["limite_registros"], 2)

    def test_chamadas_concorrentes_sao_idempotentes(self) -> None:
        with ThreadPoolExecutor(max_workers=10) as pool:
            resultados = list(pool.map(lambda _: self.executor.preparar(recomendacao()), range(10)))
        estados = [item["estado"] for item in resultados]
        self.assertEqual(estados.count("aguardando_aprovacao"), 1)
        self.assertEqual(estados.count("duplicado_idempotente"), 9)
        self.assertEqual(len(self.executor.listar_registros()), 1)

    def test_nao_ha_metodo_de_execucao_fisica(self) -> None:
        self.assertFalse(hasattr(self.executor, "executar"))
        self.assertFalse(hasattr(self.executor, "executar_operacao"))
        self.assertFalse(self.executor.contexto()["execucao_fisica_implementada"])

    def test_codigo_nao_invoca_executor_de_sistema_ou_rede(self) -> None:
        source = Path(__file__).with_name("nixal_executor_defesa_governada.py").read_text(encoding="utf-8")
        for proibido in ("subprocess.", "os.system(", "Popen(", "socket.", "urlopen(", "requests."):
            with self.subTest(proibido=proibido):
                self.assertNotIn(proibido, source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
