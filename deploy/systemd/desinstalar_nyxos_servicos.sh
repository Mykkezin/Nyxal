#!/usr/bin/env bash
set -euo pipefail

USER_SYSTEMD_DIR="${HOME}/.config/systemd/user"

systemctl --user disable --now nyxos.target 2>/dev/null || true
systemctl --user disable --now nyxal-api.service 2>/dev/null || true
systemctl --user disable --now nyxos-residente.service 2>/dev/null || true
systemctl --user daemon-reload

rm -f   "${USER_SYSTEMD_DIR}/nyxal-api.service"   "${USER_SYSTEMD_DIR}/nyxos-residente.service"   "${USER_SYSTEMD_DIR}/nyxos.target"

systemctl --user daemon-reload

echo "Serviços NyxOS removidos da sessão systemd do usuário."
echo "O arquivo de configuração em ~/.config/nyxal não foi removido."
