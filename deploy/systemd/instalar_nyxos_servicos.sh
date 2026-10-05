#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NYXAL_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
USER_SYSTEMD_DIR="${HOME}/.config/systemd/user"
CONFIG_DIR="${HOME}/.config/nyxal"

if [[ "${NYXAL_DIR}" != "${HOME}/Nyxal" ]]; then
    echo "ERRO: esta instalação espera o repositório em ${HOME}/Nyxal."
    echo "Diretório detectado: ${NYXAL_DIR}"
    exit 1
fi

mkdir -p "${USER_SYSTEMD_DIR}" "${CONFIG_DIR}"

install -m 0644 "${SCRIPT_DIR}/nyxal-api.service" "${USER_SYSTEMD_DIR}/nyxal-api.service"
install -m 0644 "${SCRIPT_DIR}/nyxos-residente.service" "${USER_SYSTEMD_DIR}/nyxos-residente.service"
install -m 0644 "${SCRIPT_DIR}/nyxos.target" "${USER_SYSTEMD_DIR}/nyxos.target"

systemctl --user daemon-reload
systemctl --user enable nyxos.target

echo "Serviços NyxOS instalados."
echo "Para iniciar nesta sessão:"
echo "  systemctl --user start nyxos.target"
echo
echo "Para acompanhar:"
echo "  systemctl --user status nyxos.target"
echo "  journalctl --user -u nyxal-api.service -u nyxos-residente.service -f"
echo
echo "Para residência também sem login gráfico, habilite o lingering da conta:"
echo "  loginctl enable-linger ${USER}"
