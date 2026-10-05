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
        assert "--habilitar-auto-experimento" not in unidade

    assert "ExecStart=/usr/bin/python3 %h/Nyxal/nyxal_web_api.py" in api
    assert (
        "ExecStart=/usr/bin/python3 %h/Nyxal/executar_nyxos_residente.py --intervalo 5"
        in residente
    )

    assert "Wants=nyxal-api.service nyxos-residente.service" in target
    assert "WantedBy=default.target" in target

    assert "systemctl --user daemon-reload" in instalador
    assert "systemctl --user enable --now nyxos.target" in instalador
    assert "loginctl enable-linger ${USER}" in instalador
assert "LINGER_STATUS" in instalador
    assert "sudo " not in instalador
    assert "/etc/systemd" not in instalador
    assert "senha" not in instalador.lower()
    assert "token" not in instalador.lower()

    assert "systemctl --user disable --now nyxos.target" in desinstalador
    assert "rm -f" in desinstalador
    assert "main" not in desinstalador.lower()

    print("TESTE_M5_9_RESIDENCIA_LINUX_OK")
    print("SERVICOS: 2")
    print("TARGET: nyxos.target")
    print("AE2_AUTOMATICA: DESABILITADA")


if __name__ == "__main__":
    main()
