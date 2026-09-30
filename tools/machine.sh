# tools/machine.sh: SOURCED by the dev tools. Finds the repo root (the folder holding machine.env.example) from
# $MACHINE_FROM (default: the current folder), sets REPO_ROOT, and loads <repo>/machine.env: this Mac's simulators,
# phone and tool paths. A variable already set in the environment wins over the file.
#   MACHINE_FROM="$ROOT" . "$ROOT/../../tools/machine.sh"; machine_require SIM_A_UDID ...
REPO_ROOT="$(cd "${MACHINE_FROM:-.}" && while [ ! -f machine.env.example ] && [ "$PWD" != / ]; do cd ..; done; pwd)"
for _k in SIM_A_UDID SIM_A_NAME SIM_B_UDID SIM_B_NAME PHONE_UDID PHONE_DEVICE XCODEGEN ART_PY; do
  eval "_cur=\${$_k:-}"
  if [ -z "$_cur" ] && [ -f "$REPO_ROOT/machine.env" ]; then
    _v=$(sed -n "s/^$_k=//p" "$REPO_ROOT/machine.env" | tail -1 | sed -e 's/^["'\'']//' -e 's/["'\'']$//')
    [ -n "$_v" ] && eval "$_k=\$_v"
  fi
done
unset _k _cur _v
# machine_require KEY...: stop with a clear message when this Mac's value is missing.
machine_require() {
  for _k in "$@"; do
    eval "_cur=\${$_k:-}"
    if [ -z "$_cur" ]; then
      echo "$_k is not set: cp $REPO_ROOT/machine.env.example $REPO_ROOT/machine.env and fill in this Mac's values" >&2
      exit 78
    fi
  done
}
