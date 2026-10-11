#!/usr/bin/env python3
"""Self-test for ascii-widget-registry: functional / error-path / extreme-edge."""
import copy
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import awr  # noqa: E402

EXAMPLE = os.path.join(HERE, "registry.example.json")

RESULTS = []
CASES = []


def case(name):
    def deco(fn):
        def wrapper():
            try:
                fn()
                RESULTS.append((name, "PASS", ""))
            except AssertionError as e:
                RESULTS.append((name, "FAIL", str(e)))
            except Exception as e:  # noqa: BLE001
                RESULTS.append((name, "FAIL", f"{type(e).__name__}: {e}"))
        CASES.append(wrapper)
        return wrapper
    return deco


def reg_file(blob):
    td = tempfile.mkdtemp()
    p = os.path.join(td, "registry.json")
    json.dump(blob, open(p, "w", encoding="utf-8"))
    return p


# ---------------- functional ----------------

@case("func/example-registry-validates")
def _():
    errors, warnings = awr.validate_registry(awr.load_registry(EXAMPLE))
    assert errors == [], errors
    assert warnings == [], warnings


@case("func/get-by-id")
def _():
    reg = awr.load_registry(EXAMPLE)
    w = awr.get_widget(reg, "spinner-classic")
    assert w["kind"] == "loader" and len(w["frames"]) == 4


@case("func/search-kind-and-tag")
def _():
    reg = awr.load_registry(EXAMPLE)
    assert len(awr.search(reg, kind="loader")) == 2
    assert len(awr.search(reg, tag="brand")) == 1
    assert awr.search(reg, kind="scene", tag="ocean")[0]["id"] == "wave-small"
    assert awr.search(reg, tag="nonexistent") == []


@case("func/render-frame-wraps-modulo")
def _():
    reg = awr.load_registry(EXAMPLE)
    w = awr.get_widget(reg, "spinner-classic")
    assert awr.render_frame(w, 4) == w["frames"][0] == "|"
    assert awr.render_frame(w, 7) == w["frames"][3]


@case("func/cli-validate-list-get")
def _():
    rc = subprocess.run([sys.executable, "awr.py", "validate", EXAMPLE],
                        capture_output=True, cwd=HERE)
    assert rc.returncode == 0, rc.stderr
    rc2 = subprocess.run([sys.executable, "awr.py", "list", EXAMPLE, "--kind", "loader"],
                         capture_output=True, cwd=HERE)
    assert b"spinner-classic" in rc2.stdout
    rc3 = subprocess.run([sys.executable, "awr.py", "get", EXAMPLE, "spinner-classic",
                          "--frame", "2"], capture_output=True, cwd=HERE)
    assert rc3.stdout.decode().strip() == "-"


# ---------------- error paths ----------------

@case("err/duplicate-widget-id")
def _():
    reg = awr.load_registry(EXAMPLE)
    reg["widgets"].append(copy.deepcopy(reg["widgets"][0]))
    errors, _ = awr.validate_registry(reg)
    assert any("duplicates" in e for e in errors), errors


@case("err/empty-frames")
def _():
    reg = awr.load_registry(EXAMPLE)
    reg["widgets"][0]["frames"] = []
    errors, _ = awr.validate_registry(reg)
    assert any("frames" in e for e in errors)


@case("err/bad-kind")
def _():
    reg = awr.load_registry(EXAMPLE)
    reg["widgets"][0]["kind"] = "gif"
    errors, _ = awr.validate_registry(reg)
    assert any("kind" in e for e in errors)


@case("err/fps-out-of-range")
def _():
    reg = awr.load_registry(EXAMPLE)
    reg["widgets"][0]["fps"] = 120
    errors, _ = awr.validate_registry(reg)
    assert any("fps" in e for e in errors)


@case("err/get-unknown-id-exit-1")
def _():
    rc = subprocess.run([sys.executable, "awr.py", "get", EXAMPLE, "nope"],
                        capture_output=True, cwd=HERE)
    assert rc.returncode == 1, rc.returncode


@case("err/corrupt-registry-json-exit-4")
def _():
    td = tempfile.mkdtemp()
    p = os.path.join(td, "r.json")
    open(p, "w").write("]]]] not json")
    rc = subprocess.run([sys.executable, "awr.py", "validate", p], capture_output=True, cwd=HERE)
    assert rc.returncode == 4, rc.returncode


@case("err/missing-file-exit-3")
def _():
    rc = subprocess.run([sys.executable, "awr.py", "validate", "ghost.json"],
                        capture_output=True, cwd=HERE)
    assert rc.returncode == 3, rc.returncode


# ---------------- extreme edges ----------------

@case("edge/empty-object")
def _():
    errors, _ = awr.validate_registry({})
    assert len(errors) >= 2


@case("edge/huge-registry-800-widgets")
def _():
    reg = awr.load_registry(EXAMPLE)
    base = reg["widgets"][0]
    reg["widgets"] = [dict(base, id=f"w-{i:04d}") for i in range(800)]
    errors, _ = awr.validate_registry(reg)
    assert errors == []
    assert len(awr.search(reg, kind="loader")) == 800


@case("edge/frame-with-control-chars-warns")
def _():
    reg = awr.load_registry(EXAMPLE)
    reg["widgets"][0]["frames"] = ["ok\nframe", "bad\x01frame"]
    errors, warnings = awr.validate_registry(reg)
    assert errors == [] and any("non-ASCII" in w or "control" in w.lower() for w in warnings), (errors, warnings)


@case("edge/empty-string-frame-rejected")
def _():
    reg = awr.load_registry(EXAMPLE)
    reg["widgets"][0]["frames"] = [""]
    errors, _ = awr.validate_registry(reg)
    assert any("non-empty" in e for e in errors)


@case("edge/non-dict-widget-entry")
def _():
    reg = awr.load_registry(EXAMPLE)
    reg["widgets"].append("not a widget")
    errors, _ = awr.validate_registry(reg)
    assert any("must be an object" in e for e in errors)


def main() -> int:
    for fn in CASES:
        fn()
    width = max(len(n) for n, _, _ in RESULTS)
    for name, status, msg in RESULTS:
        print(f"{name:<{width}}  {status}" + (f"  ({msg})" if msg else ""))
    passed = sum(1 for _, s, _ in RESULTS if s == "PASS")
    print(f"\n{passed}/{len(RESULTS)} passed")
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
