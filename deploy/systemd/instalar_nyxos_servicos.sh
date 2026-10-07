#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NYXAL_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
USER_SYSTEMD_DIR="${HOME}/.config/systemd/user"
AUTOSTART_DIR="${HOME}/.config/autostart"
CONFIG_DIR="${HOME}/.config/nyxal"
PYTHON_BIN="${NYXAL_DIR}/.venv/bin/python"

if [[ "${NYXAL_DIR}" != "${HOME}/Nyxal" ]]; then
    echo "ERRO: esta instalação espera o repositório em ${HOME}/Nyxal."
    echo "Diretório detectado: ${NYXAL_DIR}"
    exit 1
fi

if [[ ! -x "${PYTHON_BIN}" ]]; then
    echo "ERRO: ambiente Python do Nyxal não encontrado em ${PYTHON_BIN}."
    echo "Crie/ative o ambiente .venv e instale as dependências antes da residência."
    exit 1
fi

if ! "${PYTHON_BIN}" -c "import nyxal_web_api; import executar_nyxos_residente" >/dev/null 2>&1; then
    echo "ERRO: o ambiente .venv não consegue importar a pilha residente do NyxOS."
    echo "Verifique as dependências Python do projeto antes de instalar os serviços."
    exit 1
fi

mkdir -p "${USER_SYSTEMD_DIR}" "${AUTOSTART_DIR}" "${CONFIG_DIR}"

install -m 0644 "${SCRIPT_DIR}/nyxal-api.service" "${USER_SYSTEMD_DIR}/nyxal-api.service"
install -m 0644 "${SCRIPT_DIR}/nyxos-residente.service" "${USER_SYSTEMD_DIR}/nyxos-residente.service"
install -m 0644 "${SCRIPT_DIR}/nyxos-interface.service" "${USER_SYSTEMD_DIR}/nyxos-interface.service"
install -m 0755 "${SCRIPT_DIR}/iniciar_nyxos_interface.sh" "${USER_SYSTEMD_DIR}/iniciar_nyxos_interface.sh"
install -m 0755 "${SCRIPT_DIR}/iniciar_nyxos_shell.sh" "${USER_SYSTEMD_DIR}/iniciar_nyxos_shell.sh"
install -m 0644 "${SCRIPT_DIR}/nyxos.target" "${USER_SYSTEMD_DIR}/nyxos.target"

AUTOSTART_STATUS="fallback_systemd"
if install -m 0644 "${NYXAL_DIR}/deploy/autostart/nyxos-shell.desktop" "${AUTOSTART_DIR}/nyxos-shell.desktop" 2>/dev/null; then
    AUTOSTART_STATUS="desktop"
else
    echo "AVISO: não foi possível instalar o autostart .desktop; usando residência via systemd --user." >&2
fi

systemctl --user daemon-reload
systemctl --user enable --now nyxos.target

if loginctl enable-linger "${USER}" 2>/dev/null; then
    LINGER_STATUS="ativado"
else
    LINGER_STATUS="não foi possível ativar automaticamente"
fi

echo "Serviços NyxOS instalados e iniciados."
echo "Lingering da conta: ${LINGER_STATUS}"
echo "Autostart do shell: ${AUTOSTART_STATUS}"
echo
echo "Interpretador residente: ${PYTHON_BIN}"
echo "Vídeo de inicialização: ${NYXAL_DIR}/interface/assets/nyxos-startup.mp4"
if command -v mpv >/dev/null 2>&1; then
    echo "Reprodutor de vídeo: mpv"
else
    echo "AVISO: mpv não encontrado; o vídeo de inicialização não será reproduzido até sua instalação."
fi
echo "Para acompanhar:"
echo "  systemctl --user status nyxos.target"
echo "  journalctl --user -u nyxal-api.service -u nyxos-residente.service -f"
echo
if [[ "${LINGER_STATUS}" != "ativado" ]]; then
    echo "Para residência também sem login gráfico, execute:"
    echo "  loginctl enable-linger ${USER}"
fi
