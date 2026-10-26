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

# Não atravesse links simbólicos em diretórios de configuração: o instalador
# ajusta permissões, instala unidades e remove um autostart legado abaixo deles.
validar_diretorios_sem_links() {
    local caminho
    for caminho in "${HOME}/.config" "${HOME}/.config/systemd" "${USER_SYSTEMD_DIR}" "${AUTOSTART_DIR}" "${CONFIG_DIR}"; do
        if [[ -L "${caminho}" ]]; then
            echo "ERRO: ${caminho} não pode ser um link simbólico." >&2
            return 1
        fi
    done
}

if ! validar_diretorios_sem_links; then
    exit 1
fi

mkdir -p "${USER_SYSTEMD_DIR}" "${AUTOSTART_DIR}" "${CONFIG_DIR}"
# Revalida após a criação para evitar continuar se algum caminho apareceu como link.
if ! validar_diretorios_sem_links; then
    exit 1
fi
if [[ ! -d "${CONFIG_DIR}" ]]; then
    echo "ERRO: ${CONFIG_DIR} precisa ser um diretório." >&2
    exit 1
fi
chmod 700 "${CONFIG_DIR}"

ENV_FILE="${CONFIG_DIR}/nyxal.env"
if [[ -L "${ENV_FILE}" ]]; then
    echo "ERRO: ${ENV_FILE} não pode ser um link simbólico." >&2
    exit 1
fi
if [[ -e "${ENV_FILE}" && ! -f "${ENV_FILE}" ]]; then
    echo "ERRO: ${ENV_FILE} precisa ser um arquivo regular." >&2
    exit 1
fi
if [[ -f "${ENV_FILE}" ]]; then
    chmod 600 "${ENV_FILE}"
fi

if [[ -f "${NYXAL_DIR}/.gitmodules" ]] && command -v npm >/dev/null 2>&1; then
    git -C "${NYXAL_DIR}" submodule update --init --recursive
    bash "${NYXAL_DIR}/deploy/display/preparar_nyxos_display.sh"
else
    echo "AVISO: Nyxal-Display não foi preparado; mantendo a interface legada." >&2
fi

install -m 0644 "${SCRIPT_DIR}/nyxal-api.service" "${USER_SYSTEMD_DIR}/nyxal-api.service"
install -m 0644 "${SCRIPT_DIR}/nyxos-residente.service" "${USER_SYSTEMD_DIR}/nyxos-residente.service"
install -m 0644 "${SCRIPT_DIR}/nyxos-interface.service" "${USER_SYSTEMD_DIR}/nyxos-interface.service"
install -m 0755 "${SCRIPT_DIR}/iniciar_nyxos_interface.sh" "${USER_SYSTEMD_DIR}/iniciar_nyxos_interface.sh"
install -m 0755 "${SCRIPT_DIR}/iniciar_nyxos_shell.sh" "${USER_SYSTEMD_DIR}/iniciar_nyxos_shell.sh"
install -m 0644 "${SCRIPT_DIR}/nyxos.target" "${USER_SYSTEMD_DIR}/nyxos.target"

# O shell gráfico agora pertence ao graphical-session.target. O .desktop
# permanece apenas como fallback manual e não é instalado automaticamente,
# evitando duas instâncias do desktop NyxOS.
rm -f "${AUTOSTART_DIR}/nyxos-shell.desktop"

systemctl --user daemon-reload
if ! systemctl --user enable --now nyxos.target; then
    echo "ERRO: não foi possível ativar nyxos.target." >&2
    systemctl --user --no-pager --full status nyxos.target nyxal-api.service nyxos-residente.service || true
    exit 1
fi
systemctl --user enable nyxos-interface.service

# enable --now não reinicia unidades que já estão ativas. Reinicie API e residente
# para aplicar imediatamente o código/unidades recém-instalados.
CORE_RESTART_FAILED=0
for unidade in nyxal-api.service nyxos-residente.service; do
    if systemctl --user restart "${unidade}"; then
        echo "Unidade reiniciada: ${unidade}"
    else
        echo "ERRO: falha ao reiniciar ${unidade}; consulte o diagnóstico local." >&2
        CORE_RESTART_FAILED=1
    fi
done

if loginctl enable-linger "${USER}" 2>/dev/null; then
    LINGER_STATUS="ativado"
else
    LINGER_STATUS="não foi possível ativar automaticamente"
fi

if systemctl --user is-active --quiet graphical-session.target; then
    if systemctl --user restart nyxos-interface.service; then
        SHELL_STATUS="iniciado"
    else
        SHELL_STATUS="falha ao iniciar; consulte o diagnóstico local"
        CORE_RESTART_FAILED=1
    fi
else
    SHELL_STATUS="aguardando a próxima sessão gráfica"
fi

echo "Serviços NyxOS instalados e residência ativada."
echo "API: $(systemctl --user is-active nyxal-api.service || true)"
echo "Residente: $(systemctl --user is-active nyxos-residente.service || true)"
echo "Shell gráfico: ${SHELL_STATUS}"
echo "Lingering da conta: ${LINGER_STATUS}"
echo
echo "O servidor não depende mais de um terminal aberto."
echo "O desktop NyxOS será iniciado no graphical-session.target."
echo
echo "Para acompanhar:"
echo "  systemctl --user status nyxal-api.service nyxos-residente.service nyxos-interface.service"
echo "  journalctl --user -u nyxal-api.service -u nyxos-residente.service -u nyxos-interface.service -f"
echo "  bash ${NYXAL_DIR}/deploy/systemd/diagnosticar_nyxos_local.sh"
echo
if [[ "${CORE_RESTART_FAILED}" -ne 0 ]]; then
    echo "ATENÇÃO: uma ou mais unidades não iniciaram. O ambiente e as unidades foram instalados, mas a saúde dos serviços não foi confirmada." >&2
    systemctl --user --no-pager --full status nyxal-api.service nyxos-residente.service nyxos-interface.service || true
    exit 1
fi
if [[ "${LINGER_STATUS}" != "ativado" ]]; then
    echo "ATENÇÃO: para residência mesmo antes do login, execute:"
    echo "  loginctl enable-linger ${USER}"
fi
