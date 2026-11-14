"""Blender: reveal occluded geometry by hiding named objects for one view."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scene", type=Path)
    parser.add_argument("--hide", nargs="+", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    path = args.scene.resolve()
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(path))
    for name in args.hide:
        bpy.data.objects[name].hide_render = True
    bpy.context.scene.render.filepath = str(args.out.resolve())
    bpy.ops.render.render(write_still=True)
    if hashlib.sha256(path.read_bytes()).hexdigest() != before:
        raise ValueError("Retained scene was changed")
    args.out.with_suffix(".json").write_text(json.dumps({
        "purpose": "Derived inspection view with named occluding objects hidden; retained geometry and camera unchanged",
        "scene": str(path.relative_to(ROOT)), "scene_sha256": before,
        "hidden_objects": args.hide, "geometry_changed": False, "retained_scene_saved": False,
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()
