#!/usr/bin/env bash
# Nyxal Fase 0: backup verificável e inventário sem atualizar o checkout vivo.
# Executar como: sudo bash /caminho/nyxal_fase0.sh
set -Eeuo pipefail
umask 077

die() { echo "[ERRO] $*" >&2; exit 1; }
note() { echo "[INFO] $*"; }

[[ "$EUID" -eq 0 ]] || die "Execute com sudo para preservar permissões e acessar o estado privado."
TARGET_USER="${SUDO_USER:-}"
[[ -n "$TARGET_USER" && "$TARGET_USER" != "root" ]] || die "SUDO_USER ausente. Execute com sudo a partir da conta que executa a Nyxal."

PASSWD_ENTRY="$(getent passwd "$TARGET_USER" || true)"
[[ -n "$PASSWD_ENTRY" ]] || die "Não foi possível resolver a conta $TARGET_USER."
TARGET_UID="$(printf '%s' "$PASSWD_ENTRY" | cut -d: -f3)"
TARGET_HOME="$(printf '%s' "$PASSWD_ENTRY" | cut -d: -f6)"
[[ -n "$TARGET_HOME" && -d "$TARGET_HOME" && ! -L "$TARGET_HOME" ]] || die "HOME do operador inválido ou simbólico: $TARGET_HOME"

REPO_DIR="${NYXAL_REPO_DIR:-$TARGET_HOME/Nyxal}"
BACKUP_ROOT="${NYXAL_BACKUP_ROOT:-/var/backups/nyxal}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S_%N)"
BACKUP_DIR="$BACKUP_ROOT/fase0_$TIMESTAMP"
PAYLOAD_DIR="$BACKUP_DIR/payload"
INVENTORY_PATH="$BACKUP_DIR/divergencias.log"
MANIFEST_PATH="$BACKUP_DIR/manifesto_hashes.txt"
ARCHIVE_PATH="$BACKUP_DIR/estado_vivo.tar.gz"
API_UNIT="nyxal-api.service"
RESIDENT_UNIT="nyxos-residente.service"
USER_SYSTEMD_DIR="$TARGET_HOME/.config/systemd/user"
RUNTIME_DIR="/run/user/$TARGET_UID"
BUS_SOCKET="$RUNTIME_DIR/bus"

git -C "$REPO_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "Checkout Git não encontrado em $REPO_DIR. Informe NYXAL_REPO_DIR sem executar git pull."
[[ ! -L "$BACKUP_ROOT" ]] || die "O diretório de backup é link simbólico: $BACKUP_ROOT"

# A instalação observada usa systemd --user. Se existir um serviço de sistema
# ativo com o mesmo nome, abortar: não presumir qual instância é a produção.
for unit in "$API_UNIT" "$RESIDENT_UNIT"; do
    if systemctl is-active --quiet "$unit"; then
        die "Há um serviço system-level ativo ($unit). A instalação está ambígua; nenhum serviço foi parado."
    fi
done

[[ -S "$BUS_SOCKET" ]] || die "Barramento systemd --user não disponível em $BUS_SOCKET. Nenhum serviço foi parado."
run_user() {
    runuser -u "$TARGET_USER" -- env HOME="$TARGET_HOME" USER="$TARGET_USER" LOGNAME="$TARGET_USER" XDG_RUNTIME_DIR="$RUNTIME_DIR" DBUS_SESSION_BUS_ADDRESS="unix:path=$BUS_SOCKET" systemctl --user "$@"
}
run_user show-environment >/dev/null 2>&1 || die "Não foi possível consultar o systemd --user da conta $TARGET_USER."

install -d -m 700 -o root -g root "$BACKUP_ROOT"
mkdir -m 700 "$BACKUP_DIR" || die "Não foi possível reservar um diretório de backup único: $BACKUP_DIR"
install -d -m 700 -o root -g root "$PAYLOAD_DIR"
install -d -m 700 "$PAYLOAD_DIR/meta"

# Preservar também todas as alterações rastreadas, inclusive arquivos fora
# da lista de estado. Esses patches ficam somente dentro do backup privado.
git -C "$REPO_DIR" diff --binary HEAD -- > "$PAYLOAD_DIR/meta/worktree_vs_HEAD.patch"
git -C "$REPO_DIR" diff --binary --cached > "$PAYLOAD_DIR/meta/index_vs_HEAD.patch"
git -C "$REPO_DIR" status --porcelain=v1 -z > "$PAYLOAD_DIR/meta/git_status_porcelain.bin"

WAS_ACTIVE=()
for unit in "$API_UNIT" "$RESIDENT_UNIT"; do
    if run_user is-active --quiet "$unit"; then WAS_ACTIVE+=("$unit"); fi
done
SERVICES_NEED_RESTORE=1

restore_services() {
    local rc=0
    local unit
    # Recria a ordem de dependência: API antes do residente.
    for unit in "${WAS_ACTIVE[@]}"; do
        if ! run_user start "$unit"; then
            echo "[ERRO] Não foi possível iniciar $unit." >&2
            rc=1
        fi
    done
    for unit in "${WAS_ACTIVE[@]}"; do
        if ! run_user is-active --quiet "$unit"; then
            echo "[ERRO] $unit não está ativo após a tentativa de restauração." >&2
            rc=1
        fi
    done
    if [[ "$rc" -eq 0 ]]; then SERVICES_NEED_RESTORE=0; fi
    return "$rc"
}

cleanup() {
    local rc=$?
    trap - EXIT
    if [[ "$SERVICES_NEED_RESTORE" -eq 1 ]]; then
        echo "[RECUPERAÇÃO] Restaurando os serviços que estavam ativos antes da Fase 0." >&2
        restore_services || rc=1
    fi
    exit "$rc"
}
trap cleanup EXIT

note "Backup: $BACKUP_DIR"
note "Conta da instalação: $TARGET_USER ($TARGET_UID)"
note "Checkout vivo: $REPO_DIR"
note "Serviços de usuário ativos antes da captura: ${WAS_ACTIVE[*]:-(nenhum)}"

# Serviços que escrevem no estado são pausados em ordem inversa apenas durante
# a captura. A trap tenta restaurar exatamente os que estavam ativos.
for ((i=${#WAS_ACTIVE[@]}-1; i>=0; i--)); do
    unit="${WAS_ACTIVE[$i]}"
    note "Parando temporariamente $unit para obter uma captura consistente."
    run_user stop "$unit" || die "Falha ao parar $unit; a recuperação automática será tentada."
done
sleep 2
for unit in "${WAS_ACTIVE[@]}"; do
    if run_user is-active --quiet "$unit"; then die "$unit continua ativo; snapshot abortado."; fi
done

# Todas as cópias preservam o caminho relativo e não seguem links simbólicos.
# Se algum dos caminhos-alvo for link, ou contiver links numa árvore de estado,
# o script aborta em vez de afirmar que fez backup completo de dados externos.
assert_safe_path() {
    local root="$1" relative="$2" current part nested_link
    [[ "$relative" != /* && "$relative" != *".."* ]] || die "Caminho relativo inseguro: $relative"
    [[ ! -L "$root" ]] || die "Raiz simbólica não suportada: $root"
    current="${root%/}"
    [[ -n "$current" ]] || current="/"
    IFS='/' read -r -a parts <<< "$relative"
    for part in "${parts[@]}"; do
        [[ -n "$part" ]] || continue
        if [[ "$current" == "/" ]]; then current="/$part"; else current="$current/$part"; fi
        [[ ! -L "$current" ]] || die "Link simbólico no caminho de estado; revisão manual necessária: $current"
    done
    if [[ -d "$root/$relative" ]]; then
        nested_link="$(find "$root/$relative" -type l -print -quit)"
        [[ -z "$nested_link" ]] || die "Link simbólico dentro da árvore; backup completo não pode ser garantido: $nested_link"
    fi
}

capture_path() {
    local root="$1" relative="$2" destination_root="$3" label="$4"
    local source destination
    source="${root%/}/$relative"
    destination="$destination_root/$relative"
    if [[ ! -e "$source" && ! -L "$source" ]]; then
        echo "AUSENTE | $label/$relative" >> "$PAYLOAD_DIR/meta/arquivos_ausentes.txt"
        return 0
    fi
    assert_safe_path "$root" "$relative"
    install -d -m 700 "$(dirname "$destination")"
    cp -a -- "$source" "$destination"
    echo "CAPTURADO | $label/$relative" >> "$PAYLOAD_DIR/meta/arquivos_capturados.txt"
}

REPO_STATE_PATHS=(
    "capacidades_nixal.json"
    "estado_corpo_nixal.json"
    "estado_nyxal_runtime.json"
    "estado_nyxos_operacional.json"
    "eventos_delta_nyxos.json"
    "fisiologia_operacional_nyxos.json"
    "gateway_atuacao_nyxos.json"
    "log_nyxal_residente.json"
    "memoria_aprendizado_nixal.json"
    "plano_central_controle_nyxos.json"
    "presenca_maquina_nyxos.json"
    "auditoria_atuacao_nyxos.jsonl"
    "auditoria_atuacao_nyxos.jsonl.lock"
    "memoria_investigacao_nixal.json"
    "memoria_investigacao_nixal.json.lock"
    "memoria_conhecimento_nixal.json"
    "memoria_conhecimento_nixal.json.lock"
    "memoria/cristal"
    "memoria/backups"
    "memoria/cristalizacao.json"
    "memoria/cristal_atual.json"
    "experimentos/cristal_gerenciador.bin"
)
HOME_STATE_PATHS=(
    ".local/share/nyxal"
    ".local/state/nyxal"
    ".config/nyxal/nyxal.env"
    ".config/systemd/user/nyxal-api.service"
    ".config/systemd/user/nyxos-residente.service"
    ".config/systemd/user/nyxos.target"
    ".config/systemd/user/nyxal-api.service.d"
    ".config/systemd/user/nyxos-residente.service.d"
    ".hermes/.env"
)
CRITICAL_MODULES=(
    "nixal_delta.py"
    "gerenciador_cristal.py"
    "nixal_aprovacao_defesa.py"
    "nixal_auditoria_defesa.py"
    "nixal_memoria_conversacional.py"
    "nixal_persistencia_operacional.py"
    "nixal_executor_defesa_governada.py"
    "nixal_runtime.py"
    "nyxal_web_api.py"
    "deploy/systemd/nyxal-api.service"
    "deploy/systemd/nyxos-residente.service"
)

: > "$PAYLOAD_DIR/meta/arquivos_capturados.txt"
: > "$PAYLOAD_DIR/meta/arquivos_ausentes.txt"
for relative in "${REPO_STATE_PATHS[@]}"; do
    capture_path "$REPO_DIR" "$relative" "$PAYLOAD_DIR/repo_state" "repo_state"
done
for relative in "${HOME_STATE_PATHS[@]}"; do
    capture_path "$TARGET_HOME" "$relative" "$PAYLOAD_DIR/home_state" "home_state"
done

# Arquivar também unidades system-level se existirem (inativas); a presença
# delas é evidência de configuração, mas o script nunca as altera.
for relative in "etc/systemd/system/nyxal-api.service" "etc/systemd/system/nyxos-residente.service" "etc/systemd/system/nyxos.target" "etc/systemd/system/nyxal-api.service.d" "etc/systemd/system/nyxos-residente.service.d"; do
    capture_path "/" "$relative" "$PAYLOAD_DIR/system_state" "system_state"
done

install -d -m 700 "$PAYLOAD_DIR/repo_code_snapshot"
for relative in "${CRITICAL_MODULES[@]}"; do
    capture_path "$REPO_DIR" "$relative" "$PAYLOAD_DIR/repo_code_snapshot" "repo_code_snapshot"
done

# Preserva arquivos não rastreados e não ignorados (por exemplo, código local
# fora do Git), exceto o estado operacional já capturado acima.
if git -C "$REPO_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    while IFS= read -r -d '' relative; do
        skip=0
        for known in "${REPO_STATE_PATHS[@]}"; do
            if [[ "$relative" == "$known" ]]; then skip=1; break; fi
        done
        if [[ "$skip" -eq 0 ]]; then
            capture_path "$REPO_DIR" "$relative" "$PAYLOAD_DIR/repo_untracked" "repo_untracked"
        fi
    done < <(git -C "$REPO_DIR" ls-files --others --exclude-standard -z)
fi

# O inventário não imprime conteúdo de variáveis secretas ou arquivos .env.
{
    echo "=== NYXAL FASE 0 — INVENTÁRIO DE DIVERGÊNCIAS ==="
    echo "Data: $(date -Iseconds)"
    echo "Host: $(hostname)"
    echo "Conta: $TARGET_USER (uid=$TARGET_UID)"
    echo "Checkout: $REPO_DIR"
    echo "Backup: $BACKUP_DIR"
    echo "Unit manager: systemd --user"
    echo "Serviços ativos antes da captura: ${WAS_ACTIVE[*]:-(nenhum)}"
    echo
    echo "--- GIT ---"
    echo "Branch: $(git -C "$REPO_DIR" branch --show-current 2>/dev/null || echo desconhecida)"
    echo "HEAD: $(git -C "$REPO_DIR" rev-parse HEAD 2>/dev/null || echo indisponível)"
    echo "origin/main local: $(git -C "$REPO_DIR" rev-parse --verify origin/main 2>/dev/null || echo ausente)"
    REMOTE_MAIN_SHA="$(timeout 8s git -C "$REPO_DIR" ls-remote origin refs/heads/main 2>/dev/null | awk 'NR==1 {print $1}' || true)"
    echo "main remoto (consulta read-only): ${REMOTE_MAIN_SHA:-indisponível}"
    echo "Status do checkout:"
    git -C "$REPO_DIR" status --short --branch 2>&1 || true
    echo
    echo "--- SERVIÇOS E UNIDADES ---"
    for unit in "$API_UNIT" "$RESIDENT_UNIT"; do
        if run_user is-active --quiet "$unit"; then state=active; else state=inactive; fi
        fragment="$(run_user show "$unit" -p FragmentPath --value 2>/dev/null || true)"
        echo "$unit | estado após captura: $state | unit efetiva: ${fragment:-desconhecida}"
    done
    for unit in "$API_UNIT" "$RESIDENT_UNIT"; do
        if [[ -f "/etc/systemd/system/$unit" ]]; then echo "ALERTA | unidade system-level existe: /etc/systemd/system/$unit"; fi
    done
    echo
    echo "--- VARIÁVEIS DE ESTADO NA UNIT DE USUÁRIO ---"
    live_unit="$USER_SYSTEMD_DIR/$API_UNIT"
    for variable in NYXAL_CONVERSATION_MEMORY_PATH NYXAL_STATE_DIR NYXAL_CRISTAL_PATH NYXAL_DELTA_PATH NYXAL_APPROVAL_JOURNAL; do
        if [[ -f "$live_unit" ]] && grep -Eq "^[[:space:]]*Environment=(.*[[:space:]])?${variable}=" "$live_unit"; then
            echo "PRESENTE na unit: $variable"
        else
            echo "AUSENTE na unit: $variable"
        fi
    done
    if [[ -f "$live_unit" ]]; then
        echo "EnvironmentFile declarado: $(grep -E '^[[:space:]]*EnvironmentFile=' "$live_unit" | sed 's/^[[:space:]]*EnvironmentFile=//' | sed 's/^[[:space:]]*[-]//' | tr '\n' ' ' || true)"
    else
        echo "ALERTA | unit efetiva não está no caminho esperado: $live_unit"
    fi
    echo
    echo "--- DIFF UNIT VIVA VS UNIT VERSIONADA ---"
    repo_unit="$REPO_DIR/deploy/systemd/nyxal-api.service"
    if [[ -f "$live_unit" && -f "$repo_unit" ]]; then
        diff -u <(sed -E '/^[[:space:]]*Environment=/s/=.*$/=[REDACTED_ENVIRONMENT_LINE]/' "$live_unit") <(sed -E '/^[[:space:]]*Environment=/s/=.*$/=[REDACTED_ENVIRONMENT_LINE]/' "$repo_unit") || true
    else
        echo "Comparação indisponível; confira a lista de arquivos ausentes no backup."
    fi
    echo
    echo "--- MÓDULOS CRÍTICOS: HASH WORKTREE VS HEAD VS origin/main LOCAL ---"
    for relative in "${CRITICAL_MODULES[@]}"; do
        working_hash=""
        head_hash=""
        origin_hash=""
        if [[ -f "$REPO_DIR/$relative" ]]; then working_hash="$(sha256sum "$REPO_DIR/$relative" | awk '{print $1}')"; fi
        if git -C "$REPO_DIR" cat-file -e "HEAD:$relative" 2>/dev/null; then
            head_hash="$(git -C "$REPO_DIR" show "HEAD:$relative" | sha256sum | awk '{print $1}')"
        else
            head_hash="NAO_RASTREADO_NO_HEAD"
        fi
        if git -C "$REPO_DIR" cat-file -e "origin/main:$relative" 2>/dev/null; then
            origin_hash="$(git -C "$REPO_DIR" show "origin/main:$relative" | sha256sum | awk '{print $1}')"
        else
            origin_hash="NAO_DISPONIVEL_EM_ORIGIN_MAIN_LOCAL"
        fi
        [[ -n "$working_hash" ]] || working_hash="AUSENTE"
        echo "$relative | worktree=$working_hash | HEAD=$head_hash | origin/main-local=$origin_hash"
    done
    echo
    echo "--- ESTADO OPERACIONAL ESPERADO ---"
    for relative in "${REPO_STATE_PATHS[@]}"; do
        if [[ -e "$REPO_DIR/$relative" ]]; then
            if [[ -f "$REPO_DIR/$relative" ]]; then echo "PRESENTE | $relative | $(sha256sum "$REPO_DIR/$relative" | awk '{print $1}')"; else echo "PRESENTE_DIR | $relative"; fi
        else
            echo "AUSENTE | $relative"
        fi
    done
    echo
    echo "--- CAPTURA ---"
    echo "Arquivos capturados: $(wc -l < "$PAYLOAD_DIR/meta/arquivos_capturados.txt")"
    echo "Caminhos ausentes registrados: $(wc -l < "$PAYLOAD_DIR/meta/arquivos_ausentes.txt")"
    echo "Conteúdo de arquivos .env/segredos não foi impresso neste relatório."
    echo "A matriz de hashes no backup cobre todos os arquivos regulares capturados."
    echo "A Fase 0 não atualiza o checkout nem modifica os dados de estado."
} > "$INVENTORY_PATH"

# Manifesto relativo ao payload e ensaio de restauração em diretório temporário.
(
    cd "$BACKUP_DIR"
    find payload -type f -print0 | sort -z | xargs -0 -r sha256sum > "$MANIFEST_PATH"
    sha256sum -c "$MANIFEST_PATH"
)
tar -czf "$ARCHIVE_PATH" -C "$BACKUP_DIR" payload
(
    cd "$BACKUP_DIR"
    sha256sum estado_vivo.tar.gz > estado_vivo.tar.gz.sha256
    sha256sum -c estado_vivo.tar.gz.sha256
)
REHEARSAL_DIR="$(mktemp -d "$BACKUP_DIR/restore-rehearsal.XXXXXX")"
tar -xzf "$ARCHIVE_PATH" -C "$REHEARSAL_DIR"
(cd "$REHEARSAL_DIR" && sha256sum -c "$MANIFEST_PATH")
rm -r -- "$REHEARSAL_DIR"
rm -r -- "$PAYLOAD_DIR"
chmod 600 "$ARCHIVE_PATH" "$BACKUP_DIR/estado_vivo.tar.gz.sha256" "$MANIFEST_PATH" "$INVENTORY_PATH"

# Restaurar a situação de serviço anterior antes de comunicar sucesso.
restore_services || die "Backup criado, mas não foi possível confirmar a restauração de todos os serviços. Revise systemctl --user status."
echo "[OK] Serviços que estavam ativos foram restaurados e verificados."
echo "=================================================="
echo "FASE 0 CONCLUÍDA — BACKUP VERIFICADO"
echo "Diretório: $BACKUP_DIR"
echo "Arquivo: $ARCHIVE_PATH"
echo "SHA-256: $(awk '{print $1}' "$BACKUP_DIR/estado_vivo.tar.gz.sha256")"
echo "Inventário: $INVENTORY_PATH"
echo "Manifesto: $MANIFEST_PATH"
echo "O conteúdo dos dados operacionais permanece protegido; revise divergencias.log antes da Fase 1."
echo "=================================================="
