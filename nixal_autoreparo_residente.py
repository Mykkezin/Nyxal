#!/usr/bin/env python3
"""Autorreparo residente e limitado para serviços da Nyxal/NyxOS.

Só observa a API local e a sessão gráfica; pode reiniciar exclusivamente
nyxal-api.service e nyxos-interface.service. Nunca executa shell, altera
arquivos de código, instala pacotes, mexe no firewall ou modifica o kernel.
"""
from __future__ import annotations

import http.client
import json
import os
import socket
import subprocess
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


class AutoreparoResidenteNixOS:
    FONTE = "autoreparo_residente_nyxos"
    VERSAO = "1.0.0"

    FALHAS_ANTES_DO_REINICIO = 3
    MAX_REINICIOS_POR_JANELA = 3
    JANELA_REINICIOS_SEGUNDOS = 900
    COOLDOWN_REINICIO_SEGUNDOS = 90
    MAX_BYTES_AUDITORIA = 262_144

    UNIDADE_API = "nyxal-api.service"
    UNIDADE_INTERFACE = "nyxos-interface.service"
    ALVO_GRAFICO = "graphical-session.target"

    def __init__(
        self,
        *,
        health_checker: Callable[[], bool] | None = None,
        command_runner: Callable[..., Any] | None = None,
        clock: Callable[[], float] | None = None,
        arquivo_auditoria: str | Path | None = None,
        porta_api: int | None = None,
    ) -> None:
        self._health_checker = health_checker
        self._command_runner = command_runner or subprocess.run
        self._clock = clock or time.monotonic

        if porta_api is None:
            try:
                porta_api = int(os.environ.get("NYXAL_API_PORT", "8010"))
            except (TypeError, ValueError):
                porta_api = 8010
        if not isinstance(porta_api, int) or isinstance(porta_api, bool) or not 1 <= porta_api <= 65535:
            porta_api = 8010
        self.porta_api = porta_api

        if arquivo_auditoria is None:
            state_home = Path(
                os.environ.get(
                    "XDG_STATE_HOME",
                    str(Path.home() / ".local" / "state"),
                )
            ).expanduser()
            if not state_home.is_absolute():
                state_home = Path.home() / ".local" / "state"
            arquivo_auditoria = state_home / "nyxal" / "autoreparo-residente.jsonl"
        self.arquivo_auditoria = Path(arquivo_auditoria).expanduser()

        self._falhas = {"api": 0, "interface": 0}
        self._ultimas_tentativas: dict[str, float | None] = {
            "api": None,
            "interface": None,
        }
        self._reinicios: dict[str, deque[float]] = {
            "api": deque(),
            "interface": deque(),
        }

    def _rodar(self, argumentos: list[str]) -> Any:
        # Todas as chamadas são vetores constantes; nunca há shell ou comando do utilizador.
        return self._command_runner(
            argumentos,
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )

    def _unidade_ativa(self, unidade: str) -> bool:
        if unidade not in {
            self.UNIDADE_API,
            self.UNIDADE_INTERFACE,
            self.ALVO_GRAFICO,
        }:
            return False
        try:
            resultado = self._rodar(
                ["systemctl", "--user", "is-active", "--quiet", unidade]
            )
            return getattr(resultado, "returncode", 1) == 0
        except Exception:
            return False

    def _api_saudavel(self) -> bool:
        # O health-check só usa loopback, sem token, redirects ou tráfego externo.
        for host in ("127.0.0.1", "::1"):
            conexao: http.client.HTTPConnection | None = None
            try:
                conexao = http.client.HTTPConnection(
                    host,
                    self.porta_api,
                    timeout=2,
                )
                conexao.request(
                    "GET",
                    "/health",
                    headers={"Connection": "close"},
                )
                resposta = conexao.getresponse()
                if resposta.status == 200:
                    resposta.read(65_536)
                    return True
            except (OSError, socket.timeout, http.client.HTTPException):
                pass
            finally:
                if conexao is not None:
                    conexao.close()
        return False

    def _auditar(self, *, componente: str, estado: str, falhas: int, unidade: str | None) -> None:
        registro = {
            "em": datetime.now(timezone.utc).isoformat(),
            "fonte": self.FONTE,
            "versao": self.VERSAO,
            "componente": componente,
            "estado": estado,
            "falhas_consecutivas": falhas,
            "unidade": unidade,
            "autorizacao_explicita": False,
            "codigo_executado": False,
            "arquitetura_modificada": False,
        }
        caminho = self.arquivo_auditoria
        try:
            caminho.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            if caminho.parent.is_symlink() or caminho.is_symlink():
                return
            os.chmod(caminho.parent, 0o700)

            backup = Path(str(caminho) + ".1")
            if caminho.exists() and caminho.stat().st_size >= self.MAX_BYTES_AUDITORIA:
                if backup.is_symlink():
                    return
                if backup.exists():
                    backup.unlink()
                os.replace(caminho, backup)

            flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
            flags |= getattr(os, "O_NOFOLLOW", 0)
            descritor = os.open(caminho, flags, 0o600)
            try:
                os.fchmod(descritor, 0o600)
                with os.fdopen(descritor, "a", encoding="utf-8") as arquivo:
                    arquivo.write(json.dumps(registro, ensure_ascii=False, separators=(",", ":")) + "\n")
            except Exception:
                try:
                    os.close(descritor)
                except OSError:
                    pass
                raise
        except (OSError, ValueError, TypeError):
            # A falha do arquivo de auditoria nunca pode derrubar a residência.
            return

    def _tentar_reinicio(self, *, componente: str, unidade: str, falhas: int) -> dict[str, Any]:
        if falhas < self.FALHAS_ANTES_DO_REINICIO:
            return {
                "estado": "confirmando_falha",
                "reinicio_solicitado": False,
                "unidade": unidade,
            }

        agora = self._clock()
        tentativas = self._reinicios[componente]
        while tentativas and agora - tentativas[0] >= self.JANELA_REINICIOS_SEGUNDOS:
            tentativas.popleft()

        if len(tentativas) >= self.MAX_REINICIOS_POR_JANELA:
            estado = "circuito_aberto_limite_reinicios"
            self._auditar(componente=componente, estado=estado, falhas=falhas, unidade=unidade)
            return {
                "estado": estado,
                "reinicio_solicitado": False,
                "unidade": unidade,
                "tentativas_na_janela": len(tentativas),
            }

        ultima = self._ultimas_tentativas[componente]
        if ultima is not None and agora - ultima < self.COOLDOWN_REINICIO_SEGUNDOS:
            return {
                "estado": "aguardando_cooldown",
                "reinicio_solicitado": False,
                "unidade": unidade,
                "cooldown_restante_segundos": max(
                    0,
                    int(self.COOLDOWN_REINICIO_SEGUNDOS - (agora - ultima)),
                ),
            }

        # Registra a tentativa mesmo se o systemctl falhar, impedindo repetição agressiva.
        tentativas.append(agora)
        self._ultimas_tentativas[componente] = agora
        try:
            resultado = self._rodar(
                ["systemctl", "--user", "restart", unidade]
            )
            codigo = getattr(resultado, "returncode", 1)
        except Exception:
            codigo = 1

        estado = "reinicio_solicitado" if codigo == 0 else "reinicio_falhou"
        self._auditar(componente=componente, estado=estado, falhas=falhas, unidade=unidade)
        return {
            "estado": estado,
            "reinicio_solicitado": codigo == 0,
            "unidade": unidade,
            "codigo_retorno": codigo,
            "tentativas_na_janela": len(tentativas),
        }

    def verificar_e_reparar(self) -> dict[str, Any]:
        """Executa uma verificação rápida; não espera pelo serviço reiniciado."""
        try:
            api_ok = (
                bool(self._health_checker())
                if self._health_checker is not None
                else self._api_saudavel()
            )
        except Exception:
            api_ok = False

        if api_ok:
            self._falhas["api"] = 0
            api_estado = {
                "estado": "saudavel",
                "falhas_consecutivas": 0,
                "reparo": {
                    "estado": "nao_necessario",
                    "reinicio_solicitado": False,
                    "unidade": self.UNIDADE_API,
                },
            }
        else:
            self._falhas["api"] += 1
            reparo = self._tentar_reinicio(
                componente="api",
                unidade=self.UNIDADE_API,
                falhas=self._falhas["api"],
            )
            api_estado = {
                "estado": "indisponivel",
                "falhas_consecutivas": self._falhas["api"],
                "reparo": reparo,
            }
            if self._falhas["api"] in {1, self.FALHAS_ANTES_DO_REINICIO}:
                self._auditar(
                    componente="api",
                    estado="healthcheck_falhou",
                    falhas=self._falhas["api"],
                    unidade=self.UNIDADE_API,
                )

        if not self._unidade_ativa(self.ALVO_GRAFICO):
            self._falhas["interface"] = 0
            interface_estado = {
                "estado": "aguardando_sessao_grafica",
                "falhas_consecutivas": 0,
                "reparo": {
                    "estado": "adiado_sem_sessao_grafica",
                    "reinicio_solicitado": False,
                    "unidade": self.UNIDADE_INTERFACE,
                },
            }
        elif self._unidade_ativa(self.UNIDADE_INTERFACE):
            self._falhas["interface"] = 0
            interface_estado = {
                "estado": "ativa",
                "falhas_consecutivas": 0,
                "reparo": {
                    "estado": "nao_necessario",
                    "reinicio_solicitado": False,
                    "unidade": self.UNIDADE_INTERFACE,
                },
            }
        else:
            self._falhas["interface"] += 1
            reparo_interface = self._tentar_reinicio(
                componente="interface",
                unidade=self.UNIDADE_INTERFACE,
                falhas=self._falhas["interface"],
            )
            interface_estado = {
                "estado": "inativa",
                "falhas_consecutivas": self._falhas["interface"],
                "reparo": reparo_interface,
            }
            if self._falhas["interface"] in {1, self.FALHAS_ANTES_DO_REINICIO}:
                self._auditar(
                    componente="interface",
                    estado="unidade_interface_inativa",
                    falhas=self._falhas["interface"],
                    unidade=self.UNIDADE_INTERFACE,
                )

        grafico_ok = interface_estado["estado"] in {
            "ativa",
            "aguardando_sessao_grafica",
        }
        reparo_solicitado = any(
            comp["reparo"].get("reinicio_solicitado") is True
            for comp in (api_estado, interface_estado)
        )
        if api_ok and grafico_ok:
            geral = "saudavel"
        elif reparo_solicitado:
            geral = "reparo_solicitado"
        else:
            geral = "degradado"

        return {
            "sucesso": api_ok and grafico_ok,
            "estado": geral,
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "api": api_estado,
            "interface": interface_estado,
            "unidades_permitidas": [
                self.UNIDADE_API,
                self.UNIDADE_INTERFACE,
            ],
            "limites": {
                "falhas_antes_do_reinicio": self.FALHAS_ANTES_DO_REINICIO,
                "max_reinicios_por_janela": self.MAX_REINICIOS_POR_JANELA,
                "janela_reinicios_segundos": self.JANELA_REINICIOS_SEGUNDOS,
                "cooldown_reinicio_segundos": self.COOLDOWN_REINICIO_SEGUNDOS,
            },
            "autorizacao_explicita": False,
            "codigo_executado": False,
            "integracao_executada": False,
            "stable_modificada": False,
            "arquitetura_modificada": False,
        }

    def contexto(self) -> dict[str, Any]:
        return {
            "sucesso": True,
            "estado": "autoreparo_disponivel",
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "unidades_permitidas": [
                self.UNIDADE_API,
                self.UNIDADE_INTERFACE,
            ],
            "checks": ["GET /health em loopback", "estado de graphical-session.target"],
            "autorizacao_explicita": False,
            "codigo_executado": False,
            "arquitetura_modificada": False,
        }


if __name__ == "__main__":
    reparo = AutoreparoResidenteNixOS()
    print(json.dumps(reparo.verificar_e_reparar(), ensure_ascii=False, indent=2))
