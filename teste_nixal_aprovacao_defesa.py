#!/usr/bin/env python3
"""Testes do diário durável de aprovações da defesa governada (issue #103).

Cobre procedência confiável, vínculo ao escopo do plano, replay, revogação,
expiração, concorrência entre processos, recuperação após reinício, falha de
armazenamento, saturação e trilha corrompida — sempre com efeito real negado.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import tempfile
import unittest
from pathlib import Path

from nixal_aprovacao_defesa import DiarioAprovacaoDefesa, _hash_escopo
from nixal_executor_defesa_governada import ExecutorDefesaGovernada

PRINCIPAL = {
    "autenticado": True,
    "procedencia": "http_autenticado",
    "identidade": "operadora-teste",
}
PLANO = {
    "tipo": "bloqueio_temporario_origem",
    "escopo": "203.0.113.7",
    "duracao_segundos": 120,
    "motivo": "tentativas repetidas de autenticacao a partir desta origem",
}

PROGRAMA_FILHO = """
import json
import sys
from pathlib import Path

sys.path.insert(0, {base!r})
from nixal_aprovacao_defesa import DiarioAprovacaoDefesa, _hash_escopo

diario = DiarioAprovacaoDefesa(Path({caminho!r}))
acao = sys.argv[1]
if acao == "registrar":
    resultado = diario.registrar(
        principal=json.loads(sys.argv[2]), plano=json.loads(sys.argv[3]), ttl_segundos=300
    )
    print(json.dumps(resultado, ensure_ascii=False))
elif acao == "verificar":
    candidato = {{"aprovacao_id": sys.argv[2], "escopo_hash": sys.argv[3]}}
    print(json.dumps({{"concedida": diario.verificar(candidato)}}))
else:
    print(diario.contexto()["aprovacoes_ativas"])
"""


class DiarioAprovacaoDefesaTestes(unittest.TestCase):
    def setUp(self) -> None:
        self.temporario = tempfile.mkdtemp(prefix="nyxal-aprovacao-")
        self.addCleanup(shutil.rmtree, self.temporario, True)
        self.caminho = Path(self.temporario) / "aprovacoes.jsonl"
        # Relógio controlável, mas ancorado no tempo real: os filhos em
        # subprocesso usam time.time() e uma âncora do passado faria toda
        # aprovação nascer expirada.
        self.relogio_valor = [time.time()]
        self.diario = DiarioAprovacaoDefesa(
            self.caminho, relogio=lambda: self.relogio_valor[0]
        )

    def registrar(self, principal=PRINCIPAL, plano=PLANO, ttl=300):
        resultado = self.diario.registrar(
            principal=principal, plano=plano, ttl_segundos=ttl
        )
        self.assertTrue(resultado["sucesso"], resultado)
        return resultado["aprovacao_id"], _hash_escopo(plano)

    # ------------------------------------------------------------------
    # procedência confiável
    # ------------------------------------------------------------------

    def test_o_cliente_nao_consegue_registrar_a_propria_aprovacao(self) -> None:
        recusadas = [
            {"autenticado": False, "procedencia": "http_autenticado", "identidade": "x"},
            {"autenticado": True, "procedencia": "auto_declarada", "identidade": "x"},
            {"autenticado": True, "procedencia": "http_autenticado", "identidade": "   "},
            {"autenticado": True, "procedencia": "http_autenticado"},
            {"autenticado": True, "procedencia": "cli_local_confirmado",
             "identidade": "x", "auto_declarada": True},
            "sim",
            None,
        ]
        for principal in recusadas:
            resultado = self.diario.registrar(principal=principal, plano=PLANO)
            self.assertFalse(resultado["sucesso"], principal)
            self.assertFalse(resultado["efeito_executado"])
        self.assertEqual(self.diario.contexto()["aprovacoes_registradas"], 0)

    def test_aprovacao_forjada_nao_existe_no_diario_e_e_negada(self) -> None:
        self.assertFalse(
            self.diario.verificar(
                {"aprovacao_id": "apr-" + "0" * 24, "escopo_hash": _hash_escopo(PLANO)}
            )
        )
        for id_invalido in ("", "a" * 65, "apr com espaco", "apr/../x", 1, None, True):
            self.assertFalse(
                self.diario.verificar({"aprovacao_id": id_invalido, "escopo_hash": _hash_escopo(PLANO)})
            )
        # hash de escopo fora do formato também nega, sem levantar exceção.
        self.assertFalse(
            self.diario.verificar({"aprovacao_id": "apr-" + "0" * 24, "escopo_hash": "zz"})
        )

    # ------------------------------------------------------------------
    # vínculo ao escopo e replay
    # ------------------------------------------------------------------

    def test_aprovacao_obrigatoriamente_vincula_o_escopo_do_plano(self) -> None:
        aprovacao_id, _ = self.registrar()
        outro = {"tipo": "isolar_servico", "escopo": "nyxal-api", "duracao_segundos": None}
        self.assertFalse(
            self.diario.verificar({"aprovacao_id": aprovacao_id, "escopo_hash": _hash_escopo(outro)})
        )
        # negada por escopo, a aprovação continua ativa e utilizável.
        self.assertTrue(
            self.diario.verificar({"aprovacao_id": aprovacao_id, "escopo_hash": _hash_escopo(PLANO)})
        )

    def test_aprovacao_e_de_uso_unico(self) -> None:
        aprovacao_id, escopo = self.registrar()
        self.assertTrue(self.diario.verificar({"aprovacao_id": aprovacao_id, "escopo_hash": escopo}))
        self.assertFalse(self.diario.verificar({"aprovacao_id": aprovacao_id, "escopo_hash": escopo}))
        self.assertFalse(self.diario.verificar({"aprovacao_id": aprovacao_id, "escopo_hash": escopo}))
        tipos = [
            json.loads(linha)["tipo"]
            for linha in self.caminho.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(tipos, ["aprovacao_registrada", "aprovacao_consumida"])

    def test_revogacao_impede_o_uso_da_aprovacao(self) -> None:
        aprovacao_id, escopo = self.registrar()
        self.assertFalse(self.diario.revogar(aprovacao_id, principal={"autenticado": False}).get("sucesso", False))
        self.assertTrue(self.diario.revogar(aprovacao_id, principal=PRINCIPAL)["sucesso"])
        self.assertFalse(self.diario.verificar({"aprovacao_id": aprovacao_id, "escopo_hash": escopo}))
        self.assertFalse(self.diario.revogar(aprovacao_id, principal=PRINCIPAL)["sucesso"])

    def test_aprovacao_expirada_e_negada(self) -> None:
        aprovacao_id, escopo = self.registrar()
        self.relogio_valor[0] += 301
        self.assertFalse(self.diario.verificar({"aprovacao_id": aprovacao_id, "escopo_hash": escopo}))
        # o prazo não consome a aprovação: voltar no tempo não a revalida como
        # usada, mas ela também não pode ser concedida depois de expirada.
        self.relogio_valor[0] -= 1
        self.assertFalse(self.diario.verificar({"aprovacao_id": aprovacao_id, "escopo_hash": escopo}))

    # ------------------------------------------------------------------
    # durabilidade, concorrência e recuperação
    # ------------------------------------------------------------------

    def _filho(self, args: list[str]) -> str:
        script = Path(self.temporario) / "filho.py"
        script.write_text(
            PROGRAMA_FILHO.format(base=str(Path(__file__).resolve().parent), caminho=str(self.caminho)),
            encoding="utf-8",
        )
        resultado = subprocess.run(
            [sys.executable, str(script), *args], capture_output=True, text=True, timeout=60
        )
        self.assertEqual(resultado.returncode, 0, resultado.stderr[-400:])
        return resultado.stdout.strip()

    def test_reinicio_de_processo_recupera_a_aprovacao_sem_repetir_o_uso(self) -> None:
        saida = self._filho(["registrar", json.dumps(PRINCIPAL), json.dumps(PLANO)])
        registro = json.loads(saida.splitlines()[-1])
        self.assertTrue(registro["sucesso"])
        escopo = _hash_escopo(PLANO)

        revived = DiarioAprovacaoDefesa(self.caminho)
        self.assertEqual(revived.contexto()["aprovacoes_ativas"], 1)
        self.assertTrue(revived.verificar({"aprovacao_id": registro["aprovacao_id"], "escopo_hash": escopo}))
        self.assertFalse(revived.verificar({"aprovacao_id": registro["aprovacao_id"], "escopo_hash": escopo}))
        # e um processo novo, depois do consumo, também nega o replay
        self.assertEqual(
            json.loads(self._filho(["verificar", registro["aprovacao_id"], escopo]))["concedida"], False
        )

    def test_dois_processos_consomem_a_mesma_aprovacao_uma_unica_vez(self) -> None:
        script = Path(self.temporario) / "filho.py"
        script.write_text(
            PROGRAMA_FILHO.format(base=str(Path(__file__).resolve().parent), caminho=str(self.caminho)),
            encoding="utf-8",
        )
        aprovacao_id, escopo = self.registrar()
        processos = [
            subprocess.Popen(
                [sys.executable, str(script), "verificar", aprovacao_id, escopo],
                stdout=subprocess.PIPE, text=True,
            )
            for _ in range(4)
        ]
        saidas = [p.communicate(timeout=60)[0].strip().splitlines()[-1] for p in processos]
        concedidas = [json.loads(s)["concedida"] for s in saidas]
        self.assertEqual(concedidas.count(True), 1, concedidas)
        self.assertEqual(
            [
                json.loads(linha)["tipo"]
                for linha in self.caminho.read_text(encoding="utf-8").splitlines()
            ].count("aprovacao_consumida"),
            1,
        )

    # ------------------------------------------------------------------
    # armazenamento
    # ------------------------------------------------------------------

    def test_permissoes_publicas_sao_recusadas_sem_reescrever_o_arquivo(self) -> None:
        self.registrar()
        os.chmod(self.caminho, 0o644)
        diario = DiarioAprovacaoDefesa(self.caminho)
        antes = self.caminho.read_bytes()
        self.assertFalse(diario.verificar({"aprovacao_id": "apr-" + "0" * 24, "escopo_hash": _hash_escopo(PLANO)}))
        self.assertFalse(diario.registrar(principal=PRINCIPAL, plano=PLANO)["sucesso"])
        self.assertEqual(self.caminho.read_bytes(), antes)
        os.chmod(self.caminho, 0o600)
        os.chmod(self.caminho.parent, 0o755)
        self.assertFalse(DiarioAprovacaoDefesa(self.caminho).contexto()["diario_disponivel"])

    def test_diretorio_de_escrita_bloqueado_deixa_a_aprovacao_nao_consumida(self) -> None:
        aprovacao_id, escopo = self.registrar()
        bytes_antes = self.caminho.read_bytes()
        os.chmod(self.caminho, 0o400)
        diario = DiarioAprovacaoDefesa(self.caminho)
        self.assertFalse(diario.verificar({"aprovacao_id": aprovacao_id, "escopo_hash": escopo}))
        self.assertEqual(self.caminho.read_bytes(), bytes_antes)
        os.chmod(self.caminho, 0o600)
        # recuperado o acesso, a mesma aprovação ainda pode ser concedida uma vez
        diario2 = DiarioAprovacaoDefesa(self.caminho)
        self.assertTrue(diario2.verificar({"aprovacao_id": aprovacao_id, "escopo_hash": escopo}))
        self.assertFalse(diario2.verificar({"aprovacao_id": aprovacao_id, "escopo_hash": escopo}))

    def test_linha_adulterada_corrompe_a_cadeia_e_todo_o_resto_e_negado(self) -> None:
        aprovacao_id, escopo = self.registrar()
        linhas = self.caminho.read_text(encoding="utf-8").splitlines()
        registro = json.loads(linhas[0])
        registro["valor"]["aprovador"] = "outra-identidade"
        self.caminho.write_text(
            json.dumps(registro, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        diario = DiarioAprovacaoDefesa(self.caminho)
        contexto = diario.contexto()
        self.assertTrue(contexto["trilha_corrompida"])
        self.assertFalse(contexto["diario_disponivel"])
        self.assertEqual(contexto["aprovacoes_registradas"], 0)
        self.assertFalse(diario.verificar({"aprovacao_id": aprovacao_id, "escopo_hash": escopo}))
        self.assertFalse(diario.registrar(principal=PRINCIPAL, plano=PLANO)["sucesso"])

    def test_diario_saturado_recusa_novas_aprovacoes(self) -> None:
        diario = DiarioAprovacaoDefesa(self.caminho, max_registros=2)
        primeiro = diario.registrar(principal=PRINCIPAL, plano=PLANO)
        self.assertTrue(primeiro["sucesso"])
        segundo = diario.registrar(principal=PRINCIPAL, plano={"tipo": "isolar_servico", "escopo": "nyxal-api"})
        self.assertTrue(segundo["sucesso"])
        terceiro = diario.registrar(principal=PRINCIPAL, plano=PLANO)
        self.assertFalse(terceiro["sucesso"])
        self.assertEqual(terceiro["motivo"], "diario_saturado")

    def test_contexto_nao_expoe_caminho_nem_identidades(self) -> None:
        self.registrar()
        DiarioAprovacaoDefesa(self.caminho).contexto()
        texto = json.dumps(self.diario.contexto(), ensure_ascii=False)
        self.assertNotIn(str(self.caminho), texto)
        self.assertNotIn("operadora-teste", texto)
        self.assertNotIn(self.temporario, texto)

    # ------------------------------------------------------------------
    # integração com o gate dry-run
    # ------------------------------------------------------------------

    def test_gate_dry_run_so_sobe_de_estado_com_aprovacao_real(self) -> None:
        diario = DiarioAprovacaoDefesa(self.caminho)
        executor = ExecutorDefesaGovernada(verificador_aprovacao=diario.para_executor())

        forjada = executor.preparar(
            dict(PLANO),
            aprovacao={"aprovacao_id": "apr-" + "1" * 24, "escopo_hash": _hash_escopo(PLANO)},
        )
        self.assertEqual(forjada["estado"], "aguardando_aprovacao")
        self.assertFalse(forjada["executor_ativo"])
        self.assertFalse(forjada["executor_autorizado"])
        self.assertFalse(forjada["efeito_executado"])
        self.assertEqual(diario.contexto()["aprovacoes_registradas"], 0)

    def test_aprovacao_registrada_move_a_simulacao_sem_nunca_executar(self) -> None:
        diario = DiarioAprovacaoDefesa(self.caminho)
        executor = ExecutorDefesaGovernada(verificador_aprovacao=diario.para_executor())
        registro = diario.registrar(principal=PRINCIPAL, plano=PLANO, ttl_segundos=300)
        self.assertTrue(registro["sucesso"])
        candidato = {"aprovacao_id": registro["aprovacao_id"], "escopo_hash": _hash_escopo(PLANO)}

        preparado = executor.preparar(dict(PLANO), aprovacao=candidato)
        self.assertEqual(preparado["estado"], "simulacao_preparada")
        self.assertTrue(preparado["plano"]["aprovacao_verificada"])
        self.assertFalse(preparado["executor_ativo"])
        self.assertFalse(preparado["executor_autorizado"])
        self.assertFalse(preparado["efeito_executado"])
        self.assertEqual(executor.contexto()["executor_ativo"], False)
        self.assertEqual(executor.contexto()["execucao_fisica_implementada"], False)

        # replay: a segunda tentativa com a mesma aprovação não reabre nada.
        segundo = executor.preparar(dict(PLANO), aprovacao=candidato)
        self.assertIn(segundo["estado"], {"simulacao_preparada", "duplicado_idempotente", "aguardando_aprovacao"})
        self.assertFalse(segundo["executor_autorizado"])
        self.assertFalse(segundo["efeito_executado"])


class IntegracaoNaApiTestes(unittest.TestCase):
    """Deriva de instalação: o gate só é governado se a API injetar o diário."""

    def test_api_injeta_o_verificador_duravel_no_gate(self) -> None:
        fonte = Path(
            __file__
        ).resolve().parent.joinpath("nyxal_web_api.py").read_text(encoding="utf-8")
        self.assertIn("from nixal_aprovacao_defesa import DiarioAprovacaoDefesa", fonte)
        self.assertIn("DEFESA_DIARIO_APROVACOES = DiarioAprovacaoDefesa.do_ambiente()", fonte)
        self.assertIn(
            "verificador_aprovacao=DEFESA_DIARIO_APROVACOES.para_executor()", fonte
        )
        # Um gate construído sem verificador aceitaria apenas a ausência de
        # aprovação; reconstruí-lo sem a injeção reabriria o buraco da issue.
        self.assertNotIn("DEFESA_EXECUTOR_GOVERNADO = ExecutorDefesaGovernada()", fonte)
        self.assertIn('"aprovacoes": DEFESA_DIARIO_APROVACOES.contexto()', fonte)


if __name__ == "__main__":
    unittest.main(verbosity=2)
