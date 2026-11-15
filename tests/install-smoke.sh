#!/data/data/com.termux/files/usr/bin/env bash
# Installer CI: isolated venv -> launcher -> uninstall.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="${TMPDIR:-/tmp}/snaktui-install-smoke.$$"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/home" "$TMP/data" "$TMP/state" "$TMP/prefix"
export HOME="$TMP/home" XDG_DATA_HOME="$TMP/data" XDG_STATE_HOME="$TMP/state"
bash "$ROOT/install.sh" --prefix "$TMP/prefix" --no-menu >/dev/null
"$TMP/prefix/bin/snaktui" --version >/dev/null
test -d "$XDG_DATA_HOME/snaktui/venv"
bash "$ROOT/install.sh" --prefix "$TMP/prefix" --no-menu >/dev/null
bash "$ROOT/install.sh" --uninstall --yes >/dev/null
test ! -e "$TMP/prefix/bin/snaktui"
test ! -d "$XDG_DATA_HOME/snaktui/venv"
echo "installer smoke OK"
