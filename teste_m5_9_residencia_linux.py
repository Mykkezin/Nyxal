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
    diagnostico = ler("diagnosticar_nyxos_local.sh")
    shell_principal = ler("iniciar_nyxos_shell.sh")
    autoreparo = (BASE_DIR / "nixal_autoreparo_residente.py").read_text(encoding="utf-8")

    for unidade in (api, residente):
        assert "Type=simple" in unidade
        assert "WorkingDirectory=%h/Nyxal" in unidade
        assert "EnvironmentFile=-%h/.config/nyxal/nyxal.env" in unidade
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
        assert "CapabilityBoundingSet=" in unidade
        assert "RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6" in unidade
        assert "ProtectClock=true" in unidade
        assert "ProtectKernelLogs=true" in unidade
        assert "%h/Nyxal/.venv/bin/python" in unidade
        assert "/usr/bin/python3" not in unidade

    assert "Restart=always" in api
    assert "RestartSec=2" in api
    assert "Restart=on-failure" in residente
    assert "RestartSec=3" in residente

    assert (
        "ExecStart=%h/Nyxal/.venv/bin/python %h/Nyxal/nyxal_web_api.py"
        in api
    )
    assert (
        "ExecStart=%h/Nyxal/.venv/bin/python "
        "%h/Nyxal/executar_nyxos_residente.py --intervalo 5 "
        "--continuar-em-erro --habilitar-aprendizado --habilitar-auto-experimento"
        in residente
    )
    assert "--habilitar-ae5-descoberta" in residente
    assert "--habilitar-ae5-descoberta" not in api
    assert "StartLimitIntervalSec=300" in residente
    assert "StartLimitBurst=10" in residente
    assert "--habilitar-auto-experimento" not in api
    assert "--habilitar-aprendizado" not in api

    assert "Wants=nyxal-api.service nyxos-residente.service" in target
    assert "WantedBy=default.target" in target
    interface = ler("nyxos-interface.service")
    reset_service = ler("nyxos-interface-reset.service")
    reset_timer = ler("nyxos-interface-reset.timer")
    assert "Type=oneshot" in reset_service
    assert "systemctl --user try-restart nyxos-interface.service" in reset_service
    assert "OnActiveSec=2h" in reset_timer
    assert "OnUnitActiveSec=2h" in reset_timer
    assert "Unit=nyxos-interface-reset.service" in reset_timer
    assert (
        "ExecStart=/usr/bin/bash %h/Nyxal/deploy/systemd/iniciar_nyxos_shell.sh"
        in interface
    )
    assert "find_browser()" in shell_principal
    assert 'exec "${BROWSER}"' in shell_principal
    assert "iniciar_nyxos_shell.sh" in diagnostico

    assert "systemctl --user disable --now nyxal-desktop.service" in instalador
    assert "systemctl --user disable --now nyxos-interface.service" not in instalador
    assert "systemctl --user enable nyxos-interface.service" in instalador
    assert 'install -m 0644 "${SCRIPT_DIR}/nyxos-interface-reset.service"' in instalador
    assert 'install -m 0644 "${SCRIPT_DIR}/nyxos-interface-reset.timer"' in instalador
    assert "systemctl --user enable --now nyxos-interface-reset.timer" in instalador
    assert "systemctl --user restart nyxos-interface.service" in instalador
    assert 'self._unidade_habilitada(self.UNIDADE_INTERFACE)' in autoreparo
    assert '"desativada_por_configuracao"' in autoreparo

    assert "systemctl --user daemon-reload" in instalador
    assert "systemctl --user enable --now nyxos.target" in instalador
    assert 'systemctl --user restart "${unidade}"' in instalador
    assert 'for unidade in nyxal-api.service nyxos-residente.service; do' in instalador
    assert "diagnosticar_nyxos_local.sh" in instalador
    assert "nyxos-interface-reset.timer" in diagnostico
    assert "nyxos-interface-reset.service" in diagnostico
    assert "systemctl --user show" in diagnostico
    assert "prazo = time.monotonic() + 15.0" in diagnostico
    assert 'time.sleep(0.5)' in diagnostico
    assert 'conexao.request("GET", "/health"' in diagnostico
    assert "cmp -s" in diagnostico
    assert "NYXAL_API_TOKEN" not in diagnostico
    assert 'PYTHON_BIN="${NYXAL_DIR}/.venv/bin/python"' in instalador
    assert '[[ ! -x "${PYTHON_BIN}" ]]' in instalador
    assert 'import nyxal_web_api; import executar_nyxos_residente' in instalador
    assert "validar_diretorios_sem_links() {" in instalador
    assert (
        'for caminho in "${HOME}/.config" "${HOME}/.config/systemd" '
        '"${USER_SYSTEMD_DIR}" "${AUTOSTART_DIR}" "${CONFIG_DIR}";'
        in instalador
    )
    assert instalador.index("if ! validar_diretorios_sem_links; then") < instalador.index("mkdir -p")
    assert instalador.index("mkdir -p") < instalador.index("# Revalida após a criação")
    assert instalador.count("if ! validar_diretorios_sem_links; then") == 2
    assert 'chmod 700 "${CONFIG_DIR}"' in instalador
    assert 'ENV_FILE="${CONFIG_DIR}/nyxal.env"' in instalador
    assert '[[ -L "${ENV_FILE}" ]]' in instalador
    assert '[[ -e "${ENV_FILE}" && ! -f "${ENV_FILE}" ]]' in instalador
    assert 'chmod 600 "${ENV_FILE}"' in instalador
    assert 'loginctl enable-linger "${USER}"' in instalador
    assert "LINGER_STATUS" in instalador
    assert "sudo " not in instalador
    assert "/etc/systemd" not in instalador
    assert "senha" not in instalador.lower()
    assert "token" not in instalador.lower()

    assert "systemctl --user disable --now nyxos-interface-reset.timer" in desinstalador
    assert "nyxos-interface-reset.service" in desinstalador
    assert "nyxos-interface-reset.timer" in desinstalador
    assert "systemctl --user disable --now nyxos.target" in desinstalador
    assert "rm -f" in desinstalador
    assert "main" not in desinstalador.lower()

    testar_historico_residente_limitado()

    launcher = (BASE_DIR / "executar_nyxos_residente.py").read_text(
        encoding="utf-8"
    )
    assert "modo_residente=True" in launcher
    assert '"--habilitar-ae5-descoberta"' in launcher

    runtime = (BASE_DIR / "nixal_runtime.py").read_text(
        encoding="utf-8"
    )
    assert "modo_residente: bool = False" in runtime
    assert "investigacao_profunda_adiada_no_perfil_residente" in runtime
    assert "log_nyxal_residente.json" in runtime

    print("TESTE_M5_9_RESIDENCIA_LINUX_OK")
    print("TESTE_MEMORIA_RESIDENTE_LIMITADA_OK")
    print("PYTHON: .venv/bin/python")
    print("SERVICOS: API + RESIDENTE + INTERFACE PRINCIPAL; ORBE FLUTUANTE DESATIVADO")
    print("TARGET: nyxos.target")
    print("AE2_AUTOMATICA: HABILITADA_COM_GATES")
    print("AE5_DESCOBERTA_CONTINUA: HABILITADA_COM_GATES")
    print("AUTOREPARO: API/INTERFACE_COM_LIMITES")


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
