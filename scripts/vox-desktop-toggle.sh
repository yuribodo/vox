#!/usr/bin/env bash
set -euo pipefail
umask 077

readonly project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly vox_binary="${project_root}/vox"
readonly overlay_script="${project_root}/scripts/vox-overlay.py"
readonly paste_script="${project_root}/scripts/paste-x11.py"
readonly sources_script="${project_root}/scripts/vox_audio_sources.py"
readonly history_script="${project_root}/scripts/vox_history.py"
readonly history_window_script="${project_root}/scripts/vox-history-window.py"
if [[ -n "${XDG_RUNTIME_DIR:-}" ]]; then
  [[ "$XDG_RUNTIME_DIR" == /* && "$XDG_RUNTIME_DIR" != "/" ]] || {
    printf 'vox: XDG_RUNTIME_DIR must be an absolute, non-root path\n' >&2
    exit 1
  }
  readonly runtime_root="${XDG_RUNTIME_DIR}/vox"
else
  readonly runtime_root="/tmp/vox-$(id -u)"
fi
readonly state_file="${runtime_root}/recording.json"
readonly status_file="${runtime_root}/desktop-status.json"
readonly target_file="${runtime_root}/desktop-target.json"
readonly source_file="${runtime_root}/desktop-source.json"
readonly transcript_file="${runtime_root}/desktop-transcript.txt"
readonly command_log="${runtime_root}/desktop-command.log"
readonly overlay_log="${runtime_root}/desktop-overlay.log"

if [[ -L "$runtime_root" ]]; then
  printf 'vox: refusing symlink runtime directory: %s\n' "$runtime_root" >&2
  exit 1
fi
mkdir -p -m 700 "$runtime_root"
[[ -d "$runtime_root" && ! -L "$runtime_root" ]] || {
  printf 'vox: runtime path is not a real directory: %s\n' "$runtime_root" >&2
  exit 1
}
[[ "$(stat -c %u "$runtime_root")" == "$(id -u)" ]] || {
  printf 'vox: runtime directory is not owned by the current user\n' >&2
  exit 1
}
chmod 700 "$runtime_root"

exec 9>"${runtime_root}/desktop-toggle.lock"
flock -n 9 || exit 0

write_status() {
  local state="$1"
  local message="$2"
  local temporary microphone_name microphone_node
  microphone_name="$(jq -r '.description // empty' "$source_file" 2>/dev/null || true)"
  microphone_node="$(jq -r '.name // empty' "$source_file" 2>/dev/null || true)"
  temporary="$(mktemp "${runtime_root}/.desktop-status.XXXXXX")"
  chmod 600 "$temporary"
  jq -n \
    --arg state "$state" \
    --arg message "$message" \
    --arg microphone_name "$microphone_name" \
    --arg microphone_node "$microphone_node" \
    --arg updated_at "$(date --iso-8601=seconds)" \
    '{state:$state,message:$message,updated_at:$updated_at}
      + if $microphone_name == "" then {} else
          {microphone_name:$microphone_name,microphone_node:$microphone_node}
        end' > "$temporary"
  mv -f "$temporary" "$status_file"
}

write_source() {
  local source_json="$1"
  local temporary
  jq -e 'select(
    (.id | type == "number") and
    (.name | type == "string" and length > 0) and
    (.description | type == "string" and length > 0)
  ) | {id,name,description}' <<<"$source_json" >/dev/null
  temporary="$(mktemp "${runtime_root}/.desktop-source.XXXXXX")"
  chmod 600 "$temporary"
  jq '{id,name,description}' <<<"$source_json" >"$temporary"
  mv -f "$temporary" "$source_file"
}

capture_default_source() {
  local snapshot source_json
  snapshot="$(python3 "$sources_script" list)"
  source_json="$(jq -c '.sources[] | select(.default == true)' <<<"$snapshot" | head -n 1)"
  [[ -n "$source_json" ]] || return 1
  write_source "$source_json"
}

launch_overlay() {
  setsid -f python3 "$overlay_script" --runtime-dir "$runtime_root" 9>&- >>"$overlay_log" 2>&1
}

friendly_error() {
  local detail="$1"
  case "$detail" in
    "transcription was empty"*) printf '%s\n' "Nenhuma fala detectada" ;;
    "transcription failed"*) printf '%s\n' "Falha ao transcrever — áudio preservado" ;;
    "recording is not usable"*) printf '%s\n' "Não consegui usar a gravação" ;;
    "write transcript failed"*) printf '%s\n' "Não consegui preparar o texto" ;;
    *) printf '%s\n' "$detail" ;;
  esac
}

capture_desktop_target() {
  local window_id window_name temporary
  window_id="$(xdotool getactivewindow 2>/dev/null)" || return 1
  [[ "$window_id" =~ ^[0-9]+$ ]] || return 1
  window_name="$(xdotool getwindowname "$window_id" 2>/dev/null)" || return 1
  temporary="$(mktemp "${runtime_root}/.desktop-target.XXXXXX")"
  chmod 600 "$temporary"
  jq -n \
    --arg window_id "$window_id" \
    --arg window_name "$window_name" \
    --arg captured_at "$(date --iso-8601=seconds)" \
    '{window_id:$window_id,window_name:$window_name,captured_at:$captured_at}' > "$temporary"
  mv -f "$temporary" "$target_file"
}

select_source() {
  local source_id="$1"
  local selected source_node
  [[ "$source_id" =~ ^[0-9]+$ ]] || return 1
  selected="$(python3 "$sources_script" select --id "$source_id")" || {
    write_status "error" "Microfone não está mais disponível"
    launch_overlay
    return 1
  }
  write_source "$selected"
  source_node="$(jq -r '.name' <<<"$selected")"

  if [[ ! -f "$state_file" ]]; then
    return 0
  fi

  write_status "starting" "Trocando microfone"
  launch_overlay
  if ! (exec 9>&-; cd "$project_root" && "$vox_binary" cancel) >>"$command_log" 2>&1; then
    write_status "error" "Não consegui trocar o microfone"
    return 1
  fi
  if ! (exec 9>&-; cd "$project_root" && "$vox_binary" toggle \
    --source "$source_node" --output "$transcript_file") >>"$command_log" 2>&1; then
    write_status "error" "Não consegui iniciar o novo microfone"
    return 1
  fi
  write_status "recording" "Super + V para concluir"
}

paste_last() {
  local window_id last_file status=0
  # A recording owns the Flow Bar; an error status here would hide it mid-dictation.
  [[ ! -f "$state_file" ]] || return 0
  window_id="$(xdotool getactivewindow 2>/dev/null)" || window_id=""
  if [[ ! "$window_id" =~ ^[0-9]+$ ]]; then
    write_status "error" "Foque um campo de texto e tente de novo"
    launch_overlay
    return 1
  fi
  last_file="$(mktemp "${runtime_root}/.desktop-paste-last.XXXXXX")"
  # Expanded now because last_file is local; also runs on an early set -e exit.
  trap "rm -f -- '$last_file'" EXIT
  python3 "$history_script" last >"$last_file" 2>>"$command_log" || status=$?
  if [[ "$status" -eq 0 ]] &&
    python3 "$paste_script" --window-id "$window_id" <"$last_file" 2>>"$command_log"; then
    write_status "done" "Texto inserido sem enviar"
  else
    # Short enough for the fixed-width error Flow Bar, which ellipsizes.
    case "$status" in
      0) write_status "error" "Não consegui colar" ;;
      3) write_status "error" "Nenhum texto salvo" ;;
      4) write_status "error" "Histórico desativado" ;;
      *) write_status "error" "Histórico ilegível" ;;
    esac
    status=1
  fi
  launch_overlay
  return "$status"
}

open_history() {
  local window_id
  [[ ! -f "$state_file" ]] || return 0
  # Captured now: once the history window opens, it is the active window.
  window_id="$(xdotool getactivewindow 2>/dev/null)" || window_id=""
  if [[ "$window_id" =~ ^[0-9]+$ ]]; then
    setsid -f python3 "$history_window_script" --window-id "$window_id" 9>&- >>"$overlay_log" 2>&1
  else
    setsid -f python3 "$history_window_script" 9>&- >>"$overlay_log" 2>&1
  fi
}

if [[ "${1:-}" == "--history" ]]; then
  [[ $# -eq 1 ]] || exit 2
  open_history
  exit $?
fi

if [[ "${1:-}" == "--paste-last" ]]; then
  [[ $# -eq 1 ]] || exit 2
  paste_last
  exit $?
fi

if [[ ! -x "$vox_binary" ]]; then
  write_status "error" "Compile o Vox primeiro: make build"
  launch_overlay
  exit 1
fi

if [[ "${1:-}" == "--select-source" ]]; then
  [[ $# -eq 2 ]] || exit 2
  select_source "$2"
  exit $?
fi

action="start"
if [[ -f "$state_file" ]]; then
  action="stop"
fi

if [[ "$action" == "start" ]]; then
  if [[ -f "$transcript_file" ]]; then
    mv "$transcript_file" "${runtime_root}/desktop-transcript-$(date +%Y%m%d-%H%M%S).txt"
  fi
  if ! capture_desktop_target; then
    write_status "error" "Foque um campo de texto e tente de novo"
    launch_overlay
    exit 1
  fi
  if ! capture_default_source; then
    write_status "error" "Nenhum microfone disponível"
    launch_overlay
    exit 1
  fi
  write_status "starting" "Conectando ao microfone"
else
  write_status "processing" "Transcrevendo localmente"
fi
launch_overlay

source_node="$(jq -r '.name // empty' "$source_file" 2>/dev/null || true)"

if (exec 9>&-; cd "$project_root" && "$vox_binary" toggle \
  --source "$source_node" --output "$transcript_file") 2>"$command_log"; then
  if [[ "$action" == "start" ]]; then
    write_status "recording" "Super + V para concluir"
  else
    # Save before pasting so a wrong or failed target never loses the text.
    history_saved=1
    python3 "$history_script" append <"$transcript_file" 2>>"$command_log" || history_saved=0
    window_id="$(jq -r '.window_id // empty' "$target_file" 2>/dev/null || true)"
    if [[ ! "$window_id" =~ ^[0-9]+$ ]]; then
      write_status "error" "Texto preservado: destino da janela foi perdido"
      exit 1
    fi
    if ! python3 "$paste_script" --window-id "$window_id" < "$transcript_file" 2>>"$command_log"; then
      write_status "error" "Texto preservado: não foi possível colar"
      exit 1
    fi
    # Without a history copy, keep the transcript; the next start archives it.
    if [[ "$history_saved" -eq 1 ]]; then
      rm -- "$transcript_file"
    fi
    rm -- "$target_file"
    write_status "done" "Texto inserido sem enviar"
  fi
  exit 0
fi

detail="$(tail -n 1 "$command_log" | sed -E 's/^vox:[[:space:]]*//' | cut -c1-180)"
if [[ -z "$detail" ]]; then
  detail="O Vox não conseguiu concluir a ação"
fi
message="$(friendly_error "$detail")"
write_status "error" "$message"
exit 1
