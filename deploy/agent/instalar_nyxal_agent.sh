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
chmod 700 "${HOME}/.hermes" 2>/dev/null || true
echo "Skills Nyxal instaladas em ${SKILL_DIR}."
echo "Reinicie o CLI/gateway Hermes para recarregá-las."
echo "Nenhuma ferramenta de sistema foi habilitada por este script."
