#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "${BASH_SOURCE[0]%/*}/../.." && pwd)"
SKILL_DIR="${HOME}/.hermes/skills"
if [[ "${ROOT}" != "${HOME}/Nyxal" ]]; then
    echo "Este instalador espera o repositório em ${HOME}/Nyxal." >&2
    exit 1
fi
mkdir -p "${SKILL_DIR}"
for source in "${ROOT}"/skills/nyxal-*; do
    [[ -d "${source}" ]] || continue
    name="$(basename "${source}")"
    target="${SKILL_DIR}/${name}"
    mkdir -p "${target}"
    install -m 0644 "${source}/SKILL.md" "${target}/SKILL.md"
done

SOUL_SOURCE="${ROOT}/deploy/agent/NYXAL_SOUL.md"
SOUL_TARGET="${HOME}/.hermes/SOUL.md"
if [[ -f "${SOUL_SOURCE}" ]]; then
    if [[ -f "${SOUL_TARGET}" ]]; then
        read -r -p "Substituir a identidade atual do Hermes por Nyxal? Uma cópia será preservada. [s/N]: " replace_soul
        if [[ "${replace_soul,,}" == "s" || "${replace_soul,,}" == "sim" ]]; then
            backup="${SOUL_TARGET}.backup.$(date +%Y%m%d%H%M%S)"
            cp -p "${SOUL_TARGET}" "${backup}"
            install -m 0644 "${SOUL_SOURCE}" "${SOUL_TARGET}"
            echo "Identidade Nyxal instalada. Backup anterior: ${backup}"
        else
            echo "Identidade atual preservada. Reexecute e aceite a substituição para unificar a personalidade."
        fi
    else
        install -m 0644 "${SOUL_SOURCE}" "${SOUL_TARGET}"
        echo "Identidade Nyxal instalada em ${SOUL_TARGET}."
    fi
fi
chmod 700 "${HOME}/.hermes" 2>/dev/null || true
echo "Skills Nyxal instaladas em ${SKILL_DIR}."
echo "Reinicie o CLI/gateway Hermes para recarregá-las."
echo "Nenhuma ferramenta de sistema foi habilitada por este script."
