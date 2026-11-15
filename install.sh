#!/data/data/com.termux/files/usr/bin/env bash
# Install SnakTUI in an isolated venv, with a recorded launcher and uninstall.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -n "${PREFIX:-}" ]; then PREFIX_DIR="$PREFIX"; else PREFIX_DIR="$HOME/.local"; fi
DATA_ROOT="${XDG_DATA_HOME:-$HOME/.local/share}"
VENV="$DATA_ROOT/snaktui/venv"
BIN_DIR="$PREFIX_DIR/bin"
LAUNCHER="$BIN_DIR/snaktui"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/snaktui"
MANIFEST="$STATE_DIR/installed.tsv"
VENV_NOTE="$STATE_DIR/venv.path"
DRY=0
YES=0
UNINSTALL=0
MENU=1

usage() {
    cat <<EOF
Usage: ./install.sh [options]

Install:
  --prefix DIR   launcher prefix (default: \$PREFIX, else ~/.local)
  --dry-run      print what would change
  --no-menu      never show the interactive fzf menu

Uninstall:
  --uninstall    remove the launcher and the managed venv
  --yes          skip the uninstall confirmation

  -h, --help     show this help

The app itself lives in $VENV
EOF
}

die() { printf 'error: %s\n' "$*" >&2; exit 1; }
info() { printf '\033[38;2;123;216;143m[snaktui]\033[0m %s\n' "$*"; }
warn() { printf '\033[38;2;230;170;70m[snaktui]\033[0m %s\n' "$*" >&2; }
have() { command -v "$1" >/dev/null 2>&1; }

while [ "$#" -gt 0 ]; do
    case "$1" in
        --prefix) shift; [ "$#" -gt 0 ] || die "--prefix needs a directory"; PREFIX_DIR="$1" ;;
        --prefix=*) PREFIX_DIR="${1#*=}" ;;
        --dry-run) DRY=1 ;;
        --yes|-y) YES=1 ;;
        --uninstall) UNINSTALL=1 ;;
        --no-menu) MENU=0 ;;
        -h|--help) usage; exit 0 ;;
        *) die "unknown option: $1 (try --help)" ;;
    esac
    shift
done

case "$PREFIX_DIR" in
    /*) ;;
    *) PREFIX_DIR="$PWD/$PREFIX_DIR" ;;
esac
BIN_DIR="$PREFIX_DIR/bin"
LAUNCHER="$BIN_DIR/snaktui"

if [ "$MENU" = "1" ] && [ -t 0 ] && [ -t 1 ] && have fzf && [ "$UNINSTALL" = "0" ]; then
    choice=$(printf 'Install or update SnakTUI\nUninstall\nChange launcher prefix\nCancel\n' \
        | fzf --reverse --height=40% --border --prompt='SnakTUI install> ') || choice="Cancel"
    case "$choice" in
        "Install or update SnakTUI") ;;
        "Uninstall") UNINSTALL=1 ;;
        "Change launcher prefix")
            printf 'Launcher prefix [%s]: ' "$PREFIX_DIR"
            read -r new_prefix
            if [ -n "$new_prefix" ]; then
                PREFIX_DIR="$new_prefix"
                case "$PREFIX_DIR" in /*) ;; *) PREFIX_DIR="$PWD/$PREFIX_DIR" ;; esac
                BIN_DIR="$PREFIX_DIR/bin"; LAUNCHER="$BIN_DIR/snaktui"
            fi
            ;;
        *) echo "Canceled."; exit 0 ;;
    esac
fi

if [ "$UNINSTALL" = "1" ]; then
    if [ -f "$MANIFEST" ]; then
        IFS=$'\t' read -r stored_launcher _ < "$MANIFEST"
        [ -n "$stored_launcher" ] && LAUNCHER="$stored_launcher"
    fi
    if [ -f "$VENV_NOTE" ]; then
        stored_venv=$(cat "$VENV_NOTE")
        case "$stored_venv" in
            */snaktui/venv) VENV="$stored_venv" ;;
        esac
    fi
    [ -e "$LAUNCHER" ] || [ -e "$VENV" ] || { info "no SnakTUI install found"; exit 0; }
    if [ "$YES" = "0" ] && [ "$DRY" = "0" ]; then
        if [ -t 0 ]; then
            printf 'Remove %s and the venv at %s? [y/N] ' "$LAUNCHER" "$VENV"
            read -r reply
            case "$reply" in [Yy]*) ;; *) echo "Canceled."; exit 0 ;; esac
        else
            die "use --yes with --uninstall in a non-interactive shell"
        fi
    fi
    if [ "$DRY" = "1" ]; then
        printf '  would remove: %s\n' "$LAUNCHER"
        printf '  would remove: %s\n' "$VENV"
        exit 0
    fi
    rm -f "$LAUNCHER"
    case "$VENV" in
        */snaktui/venv) rm -rf "$VENV" ;;
        *) warn "refusing to remove unexpected venv path: $VENV" ;;
    esac
    rm -f "$MANIFEST" "$VENV_NOTE"
    rmdir "$STATE_DIR" 2>/dev/null || true
    rmdir "$DATA_ROOT/snaktui" 2>/dev/null || true
    info "uninstall complete"
    exit 0
fi

PY=python3
have "$PY" || die "python3 is required"
"$PY" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' \
    || die "Python 3.10 or newer is required"

if [ "$DRY" = "1" ]; then
    printf '  would create venv: %s\n' "$VENV"
    printf '  would install %s into it with pip\n' "$REPO_DIR"
    printf '  would link %s -> %s\n' "$LAUNCHER" "$VENV/bin/snaktui"
    exit 0
fi

info "creating venv at $VENV"
mkdir -p "$(dirname "$VENV")"
[ -d "$VENV" ] || "$PY" -m venv "$VENV" || die "could not create venv (install python3-venv?)"
info "installing/updating SnakTUI (pip)"
"$VENV/bin/python" -m pip install --disable-pip-version-check --quiet --upgrade "$REPO_DIR" \
    || die "pip install failed"
[ -x "$VENV/bin/snaktui" ] || die "venv has no snaktui launcher"

mkdir -p "$BIN_DIR"
if [ -L "$LAUNCHER" ] && [ "$(readlink "$LAUNCHER")" = "$VENV/bin/snaktui" ]; then
    info "launcher unchanged -> $LAUNCHER"
else
    if [ -e "$LAUNCHER" ] && [ ! -L "$LAUNCHER" ]; then
        bak="$LAUNCHER.bak-$(date +%Y%m%d-%H%M%S)-$$"
        cp -p "$LAUNCHER" "$bak"
        printf '  backup: %s\n' "$bak"
    fi
    ln -sfn "$VENV/bin/snaktui" "$LAUNCHER"
    info "installed launcher -> $LAUNCHER"
fi
mkdir -p "$STATE_DIR"
printf '%s\tsymlink\n' "$LAUNCHER" > "$MANIFEST"
printf '%s\n' "$VENV" > "$VENV_NOTE"

"$VENV/bin/snaktui" --version >/dev/null 2>&1 && info "installed: $("$VENV/bin/snaktui" --version | head -n1)"
case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *) printf 'Add %s to PATH to run snaktui.\n' "$BIN_DIR" ;;
esac
