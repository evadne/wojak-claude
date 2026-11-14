"""Run inside Blender after reviewing a generated script; render fixed views."""

import argparse
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    record = json.loads(args.result.read_text())
    if record.get("status") != "completed":
        raise ValueError("The model call did not complete")
    answer = record["parsed_answer"]
    source = answer["script"]
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "generated.py").write_text(source + "\n")
    exec(compile(source, str(args.out / "generated.py"), "exec"), {"__name__": "__main__"})
    bpy.context.view_layer.update()
    visible = [o for o in bpy.context.scene.objects if o.type in {"MESH", "CURVE", "SURFACE", "META", "FONT"} and not o.hide_render]
    if not visible:
        raise ValueError("No visible geometry")
    depsgraph = bpy.context.evaluated_depsgraph_get()
    points = [obj.matrix_world @ Vector(corner) for original in visible
              for obj in [original.evaluated_get(depsgraph)] for corner in obj.bound_box]
    lower = Vector(tuple(min(p[i] for p in points) for i in range(3)))
    upper = Vector(tuple(max(p[i] for p in points) for i in range(3)))
    centre = (lower + upper) / 2
    extent = max(upper - lower)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 900
    scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    shading = scene.display.shading
    shading.light = "STUDIO"
    shading.color_type = "SINGLE"
    shading.single_color = (0.72, 0.72, 0.72)
    shading.background_type = "WORLD"
    shading.show_shadows = True
    shading.show_cavity = True
    shading.cavity_type = "BOTH"
    shading.show_specular_highlight = True
    scene.world.color = (1, 1, 1)
    scene.view_settings.view_transform = "Standard"
    camera_data = bpy.data.cameras.new("StudyCamera")
    camera = bpy.data.objects.new("StudyCamera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = extent * 1.25
    for name, direction in [("front", Vector((0, -3, 0.15))), ("oblique", Vector((2, -3, 1)))]:
        camera.location = centre + direction.normalized() * extent * 3
        camera.rotation_euler = (centre - camera.location).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = str((args.out / (name + ".png")).resolve())
        bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str((args.out / "scene.blend").resolve()))
    (args.out / "render-metadata.json").write_text(json.dumps({
        "bounds_min": list(lower), "bounds_max": list(upper),
        "geometry_object_count": len(visible), "blender_version": bpy.app.version_string,
        "wrapper": "scripts/render_generated.py", "geometry_corrections": [],
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()
