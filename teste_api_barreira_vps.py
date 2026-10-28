#!/usr/bin/env python3
"""Regressões da barreira de impacto real sobre VMs na API local.

Cobre a topologia realmente instalada: loopback direto, sem proxy reverso e
sem Bearer. Nesse arranjo a confiança de loopback é suficiente para ligar ou
desligar a máquina, mas não pode autorizar uma ação irreversível.

O teste usa porta efêmera, sem tocar na API residente nem em estado operacional.
"""

from __future__ import annotations

import http.client
import json
import threading
import unittest
from unittest.mock import patch

import nyxal_web_api as api


class TesteBarreiraVpsIrreversivel(unittest.TestCase):
    def setUp(self) -> None:
        self.proxy_original = api.PROXY_MODE
        self.token_original = api.API_TOKEN
        self.cors_original = api.CORS_ORIGINS
        self.habilitado_original = api.VPS_ACACOES_IRREVERSIVEIS_HABILITADAS
        api.PROXY_MODE = False
        api.API_TOKEN = "segredo-de-teste"
        api.CORS_ORIGINS = api.parse_allowed_origins("")
        self.server = api.NyxalThreadingHTTPServer(("127.0.0.1", 0), api.NyxalAPIHandler)
        self.server.request_slots = api.BoundedSemaphore(api.MAX_CONCURRENT_HTTP_REQUESTS)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.host, self.port = self.server.server_address
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

        def restaurar() -> None:
            api.PROXY_MODE = self.proxy_original
            api.API_TOKEN = self.token_original
            api.CORS_ORIGINS = self.cors_original
            api.VPS_ACACOES_IRREVERSIVEIS_HABILITADAS = self.habilitado_original

        self.addCleanup(restaurar)

    def pos(self, corpo: dict, *, token: str | None = None) -> tuple[int, dict]:
        bruto = json.dumps(corpo).encode("utf-8")
        cabecalhos = {"Content-Type": "application/json", "Content-Length": str(len(bruto))}
        if token is not None:
            cabecalhos["Authorization"] = f"Bearer {token}"
        conexao = http.client.HTTPConnection(self.host, self.port, timeout=3)
        try:
            conexao.request("POST", "/api/vps/action", body=bruto, headers=cabecalhos)
            resposta = conexao.getresponse()
            texto = resposta.read().decode("utf-8", errors="replace")
            try:
                return resposta.status, json.loads(texto)
            except json.JSONDecodeError:
                return resposta.status, {"_bruto": texto}
        finally:
            conexao.close()

    def test_acao_irreversivel_negada_por_padrao_sem_habilitacao(self) -> None:
        api.VPS_ACACOES_IRREVERSIVEIS_HABILITADAS = False
        with patch.object(api.VPS_NYXOS, "action") as action:
            status, corpo = self.pos({"nome": "delta", "acao": "destroy"})
        self.assertEqual(status, 423)
        self.assertEqual(corpo.get("estado"), "acao_nao_habilitada")
        action.assert_not_called()

    def test_acao_irreversivel_habilitada_exige_bearer_mesmo_em_loopback(self) -> None:
        api.VPS_ACACOES_IRREVERSIVEIS_HABILITADAS = True
        with patch.object(api.VPS_NYXOS, "action") as action:
            status, corpo = self.pos({"nome": "delta", "acao": "destroy"})
        self.assertIn(status, (401, 403))
        action.assert_not_called()
        self.assertNotIn("segredo-de-teste", json.dumps(corpo))

    def test_acao_irreversivel_executa_com_bearer_correto(self) -> None:
        api.VPS_ACACOES_IRREVERSIVEIS_HABILITADAS = True
        with patch.object(
            api.VPS_NYXOS, "action", return_value={"sucesso": True, "estado": "acao_executada"}
        ) as action:
            status, corpo = self.pos(
                {"nome": "delta", "acao": "destroy"}, token="segredo-de-teste"
            )
        action.assert_called_once_with(nome="delta", acao="destroy")
        self.assertEqual(status, 200)
        self.assertEqual(corpo.get("estado"), "acao_executada")

    def test_ciclo_reversivel_do_painel_continua_sem_token(self) -> None:
        """ON/OFF/REBOOT do painel local dependem da confiança de loopback."""
        api.VPS_ACACOES_IRREVERSIVEIS_HABILITADAS = False
        for acao in ("start", "shutdown", "reboot"):
            with self.subTest(acao=acao):
                with patch.object(
                    api.VPS_NYXOS, "action", return_value={"sucesso": True, "estado": "acao_executada"}
                ) as action:
                    status, _corpo = self.pos({"nome": "delta", "acao": acao})
                action.assert_called_once_with(nome="delta", acao=acao)
                self.assertEqual(status, 200)

    def test_autostart_off_tambem_e_irreversivel(self) -> None:
        api.VPS_ACACOES_IRREVERSIVEIS_HABILITADAS = False
        with patch.object(api.VPS_NYXOS, "action") as action:
            status, _corpo = self.pos({"nome": "delta", "acao": "autostart_off"})
        self.assertEqual(status, 423)
        action.assert_not_called()


if __name__ == "__main__":
    unittest.main()
