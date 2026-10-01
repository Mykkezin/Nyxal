#!/usr/bin/env python3

from __future__ import annotations

import json
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory


TESTES = 0
FALHAS = 0


def verificar(condicao: bool, mensagem: str) -> None:
    global TESTES, FALHAS
    TESTES += 1

    if not condicao:
        FALHAS += 1
        print(f"FALHA: {mensagem}")


def main() -> None:
    base = Path(__file__).resolve().parent
    runtime = base / "nixal_runtime.py"
    estado = base / "estado_nyxal_runtime.json"
    log = base / "log_nyxal_runtime.json"

    verificar(runtime.exists(), "Runtime existe")
    verificar(runtime.is_file(), "Runtime é arquivo")

    with TemporaryDirectory() as temporario:
        backup = Path(temporario)

        estado_backup = backup / "estado_nyxal_runtime.json"
        log_backup = backup / "log_nyxal_runtime.json"

        estado_existia = estado.exists()
        log_existia = log.exists()

        if estado_existia:
            shutil.copy2(estado, estado_backup)

        if log_existia:
            shutil.copy2(log, log_backup)

        processo = None

        try:
            if estado.exists():
                estado.unlink()

            if log.exists():
                log.unlink()

            processo = subprocess.Popen(
                [sys.executable, str(runtime)],
                cwd=base,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )

            time.sleep(5.0)

            verificar(
                processo.poll() is None,
                "Runtime permaneceu ativo sem mensagem humana",
            )

            processo.send_signal(signal.SIGINT)

            try:
                saida, _ = processo.communicate(timeout=5.0)
            except subprocess.TimeoutExpired:
                processo.kill()
                saida, _ = processo.communicate()
                verificar(
                    False,
                    "Runtime encerrou dentro do tempo esperado",
                )

            verificar(
                processo.returncode == 0,
                "Runtime terminou normalmente após interrupção controlada",
            )

            verificar(
                "NYXAL RUNTIME — MODO PERSISTENTE" in saida,
                "modo persistente foi iniciado",
            )

            verificar(
                "NYXAL RUNTIME — EXECUÇÃO INTERROMPIDA." in saida,
                "interrupção controlada foi registrada",
            )

            verificar(
                log.exists(),
                "log foi criado durante a inicialização",
            )

            verificar(
                estado.exists(),
                "estado foi criado durante a inicialização",
            )

            if log.exists():
                dados = json.loads(
                    log.read_text(encoding="utf-8")
                )

                verificar(
                    isinstance(dados, list),
                    "log produzido é uma lista JSON",
                )

                verificar(
                    len(dados) >= 2,
                    "pelo menos dois ciclos foram executados",
                )

                if isinstance(dados, list) and dados:
                    ciclos = dados[-2:]

                    verificar(
                        all(
                            ciclo.get("sucesso") is True
                            for ciclo in ciclos
                        ),
                        "ciclos iniciados sem mensagem concluíram com sucesso",
                    )

                    verificar(
                        all(
                            ciclo.get("estado") == "ciclo_concluido"
                            for ciclo in ciclos
                        ),
                        "ciclos iniciados sem mensagem foram concluídos",
                    )

                    verificar(
                        all(
                            ciclo.get("valor", {})
                            .get("avaliacao", {})
                            .get("avaliacao")
                            == "sucesso"
                            for ciclo in ciclos
                        ),
                        "ciclos persistentes foram avaliados como sucesso",
                    )

                    verificar(
                        all(
                            ciclo.get("valor", {})
                            .get("experiencia", {})
                            .get("estado")
                            == "experiencia_registrada"
                            for ciclo in ciclos
                        ),
                        "ciclos persistentes registraram experiência",
                    )

        finally:
            if processo is not None and processo.poll() is None:
                processo.kill()
                processo.wait()

            if estado.exists():
                estado.unlink()

            if log.exists():
                log.unlink()

            if estado_existia:
                shutil.copy2(estado_backup, estado)

            if log_existia:
                shutil.copy2(log_backup, log)

    print("=" * 60)
    print("TESTE — NYXAL RUNTIME INICIALIZAÇÃO SEM MENSAGEM")
    print("=" * 60)
    print(f"TESTES EXECUTADOS: {TESTES}")
    print(f"FALHAS: {FALHAS}")
    print(f"PASSOU: {FALHAS == 0}")
    print("=" * 60)

    raise SystemExit(0 if FALHAS == 0 else 1)


if __name__ == "__main__":
    main()
