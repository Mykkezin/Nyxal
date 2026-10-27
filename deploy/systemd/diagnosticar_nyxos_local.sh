#!/usr/bin/env bash
set -uo pipefail

SCRIPT_DIR="${BASH_SOURCE[0]}"
SCRIPT_DIR="$(cd "$(dirname "${SCRIPT_DIR}")" && pwd)"
NYXAL_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PYTHON_BIN="${NYXAL_DIR}/.venv/bin/python"
USER_SYSTEMD_DIR="${HOME}/.config/systemd/user"
ENV_FILE="${HOME}/.config/nyxal/nyxal.env"

printf '%s\n' '=== Diagnóstico local Nyxal / NyxOS (somente leitura) ==='
printf 'Repositório: %s\n' "${NYXAL_DIR}"
printf 'Python do ambiente: %s\n' "${PYTHON_BIN}"

if ! command -v systemctl >/dev/null 2>&1; then
  echo 'ERRO: systemctl não está disponível neste sistema.'
  exit 2
fi

for unidade in nyxos.target nyxal-api.service nyxos-residente.service nyxos-interface.service; do
  printf '\n--- %s ---\n' "${unidade}"
  if systemctl --user show "${unidade}" \
      --property=LoadState,ActiveState,SubState,Result,ExecMainStatus,NRestarts,FragmentPath \
      --no-pager 2>/dev/null; then
    :
  else
    echo 'Não foi possível consultar a unidade (ausente, user systemd indisponível ou sessão sem barramento).'
  fi

  fonte="${NYXAL_DIR}/deploy/systemd/${unidade}"
  instalada="${USER_SYSTEMD_DIR}/${unidade}"
  if [[ -f "${fonte}" && -f "${instalada}" ]]; then
    if cmp -s "${fonte}" "${instalada}"; then
      echo 'Unidade instalada: sincronizada com o repositório.'
    else
      echo 'ALERTA: unidade instalada está DESATUALIZADA em relação ao repositório.'
    fi
  elif [[ ! -f "${instalada}" ]]; then
    echo 'ALERTA: unidade ainda não foi instalada.'
  fi
done

SHELL_SCRIPT="${NYXAL_DIR}/deploy/systemd/iniciar_nyxos_shell.sh"
printf '\n--- Entrypoint do desktop NyxOS ---\n'
if [[ ! -f "${SHELL_SCRIPT}" ]]; then
  echo "ERRO: script de entrada ausente: ${SHELL_SCRIPT}"
elif [[ ! -x /usr/bin/bash ]]; then
  echo 'ERRO: /usr/bin/bash não existe ou não é executável.'
else
  printf 'Arquivo: %s\n' "${SHELL_SCRIPT}"
  stat -c 'Permissões: %A (%a)' "${SHELL_SCRIPT}" 2>/dev/null || true
  if /usr/bin/bash -n "${SHELL_SCRIPT}"; then
    echo 'Sintaxe Bash do desktop: OK.'
  else
    echo 'ERRO: a sintaxe Bash do entrypoint falhou.'
  fi
fi

if [[ -f "${ENV_FILE}" ]]; then
  printf '\nConfiguração local existe; modo/permissões: '
  stat -c '%a' "${ENV_FILE}" 2>/dev/null || echo 'indisponível'
  echo 'O conteúdo de nyxal.env e quaisquer segredos não são exibidos.'
else
  echo
  echo 'AVISO: ~/.config/nyxal/nyxal.env não existe; provedores que dependem de credenciais podem ficar indisponíveis.'
fi

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo
  echo 'ERRO: .venv/bin/python não existe ou não é executável.'
  echo 'A instalação não pode iniciar o runtime até corrigir o ambiente virtual.'
  exit 2
fi

"${PYTHON_BIN}" - "${NYXAL_DIR}" "${ENV_FILE}" <<'PY'
import ast
import http.client
import re
import sys
import time
from pathlib import Path

root = Path(sys.argv[1])
env_file = Path(sys.argv[2])
arquivos = (
    "nyxal_web_api.py",
    "executar_nyxos_residente.py",
    "nixal_ciclo_residente.py",
    "nixal_autoreparo_residente.py",
)
falhas = []
for nome in arquivos:
    caminho = root / nome
    if not caminho.is_file():
        print(f"FALHA: arquivo obrigatório ausente: {nome}")
        falhas.append(nome)
        continue
    try:
        ast.parse(caminho.read_text(encoding="utf-8"), filename=nome)
        print(f"SINTAXE_OK: {nome}")
    except (OSError, UnicodeError, SyntaxError) as erro:
        print(f"SINTAXE_FALHOU: {nome} ({type(erro).__name__})")
        falhas.append(nome)

porta = 8010
try:
    if env_file.is_file():
        texto = env_file.read_text(encoding="utf-8")
        match = re.search(r"(?m)^\s*NYXAL_API_PORT\s*=\s*['\"]?([0-9]{1,5})['\"]?\s*(?:#.*)?$", texto)
        if match:
            candidata = int(match.group(1))
            if 1 <= candidata <= 65535:
                porta = candidata
except (OSError, UnicodeError):
    pass

saudavel = False
prazo = time.monotonic() + 15.0
ultima_falha = "nenhuma resposta HTTP válida"
while not saudavel and time.monotonic() < prazo:
    for host in ("127.0.0.1", "::1"):
        conexao = None
        try:
            conexao = http.client.HTTPConnection(host, porta, timeout=1)
            conexao.request("GET", "/health", headers={"Connection": "close"})
            resposta = conexao.getresponse()
            resposta.read(4096)
            if resposta.status == 200:
                print(f"API_HEALTH_OK: HTTP 200 em loopback, porta {porta}")
                saudavel = True
                break
            ultima_falha = f"HTTP {resposta.status} em {host}"
        except (OSError, TimeoutError, http.client.HTTPException) as erro:
            ultima_falha = f"{type(erro).__name__} em {host}"
        finally:
            if conexao is not None:
                conexao.close()
    if not saudavel and time.monotonic() < prazo:
        time.sleep(0.5)

if not saudavel:
    print(f"API_INDISPONIVEL: {ultima_falha} na porta {porta} após aguardar até 15 segundos")
if not saudavel:
    print("Ação recomendada: verifique os estados/resultados systemd exibidos acima e consulte o journal pelo comando abaixo.")
    print("journalctl --user -u nyxal-api.service -u nyxos-residente.service -u nyxos-interface.service -n 100 --no-pager")
if falhas:
    print("Corrija os arquivos/erros de sintaxe indicados antes de reiniciar os serviços.")
    raise SystemExit(2)
if not saudavel:
    raise SystemExit(1)
print("DIAGNOSTICO_SINTAXE_E_API_OK")
PY
status=$?

printf '\n=== Próximo passo seguro ===\n'
echo 'Após atualizar a main, aplique as unidades:'
echo '  bash deploy/systemd/instalar_nyxos_servicos.sh'
echo 'Para consultar novamente:'
echo '  bash deploy/systemd/diagnosticar_nyxos_local.sh'
exit "${status}"
