#!/usr/bin/env bash
#
# start.sh - one-command launcher for a Python app.
#
#   ./start.sh                 run the app            (python -O -X faulthandler main.py)
#   ./start.sh arg1 arg2       run, forwarding args to main.py
#   ./start.sh -- --help       run, forwarding args that look like start.sh flags
#   ./start.sh --setup         only prepare the environment (venv + deps), don't run
#   ./start.sh --pm2           (re)start under pm2, using this same script
#   ./start.sh --help          show this help


set -Eeuo pipefail

SCRIPT_PATH="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/$(basename -- "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
cd -- "$SCRIPT_DIR"

ENTRY="${ENTRY:-main.py}"
REQUIREMENTS="${REQUIREMENTS:-requirements.txt}"
MIN_PYTHON="${MIN_PYTHON:-3.15}"
APP_NAME="${APP_NAME:-$(basename -- "$SCRIPT_DIR")}"

VENV_NAME=".venv"                      # the one we create / own
VENV_CANDIDATES=(".venv" "venv" "env" ".env")
PY_FLAGS=(-O -X faulthandler)          # <- the flags you want on every run

PY=""                                  # resolved interpreter (set by resolve_python)
ENV_KIND=""                            # how it was resolved (for logging)

if [[ -t 2 ]]; then
  C_DIM=$'\033[2m'; C_YEL=$'\033[33m'; C_RED=$'\033[31m'; C_OFF=$'\033[0m'
else
  C_DIM=""; C_YEL=""; C_RED=""; C_OFF=""
fi
log()  { printf '%s[start]%s %s\n'         "$C_DIM" "$C_OFF" "$*" >&2; }
vlog() { [[ "${START_VERBOSE:-0}" == 1 ]] && log "$*" || true; }
warn() { printf '%s[start] warn:%s %s\n'  "$C_YEL" "$C_OFF" "$*" >&2; }
die()  { printf '%s[start] error:%s %s\n' "$C_RED" "$C_OFF" "$*" >&2; exit 1; }
trap 'die "unexpected failure at line $LINENO: $BASH_COMMAND"' ERR

usage() { sed -n '3,18p' "$SCRIPT_PATH" | sed 's/^# \{0,1\}//'; }

use_uv() { [[ "${USE_UV:-1}" == 1 ]] && command -v uv >/dev/null 2>&1; }

py_ok() {
  local major="${MIN_PYTHON%%.*}" minor="${MIN_PYTHON#*.}"
  "$1" -c "import sys; sys.exit(0 if sys.version_info[:2] >= ($major, $minor) else 1)" \
    >/dev/null 2>&1
}

env_python() {
  local p
  for p in "$1/bin/python" "$1/bin/python3" "$1/Scripts/python.exe"; do
    if [[ -x "$p" ]]; then printf '%s\n' "$p"; return 0; fi
  done
  return 1
}

find_system_python() {
  local c
  for c in python3.15 python3 python; do
    if command -v "$c" >/dev/null 2>&1 && py_ok "$c"; then
      command -v "$c"; return 0
    fi
  done
  return 1
}

hash_file() {
  if   command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | cut -d' ' -f1
  elif command -v shasum    >/dev/null 2>&1; then shasum -a 256 "$1" | cut -d' ' -f1
  else cksum "$1" | awk '{print $1"-"$2}'
  fi
}

create_venv() {
  local base
  base="$(find_system_python)" \
    || die "no Python >= $MIN_PYTHON found on PATH. Install one or run: PYTHON=/path/to/python ./start.sh"
  log "creating $VENV_NAME with $("$base" --version 2>&1) ($base)"

  if use_uv; then
    uv venv --quiet --python "$base" "$SCRIPT_DIR/$VENV_NAME" \
      || { rm -rf -- "$SCRIPT_DIR/$VENV_NAME"; die "uv venv failed"; }
  else
    "$base" -m venv "$SCRIPT_DIR/$VENV_NAME" \
      || { rm -rf -- "$SCRIPT_DIR/$VENV_NAME"
           die "venv creation failed (Debian/Ubuntu: sudo apt install python3-venv)"; }
  fi
  PY="$(env_python "$SCRIPT_DIR/$VENV_NAME")" || die "venv created but no interpreter found inside it"
  ENV_KIND="created $VENV_NAME"
}

resolve_python() {
  local p d name
  if [[ -n "${PYTHON:-}" ]]; then
    p="$(command -v "$PYTHON" 2>/dev/null)" || die "PYTHON='$PYTHON' not found"
    py_ok "$p" || die "PYTHON='$PYTHON' is not usable or older than $MIN_PYTHON"
    PY="$p"; ENV_KIND="PYTHON override"; return 0
  fi

  if [[ -n "${VIRTUAL_ENV:-}" ]] && p="$(env_python "$VIRTUAL_ENV")" && py_ok "$p"; then
    PY="$p"; ENV_KIND="active venv ($VIRTUAL_ENV)"; return 0
  fi

  d="$SCRIPT_DIR/$VENV_NAME"
  if [[ -f "$d/pyvenv.cfg" ]]; then
    p="$(env_python "$d" || true)"
    if [[ -z "$p" ]] || ! py_ok "$p"; then
      warn "$VENV_NAME is broken or older than $MIN_PYTHON - recreating"
      rm -rf -- "$d"
    fi
  fi

  for name in "${VENV_CANDIDATES[@]}"; do
    d="$SCRIPT_DIR/$name"
    [[ -d "$d" ]] || continue
    if p="$(env_python "$d")" && py_ok "$p"; then
      PY="$p"; ENV_KIND="$name"; return 0
    fi
  done

  # 5. Active conda env
  if [[ -n "${CONDA_PREFIX:-}" ]] && p="$(env_python "$CONDA_PREFIX")" && py_ok "$p"; then
    PY="$p"; ENV_KIND="conda ($CONDA_PREFIX)"; return 0
  fi

  create_venv
}

sync_requirements() {
  if [[ ! -f "$REQUIREMENTS" ]]; then
    warn "$REQUIREMENTS not found - skipping dependency install"
    return 0
  fi

  local root stamp_file want have
  root="$("$PY" -c 'import sys; print(sys.prefix)')"
  stamp_file="$root/.start.stamp"
  want="$(hash_file "$REQUIREMENTS")-$("$PY" -c 'import sys; print("%d.%d.%d" % sys.version_info[:3])')"
  have="$(cat "$stamp_file" 2>/dev/null || true)"

  if [[ "$want" == "$have" && "${FORCE_INSTALL:-0}" != 1 ]]; then
    vlog "dependencies up to date"
    return 0
  fi

  log "installing $REQUIREMENTS ..."
  if use_uv; then
    uv pip install --quiet --python "$PY" -r "$REQUIREMENTS" \
      || die "dependency install failed (uv)"
  else
    "$PY" -m pip --version >/dev/null 2>&1 || "$PY" -m ensurepip --upgrade >/dev/null 2>&1 \
      || die "pip is not available in this environment"
    "$PY" -m pip install --disable-pip-version-check --quiet -r "$REQUIREMENTS" \
      || die "dependency install failed (pip)"
  fi
  printf '%s\n' "$want" >"$stamp_file" 2>/dev/null || warn "could not write $stamp_file (will reinstall next run)"
}

prepare() {
  resolve_python
  log "python $("$PY" -c 'import platform; print(platform.python_version())') [$ENV_KIND]"
  sync_requirements
}

run_app() {
  [[ -f "$ENTRY" ]] || die "entry file '$ENTRY' not found in $SCRIPT_DIR"

  export PYTHON_JIT="${PYTHON_JIT:-1}"
  export PYTHONUNBUFFERED="${PYTHONUNBUFFERED:-1}"   # so pm2/journald logs appear immediately

  [[ -n "${pm_id:-}" ]] && vlog "running under pm2 (id $pm_id)"
  vlog "exec: PYTHON_JIT=$PYTHON_JIT $PY ${PY_FLAGS[*]} $ENTRY $*"

  trap - ERR
  exec "$PY" "${PY_FLAGS[@]}" "$ENTRY" "$@"
}

start_pm2() {
  command -v pm2 >/dev/null 2>&1 || die "pm2 not found (install with: npm i -g pm2)"
  prepare   # fail loudly here in your terminal rather than in a pm2 restart loop

  if pm2 describe "$APP_NAME" >/dev/null 2>&1; then
    log "restarting pm2 process '$APP_NAME'"
    pm2 restart "$APP_NAME" --update-env
  else
    log "starting pm2 process '$APP_NAME'"
    if (( $# )); then
      pm2 start "$SCRIPT_PATH" --name "$APP_NAME" --interpreter bash --time -- "$@"
    else
      pm2 start "$SCRIPT_PATH" --name "$APP_NAME" --interpreter bash --time
    fi
  fi
  log "tip: 'pm2 save' to persist across reboots, 'pm2 logs $APP_NAME' to tail output"
}

main() {
  case "${1:-}" in
    --setup)   shift; prepare; log "environment ready"; return 0 ;;
    --pm2)     shift; start_pm2 "$@"; return 0 ;;
    -h|--help) usage; return 0 ;;
    --)        shift ;;
  esac
  prepare
  run_app "$@"
}

main "$@"
