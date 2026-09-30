"""This Mac's simulators, phone and tool paths, for the Python dev tools (the shell tools use tools/machine.sh).

Reads <repo>/machine.env (copy machine.env.example); an environment variable of the same name wins.
    import machine; machine.get("SIM_A_UDID"); machine.require("PHONE_UDID")
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FILE = os.path.join(REPO_ROOT, "machine.env")


def _load():
    vals = {}
    if os.path.exists(_FILE):
        for line in open(_FILE, encoding="utf-8"):
            s = line.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            k, v = s.split("=", 1)
            v = v.strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                v = v[1:-1]
            vals[k.strip()] = v
    return vals


_VALS = _load()


def get(key, default=None):
    return os.environ.get(key) or _VALS.get(key) or default


def require(key):
    v = get(key)
    if not v:
        sys.exit(f"{key} is not set: cp {REPO_ROOT}/machine.env.example {REPO_ROOT}/machine.env "
                 f"and fill in this Mac's values")
    return v


def slot_udid(slot):
    """The simulator UDID of build slot A or B (tools/slot.sh)."""
    return require(f"SIM_{slot}_UDID")
