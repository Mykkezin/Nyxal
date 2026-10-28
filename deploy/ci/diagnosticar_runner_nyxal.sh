#!/usr/bin/env bash
# Diagnóstico somente leitura do runner GitHub Actions da Nyxal.
# Não reinicia serviços, não apaga arquivos e não imprime linhas brutas de logs.
set -uo pipefail

RUNNER_ROOT="${1:-/home/nyxal/actions-runner}"
SINCE="${NYXAL_DIAG_SINCE:-30 minutes ago}"

section() { printf '\n=== %s ===\n' "$1"; }

printf 'NYXAL_RUNNER_DIAG_START\n'
printf 'timestamp_utc=%s\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || printf unavailable)"
printf 'hostname=%s\n' "$(hostname 2>/dev/null || printf unavailable)"
printf 'runner_root=%s\n' "$RUNNER_ROOT"
printf 'journal_window=%s\n' "$SINCE"
printf 'mode=read_only\n'

section 'Diretórios e permissões'
for path in \
  "$RUNNER_ROOT" \
  "$RUNNER_ROOT/_work" \
  "$RUNNER_ROOT/_work/_temp" \
  "$RUNNER_ROOT/_work/_temp/_runner_file_commands" \
  "$RUNNER_ROOT/_actions" \
  "$RUNNER_ROOT/_diag"; do
  if [[ -e "$path" ]]; then
    stat -c 'path=%n owner=%U group=%G mode=%a type=%F modified=%y' "$path" 2>/dev/null || printf 'path=%s stat=unavailable\n' "$path"
    if [[ -d "$path" ]]; then
      entries="$(find "$path" -mindepth 1 -maxdepth 1 -printf '.' 2>/dev/null | wc -c | tr -d ' ')"
      printf 'direct_entries=%s path=%s\n' "${entries:-unavailable}" "$path"
    fi
  else
    printf 'path=%s state=missing\n' "$path"
  fi
done

section 'Espaço e inodes'
if [[ -e "$RUNNER_ROOT" ]]; then
  df -h "$RUNNER_ROOT" 2>/dev/null || printf 'df_bytes=unavailable\n'
  df -i "$RUNNER_ROOT" 2>/dev/null || printf 'df_inodes=unavailable\n'
else
  printf 'filesystem=unavailable_runner_root_missing\n'
fi

section 'Processos Runner.Listener / Runner.Worker'
if command -v ps >/dev/null 2>&1; then
  ps -eo pid=,ppid=,user=,etime=,comm=,args= 2>/dev/null | awk -v root="$RUNNER_ROOT" '
    $5 ~ /^(Runner\.Listener|Runner\.Worker|runsvc\.sh)$/ {
      root_match = index($0, root) > 0
      if ($5 ~ /^Runner\.Listener$/) {
        if (root_match) listeners_root++; else listeners_other++
      }
      if ($5 ~ /^Runner\.Worker$/) {
        if (root_match) workers_root++; else workers_other++
      }
      if ($5 ~ /^runsvc\.sh$/) {
        if (root_match) service_scripts_root++; else service_scripts_other++
      }
      printf "pid=%s ppid=%s user=%s elapsed=%s command=%s root_match=%s\n", $1, $2, $3, $4, $5, (root_match ? "yes" : "no")
    }
    END {
      printf "summary_listener_same_root=%d listener_other_path=%d worker_same_root=%d worker_other_path=%d runsvc_same_root=%d runsvc_other_path=%d\n", listeners_root, listeners_other, workers_root, workers_other, service_scripts_root, service_scripts_other
      if (listeners_root > 1) print "warning=multiple_listener_processes_reference_same_runner_root"
    }
  '
else
  printf 'process_list=unavailable\n'
fi

section 'Serviços systemd do runner'
if command -v systemctl >/dev/null 2>&1; then
  mapfile -t RUNNER_UNITS < <(systemctl list-units --all --type=service --no-legend 'actions.runner.*.service' 2>/dev/null | awk '{print $1}')
  if (("${#RUNNER_UNITS[@]}" == 0)); then
    printf 'runner_units=none_visible\n'
  else
    for unit in "${RUNNER_UNITS[@]}"; do
      printf 'unit=%s\n' "$unit"
      systemctl show "$unit" -p LoadState -p ActiveState -p SubState -p MainPID --no-pager 2>/dev/null || printf 'service_state=unavailable\n'
      if command -v journalctl >/dev/null 2>&1; then
        for pattern in 'Missing file at path' 'set_output_' 'No such file or directory' 'Permission denied' 'Runner.Worker' 'Runner.Listener' 'cancelled' 'fatal'; do
          count="$(journalctl -u "$unit" --since "$SINCE" --no-pager -o cat 2>/dev/null | grep -Fic "$pattern" || true)"
          printf 'journal_match_count pattern=%q count=%s\n' "$pattern" "${count:-0}"
        done
      fi
    done
  fi
  printf '\n-- Timers que podem afetar workspace/temp (nomes, sem comandos) --\n'
  # NEXT e LAST são datas com largura variável, então a unit nunca está numa
  # coluna fixa: ela é sempre a penúltima e o serviço acionado é a última.
  systemctl list-timers --all --no-legend 2>/dev/null | awk '
    tolower($0) ~ /(nyxal|runner|clean|tmp|temp|work)/ {
      printf "timer_unit=%s proxima=%s %s %s %s aciona=%s\n", $(NF - 1), $1, $2, $3, $4, $NF
    }' || true
else
  printf 'systemd=unavailable\n'
fi

section 'Resumo de logs Runner (somente contagens, sem linhas brutas)'
if [[ -d "$RUNNER_ROOT/_diag" ]]; then
  mapfile -t LOGS < <(find "$RUNNER_ROOT/_diag" -maxdepth 1 -type f -name 'Runner_*.log' -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -n 3 | cut -d' ' -f2-)
  if (("${#LOGS[@]}" == 0)); then
    printf 'runner_log_files=none_found\n'
  else
    for file in "${LOGS[@]}"; do
      printf 'log_file=%s\n' "$(basename "$file")"
      for pattern in 'Missing file at path' 'set_output_' 'No such file or directory' 'Permission denied' 'DirectoryNotFoundException' 'Runner.Worker' 'Runner.Listener' 'fatal'; do
        count="$(grep -Fic "$pattern" "$file" 2>/dev/null || true)"
        printf 'log_match_count pattern=%q count=%s\n' "$pattern" "${count:-0}"
      done
    done
  fi
else
  printf 'runner_diag_directory=missing\n'
fi

printf '\nNota: ausência de _runner_file_commands depois que um job termina pode ser normal; compare horário, dono, processos e logs no momento da falha.\n'
printf 'NYXAL_RUNNER_DIAG_END\n'
