#!/usr/bin/env python3
"""Validação estrutural do M5.9 — residência Linux via systemd do usuário."""

from __future__ import annotations

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
SYSTEMD_DIR = BASE_DIR / "deploy" / "systemd"


def ler(nome: str) -> str:
    caminho = SYSTEMD_DIR / nome
    assert caminho.is_file(), f"arquivo ausente: {nome}"
    return caminho.read_text(encoding="utf-8")


def main() -> None:
    api = ler("nyxal-api.service")
    residente = ler("nyxos-residente.service")
    target = ler("nyxos.target")
    instalador = ler("instalar_nyxos_servicos.sh")
    desinstalador = ler("desinstalar_nyxos_servicos.sh")

    for unidade in (api, residente):
        assert "Type=simple" in unidade
        assert "WorkingDirectory=%h/Nyxal" in unidade
        assert "EnvironmentFile=-%h/.config/nyxal/nyxal.env" in unidade
        assert "Restart=on-failure" in unidade
        assert "RestartSec=3" in unidade
        assert "NoNewPrivileges=true" in unidade
        assert "PrivateTmp=true" in unidade
        assert "UMask=0077" in unidade
        assert "ProtectSystem=full" in unidade
        assert "ProtectKernelTunables=true" in unidade
        assert "ProtectKernelModules=true" in unidade
        assert "ProtectControlGroups=true" in unidade
        assert "RestrictSUIDSGID=true" in unidade
        assert "LockPersonality=true" in unidade
        assert "RestrictRealtime=true" in unidade
        assert "SystemCallArchitectures=native" in unidade
        assert "%h/Nyxal/.venv/bin/python" in unidade
        assert "/usr/bin/python3" not in unidade
        assert "--habilitar-auto-experimento" not in unidade

    assert (
        "ExecStart=%h/Nyxal/.venv/bin/python %h/Nyxal/nyxal_web_api.py"
        in api
    )
    assert (
        "ExecStart=%h/Nyxal/.venv/bin/python "
        "%h/Nyxal/executar_nyxos_residente.py --intervalo 5"
        in residente
    )

    assert "Wants=nyxal-api.service nyxos-residente.service" in target
    assert "WantedBy=default.target" in target

    assert "systemctl --user daemon-reload" in instalador
    assert "systemctl --user enable --now nyxos.target" in instalador
    assert 'PYTHON_BIN="${NYXAL_DIR}/.venv/bin/python"' in instalador
    assert '[[ ! -x "${PYTHON_BIN}" ]]' in instalador
    assert 'import nyxal_web_api; import executar_nyxos_residente' in instalador
    assert 'chmod 700 "${CONFIG_DIR}"' in instalador
    assert 'ENV_FILE="${CONFIG_DIR}/nyxal.env"' in instalador
    assert '[[ -L "${ENV_FILE}" ]]' in instalador
    assert 'chmod 600 "${ENV_FILE}"' in instalador
    assert "loginctl enable-linger ${USER}" in instalador
    assert "LINGER_STATUS" in instalador
    assert "sudo " not in instalador
    assert "/etc/systemd" not in instalador
    assert "senha" not in instalador.lower()
    assert "token" not in instalador.lower()

    assert "systemctl --user disable --now nyxos.target" in desinstalador
    assert "rm -f" in desinstalador
    assert "main" not in desinstalador.lower()

    testar_historico_residente_limitado()

    launcher = (BASE_DIR / "executar_nyxos_residente.py").read_text(
        encoding="utf-8"
    )
    assert "modo_residente=True" in launcher

    runtime = (BASE_DIR / "nixal_runtime.py").read_text(
        encoding="utf-8"
    )
    assert "modo_residente: bool = False" in runtime
    assert "investigacao_profunda_adiada_no_perfil_residente" in runtime
    assert "log_nyxal_residente.json" in runtime

    print("TESTE_M5_9_RESIDENCIA_LINUX_OK")
    print("TESTE_MEMORIA_RESIDENTE_LIMITADA_OK")
    print("PYTHON: .venv/bin/python")
    print("SERVICOS: 2")
    print("TARGET: nyxos.target")
    print("AE2_AUTOMATICA: DESABILITADA")

def testar_historico_residente_limitado() -> None:
    from nixal_ciclo_residente import CicloResidenteNixOS

    class RuntimeFalso:
        def __init__(self) -> None:
            self.ciclos = 0
            self.residente = None

        def executar_ciclo(self) -> dict:
            self.ciclos += 1
            if self.ciclos >= 20 and self.residente is not None:
                self.residente.parar()
            return {
                "sucesso": True,
                "estado": "ciclo_concluido",
                "ciclo": self.ciclos,
            }

    runtime = RuntimeFalso()
    residente = CicloResidenteNixOS(
        runtime,
        intervalo_segundos=0,
    )
    runtime.residente = residente

    resultados = residente.executar()

    assert runtime.ciclos == 20
    assert len(resultados) == 1
    assert resultados[0]["ciclo"] == 20
    assert residente.contexto()["ciclos_executados"] == 20


if __name__ == "__main__":
    main()
