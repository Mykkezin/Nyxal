#!/usr/bin/env bash
set -euo pipefail

NYXAL_ENV="${HOME}/.config/nyxal/nyxal.env"
HERMES_ENV="${HOME}/.hermes/.env"
mkdir -p "${HOME}/.config/nyxal" "${HOME}/.hermes"
touch "${NYXAL_ENV}" "${HERMES_ENV}"
chmod 600 "${NYXAL_ENV}" "${HERMES_ENV}"

get_env() {
    local file="$1" key="$2"
    awk -F= -v key="${key}" '$1 == key { sub(/^[^=]*=/, ""); value=$0 } END { print value }' "${file}" 2>/dev/null || true
}
set_env() {
    local file="$1" key="$2" value="$3" tmp
    [[ "${value}" != *$'\n'* && "${value}" != *$'\r'* ]] || { echo "Valor inválido para ${key}." >&2; return 2; }
    tmp="$(mktemp)"
    awk -F= -v key="${key}" '$1 != key { print }' "${file}" > "${tmp}"
    printf '%s=%s\n' "${key}" "${value}" >> "${tmp}"
    cat "${tmp}" > "${file}"
    rm -f "${tmp}"
    chmod 600 "${file}"
}
prompt_secret() {
    local prompt="$1" value
    read -r -s -p "${prompt}" value
    printf '\n' >&2
    printf '%s' "${value}"
}

echo "=== Configuração local do agente Nyxal ==="
echo "Chaves serão armazenadas fora do Git, com permissão 600."
read -r -p "Provedor principal [auto/hermes/gemini/letta/nyxal] (auto): " provider
provider="${provider:-auto}"
case "${provider}" in auto|hermes|gemini|letta|nyxal) ;; *) echo "Provedor inválido." >&2; exit 2 ;; esac
set_env "${NYXAL_ENV}" "NYXAL_AGENT_PROVIDER" "${provider}"

read -r -p "Configurar Gemini direto no Nyxal? [s/N]: " use_gemini
if [[ "${use_gemini,,}" == "s" || "${use_gemini,,}" == "sim" ]]; then
    gemini_key="$(prompt_secret "Gemini API key (entrada oculta; Enter mantém a atual): ")"
    if [[ -n "${gemini_key}" ]]; then set_env "${NYXAL_ENV}" "NYXAL_GEMINI_API_KEY" "${gemini_key}"; fi
    read -r -p "Modelo Gemini [gemini-3.7-flash]: " gemini_model
    set_env "${NYXAL_ENV}" "NYXAL_GEMINI_MODEL" "${gemini_model:-gemini-3.7-flash}"
fi

read -r -p "Conectar o Nyxal ao Hermes Agent local? [S/n]: " use_hermes
if [[ -z "${use_hermes}" || "${use_hermes,,}" == "s" || "${use_hermes,,}" == "sim" ]]; then
    set_env "${NYXAL_ENV}" "NYXAL_HERMES_BASE_URL" "http://127.0.0.1:8642/v1"
    hermes_key="$(get_env "${HERMES_ENV}" "API_SERVER_KEY")"
    nyxal_key="$(get_env "${NYXAL_ENV}" "NYXAL_HERMES_API_KEY")"
    if [[ -n "${hermes_key}" ]]; then shared_key="${hermes_key}"
    elif [[ -n "${nyxal_key}" ]]; then shared_key="${nyxal_key}"
    else shared_key="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"; fi
    set_env "${HERMES_ENV}" "API_SERVER_ENABLED" "true"
    set_env "${HERMES_ENV}" "API_SERVER_HOST" "127.0.0.1"
    set_env "${HERMES_ENV}" "API_SERVER_PORT" "8642"
    set_env "${HERMES_ENV}" "API_SERVER_KEY" "${shared_key}"
    set_env "${NYXAL_ENV}" "NYXAL_HERMES_API_KEY" "${shared_key}"
    unset shared_key hermes_key nyxal_key
fi

read -r -p "Configurar agente Letta para memória persistente? [s/N]: " use_letta
if [[ "${use_letta,,}" == "s" || "${use_letta,,}" == "sim" ]]; then
    read -r -p "Letta base URL [http://127.0.0.1:8283]: " letta_url
    read -r -p "ID do agente Nyxal no Letta: " letta_id
    letta_key="$(prompt_secret "Letta API key (se exigida; entrada oculta): ")"
    set_env "${NYXAL_ENV}" "LETTA_BASE_URL" "${letta_url:-http://127.0.0.1:8283}"
    [[ -z "${letta_id}" ]] || set_env "${NYXAL_ENV}" "LETTA_AGENT_ID" "${letta_id}"
    [[ -z "${letta_key}" ]] || set_env "${NYXAL_ENV}" "LETTA_API_KEY" "${letta_key}"
    read -r -p "Enviar conversas ao agente Letta para revisão de memória? [s/N]: " sync_memory
    if [[ "${sync_memory,,}" == "s" || "${sync_memory,,}" == "sim" ]]; then set_env "${NYXAL_ENV}" "LETTA_MEMORY_SYNC_ENABLED" "true"
    else set_env "${NYXAL_ENV}" "LETTA_MEMORY_SYNC_ENABLED" "false"; fi
fi

set_env "${NYXAL_ENV}" "NYXAL_KOKORO_VOICE" "pf_dora"
chmod 600 "${NYXAL_ENV}" "${HERMES_ENV}"
echo "Configuração salva:"
echo "  ${NYXAL_ENV}"
echo "  ${HERMES_ENV}"
echo "Próximos passos: hermes model; hermes gateway setup; configurar Gmail conforme docs/NYXAL_AGENT_STACK.md;"
echo "reiniciar com: systemctl --user restart nyxal-api.service"
echo "verificar com: curl -fsS http://127.0.0.1:8010/api/agent/status"
