#!/usr/bin/env python3
"""ascii-widget-registry (awr) -- JSON registry spec + distributor for
ASCII/text animation assets.

A registry file lists widgets (loaders, scenes, charts, logos, banners) as
data: frames, fps, tags. awr validates the registry against the spec and
serves widgets by id / kind / tag, so agents and static-site generators can
consume ASCII art without importing anyone's framework.

Pure stdlib. Zero rendering dependencies: a widget is just frames of text.
"""
from __future__ import annotations

import argparse
import json
import sys
import time

VERSION = "0.1.1"
SCHEMA_ID = "awr/1"
KINDS = ("loader", "scene", "chart", "logo", "banner")
FPS_MIN, FPS_MAX = 1, 60
MAX_FRAME_LINES = 200
MAX_FRAMES = 1000


def load_registry(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def validate_registry(reg: dict) -> tuple:
    """Return (errors, warnings)."""
    errors, warnings = [], []

    def need(cond, msg):
        if not cond:
            errors.append(msg)

    if not isinstance(reg, dict):
        return [f"registry root must be an object, got {type(reg).__name__}"], []
    need(reg.get("schema") == SCHEMA_ID, f"schema field must be {SCHEMA_ID!r}")
    widgets = reg.get("widgets")
    need(isinstance(widgets, list) and len(widgets) > 0,
         "widgets must be a non-empty list")
    if not isinstance(widgets, list):
        return errors, warnings
    seen = set()
    for i, w in enumerate(widgets):
        if not isinstance(w, dict):
            errors.append(f"widgets[{i}] must be an object")
            continue
        wid = w.get("id")
        need(isinstance(wid, str) and re_id_ok(wid),
             f"widgets[{i}].id must match [a-z0-9][a-z0-9-]*, got {wid!r}")
        if wid in seen:
            errors.append(f"widgets[{i}].id duplicates {wid!r}")
        seen.add(wid)
        need(w.get("kind") in KINDS,
             f"widgets[{i}].kind must be one of {KINDS}, got {w.get('kind')!r}")
        frames = w.get("frames")
        need(isinstance(frames, list) and len(frames) > 0,
             f"widgets[{i}].frames must be a non-empty list of strings")
        if isinstance(frames, list):
            if len(frames) > MAX_FRAMES:
                errors.append(f"widgets[{i}] has {len(frames)} frames > max {MAX_FRAMES}")
            for j, fr in enumerate(frames):
                if not isinstance(fr, str) or fr == "":
                    errors.append(f"widgets[{i}].frames[{j}] must be a non-empty string")
                    continue
                if fr.count("\n") + 1 > MAX_FRAME_LINES:
                    errors.append(f"widgets[{i}].frames[{j}] exceeds {MAX_FRAME_LINES} lines")
                bad = sorted({ch for ch in fr if (ord(ch) > 126 and ch not in "\u2800\u2588\u2592\u2591\u256d\u256e\u256f\u2570\u256d") or (ord(ch) < 32 and ch != "\n")})
                if bad:
                    warnings.append(
                        f"widgets[{i}].frames[{j}] uses non-ASCII chars {bad!r}: "
                        "may break on ASCII-only terminals")
        fps = w.get("fps", 8)
        need(isinstance(fps, int) and FPS_MIN <= fps <= FPS_MAX,
             f"widgets[{i}].fps must be int in [{FPS_MIN},{FPS_MAX}], got {fps!r}")
        tags = w.get("tags", [])
        need(isinstance(tags, list) and all(isinstance(t, str) for t in tags),
             f"widgets[{i}].tags must be a list of strings")
    return errors, warnings


def re_id_ok(s: str) -> bool:
    import re
    return bool(re.match(r"^[a-z0-9][a-z0-9-]*$", s))


def get_widget(reg: dict, widget_id: str) -> dict:
    for w in reg.get("widgets", []):
        if isinstance(w, dict) and w.get("id") == widget_id:
            return w
    raise KeyError(f"no widget with id {widget_id!r}")


def search(reg: dict, kind: str | None = None, tag: str | None = None) -> list:
    out = []
    for w in reg.get("widgets", []):
        if not isinstance(w, dict):
            continue
        if kind and w.get("kind") != kind:
            continue
        if tag and tag not in (w.get("tags") or []):
            continue
        out.append(w)
    return out


def render_frame(widget: dict, index: int) -> str:
    frames = widget["frames"]
    return frames[index % len(frames)]


def preview(widget: dict, cycles: int = 1, delay: float = 0.12) -> None:
    """Print one full frame cycle (blocking, tiny). For terminals only."""
    frames = widget["frames"]
    n = min(len(frames) * cycles, MAX_FRAMES)
    for k in range(n):
        print("\n" * 0 + render_frame(widget, k), flush=True)
        if k < n - 1:
            time.sleep(delay)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cmd_validate(args) -> int:
    reg = load_registry(args.file)
    errors, warnings = validate_registry(reg)
    for w in warnings:
        print(f"warning: {w}")
    if errors:
        for e in errors:
            print(f"error: {e}", file=sys.stderr)
        return 1
    n = len(reg["widgets"])
    print(f"valid {SCHEMA_ID} registry ({n} widget(s))")
    return 0


def _cmd_list(args) -> int:
    reg = load_registry(args.file)
    found = search(reg, kind=args.kind, tag=args.tag)
    if not found:
        print("(no widgets match)")
    for w in found:
        tags = ",".join(w.get("tags", []))
        print(f"{w['id']:<24} {w['kind']:<7} {len(w['frames']):>3} frames  fps={w.get('fps', 8):<3} {tags}")
    return 0


def _cmd_get(args) -> int:
    reg = load_registry(args.file)
    try:
        w = get_widget(reg, args.id)
    except KeyError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if args.frame is not None:
        print(render_frame(w, args.frame))
    elif args.meta:
        print(json.dumps({k: v for k, v in w.items() if k != "frames"},
                         ensure_ascii=False, indent=2))
    else:
        print(f"# {w['id']} ({w['kind']}, {len(w['frames'])} frames)")
        preview(w)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="awr", description="ASCII widget registry")
    p.add_argument("--version", action="version", version=VERSION)
    sub = p.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate", help="validate a registry file")
    v.add_argument("file")
    v.set_defaults(func=_cmd_validate)
    l = sub.add_parser("list", help="list widgets, filter by kind/tag")
    l.add_argument("file")
    l.add_argument("--kind", choices=KINDS)
    l.add_argument("--tag")
    l.set_defaults(func=_cmd_list)
    g = sub.add_parser("get", help="fetch one widget")
    g.add_argument("file")
    g.add_argument("id")
    g.add_argument("--frame", type=int, help="print a single frame (mod frame count)")
    g.add_argument("--meta", action="store_true", help="print metadata without frames")
    g.set_defaults(func=_cmd_get)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except FileNotFoundError as e:
        print(f"error: file not found: {e.filename}", file=sys.stderr)
        return 3
    except json.JSONDecodeError as e:
        print(f"error: not valid JSON: {e}", file=sys.stderr)
        return 4
    except OSError as e:
        print(f"error: {e}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    sys.exit(main())
