#!/usr/bin/env bash
# Read-only snapshot for identifying which Nyxal/LLM runtimes are active.
# Deliberately avoids printing full process command lines or environment values.
set -uo pipefail

section() { printf '\n=== %s ===\n' "$1"; }

section "Timestamp and host"
date --iso-8601=seconds
hostnamectl --static 2>/dev/null || hostname

section "Relevant user services (read-only)"
for unit in \
  nyxal-api.service \
  nyxal-desktop.service \
  nyxos-residente.service \
  nyxos-interface.service \
  ollama.service \
  ollama; do
  state="$(systemctl --user show "$unit" --property=LoadState,ActiveState,SubState,MainPID,FragmentPath --no-pager 2>/dev/null || true)"
  if [[ -n "$state" && "$state" != *$'LoadState=not-found'* ]]; then
    printf '[%s]\n%s\n' "$unit" "$state"
  fi
done

section "Other running user services (names/descriptions only)"
systemctl --user list-units --type=service --state=running --no-legend --no-pager 2>/dev/null \
  | awk '{ unit=$1; $1=""; sub(/^ /, ""); print unit " — " $0 }' \
  | grep -Ei 'nyx|nix|ollama|voice|assistant|agent|llm|qwen|hermes|letta|gemini|open.?webui|vllm|llama|local.?ai' \
  || true

section "System services matching assistant/LLM names (names/descriptions only)"
systemctl list-units --type=service --state=running --no-legend --no-pager 2>/dev/null \
  | awk '{ unit=$1; $1=""; sub(/^ /, ""); print unit " — " $0 }' \
  | grep -Ei 'nyx|nix|ollama|voice|assistant|agent|llm|qwen|hermes|letta|gemini|open.?webui|vllm|llama|local.?ai' \
  || true

section "Local Ollama runtime"
if command -v ollama >/dev/null 2>&1; then
  printf '%s\n' '-- ollama ps --'
  ollama ps 2>&1 || true
  printf '%s\n' '-- ollama list (model names only) --'
  ollama list 2>&1 | awk 'NR == 1 { print; next } { print $1 }'
else
  echo "Ollama CLI not found in PATH."
fi

section "Listening TCP ports (process names/PIDs only)"
ss -ltnp 2>/dev/null || true

section "Top processes (no command-line arguments)"
ps -eo pid,ppid,comm,etime,%cpu,%mem --sort=-%cpu 2>/dev/null | head -n 36

section "Executable paths and working directories for likely AI runtimes"
# Read /proc metadata only. Never read cmdline or environ: those may contain credentials.
while read -r pid comm; do
  exe="$(readlink -f "/proc/${pid}/exe" 2>/dev/null || true)"
  cwd="$(readlink -f "/proc/${pid}/cwd" 2>/dev/null || true)"
  ppid="$(awk '/^PPid:/ {print $2; exit}' "/proc/${pid}/status" 2>/dev/null || true)"
  cgroup="$(tr '\n' ' ' < "/proc/${pid}/cgroup" 2>/dev/null | cut -c1-180)"
  printf 'PID=%s PPID=%s COMM=%s EXE=%s CWD=%s CGROUP=%s\n' \
    "${pid}" "${ppid:-unknown}" "${comm}" "${exe:-unavailable}" \
    "${cwd:-unavailable}" "${cgroup:-unavailable}"
done < <(
  ps -eo pid=,comm= 2>/dev/null \
    | awk 'tolower($2) ~ /(python|node|ollama|qwen|hermes|letta|gemini|llama|vllm|nyx|nix)/ {print $1, $2}' \
    | head -n 60
)

section "Configured conversational provider/model (allowlisted non-secret settings only)"
env_file="${HOME}/.config/nyxal/nyxal.env"
if [[ -r "$env_file" ]]; then
  awk -F= '
    /^(NYXAL_LLM_PROVIDER|NYXAL_CONVERSATIONAL_MODEL|NYXAL_AMD_CLOUD_MODEL|NYXAL_AGENT_PROVIDER|OLLAMA_HOST)=/ {
      key=$1; sub(/^[^=]*=/, "", $0); print key "=" $0
    }
  ' "$env_file" | sed -E 's/[[:space:]]+#.*$//'
else
  echo "No readable ~/.config/nyxal/nyxal.env; provider may be configured elsewhere."
fi

section "Nyxal API health (no chat content)"
curl --max-time 3 -sS http://127.0.0.1:8010/health || true
printf '\n\nDone. No service was stopped, restarted, or modified. No API tokens or full process arguments were printed.\n'
