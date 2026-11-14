"""Blender: measure retained prongs intersecting retained socket plastic."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

import bmesh
import bpy

ROOT = Path(__file__).resolve().parents[1]


def mesh_stats(obj):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        bm.transform(obj.matrix_world)
        return {
            "volume": abs(bm.calc_volume(signed=True)),
            "closed_manifold": bool(bm.faces) and all(edge.is_manifold for edge in bm.edges),
            "vertices": len(bm.verts), "faces": len(bm.faces),
        }
    finally:
        bm.free()
        evaluated.to_mesh_clear()


def evaluated_copy(obj, name):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph), depsgraph=depsgraph)
    copy = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(copy)
    copy.matrix_world = obj.matrix_world.copy()
    return copy


def overlap(body, prong, tolerance):
    bpy.context.view_layer.update()
    body_stats = mesh_stats(body)
    prong_stats = mesh_stats(prong)
    if not body_stats["closed_manifold"] or not prong_stats["closed_manifold"]:
        raise ValueError("Closed manifold operands required: " + body.name + ", " + prong.name)
    a = evaluated_copy(body, "AuditBody")
    b = evaluated_copy(prong, "AuditProng")
    try:
        modifier = a.modifiers.new("AuditIntersection", "BOOLEAN")
        modifier.operation = "INTERSECT"
        modifier.solver = "EXACT"
        modifier.object = b
        bpy.context.view_layer.update()
        intersection = mesh_stats(a)
        return {
            "body": body.name, "prong": prong.name,
            "body_volume": body_stats["volume"], "prong_volume": prong_stats["volume"],
            "intersection_volume": intersection["volume"],
            "fraction_of_prong_inside_plastic": intersection["volume"] / prong_stats["volume"],
            "plastic_penetration": intersection["volume"] > tolerance,
            "operand_closed_manifold": True,
        }
    finally:
        for obj in [a, b]:
            mesh = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            bpy.data.meshes.remove(mesh)


def cube(name, centre, dimensions):
    bpy.ops.mesh.primitive_cube_add(size=1, location=centre)
    obj = bpy.context.object
    obj.name = name
    obj.scale = dimensions
    bpy.context.view_layer.update()
    return obj


def calibrate(tolerance):
    controls = []
    for label, cavity_depth, expected in [("solid_block", 0, 84.0), ("shallow_recess", 2, 60.0), ("clear_receptacle", 8, 0.0)]:
        for obj in list(bpy.data.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        body = cube("ControlBody", (0, 0, 0), (32, 16, 24))
        if cavity_depth:
            for x in [-5, 5]:
                # Extend outside the front face to avoid a coplanar cutter.
                back = -8 + cavity_depth
                cutter = cube("ControlCutter", (x, (-8.2 + back) / 2, 0), (2.4, back + 8.2, 6.4))
                modifier = body.modifiers.new("ControlPocket", "BOOLEAN")
                modifier.operation = "DIFFERENCE"
                modifier.solver = "EXACT"
                modifier.object = cutter
                bpy.context.view_layer.objects.active = body
                bpy.ops.object.modifier_apply(modifier=modifier.name)
                bpy.data.objects.remove(cutter, do_unlink=True)
        prongs = [cube("ControlProng" + str(i), (x, -4.5, 0), (2, 7, 6)) for i, x in enumerate([-5, 5])]
        measurements = [overlap(body, prong, tolerance) for prong in prongs]
        passed = all(abs(m["intersection_volume"] - expected) < tolerance for m in measurements)
        controls.append({"control": label, "expected_intersection_volume_per_prong": expected,
                         "passed": passed, "measurements": measurements})
        if not passed:
            raise ValueError("Intersection calibration failed: " + label)
    return controls


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("protocol", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    protocol = json.loads(args.protocol.read_text())
    tolerance = protocol["volume_tolerance"]
    report = {
        "method": "Exact Boolean intersection of evaluated meshes in their retained placements; no source geometry repair or saving",
        "units": "Blender model units cubed, not physical millimetres",
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "protocol_sha256": hashlib.sha256(args.protocol.read_bytes()).hexdigest(),
        "blender_version": bpy.app.version_string,
        "volume_tolerance": tolerance,
        "calibration": calibrate(tolerance),
        "cases": [],
    }
    for case in protocol["cases"]:
        path = ROOT / case["scene"]
        before = hashlib.sha256(path.read_bytes()).hexdigest()
        bpy.ops.wm.open_mainfile(filepath=str(path))
        measurements = [overlap(bpy.data.objects[case["body"]], bpy.data.objects[name], tolerance) for name in case["prongs"]]
        after = hashlib.sha256(path.read_bytes()).hexdigest()
        if before != after:
            raise ValueError("Audit changed the retained scene")
        report["cases"].append({
            "id": case["id"], "scene": case["scene"], "scene_sha256": before,
            "source_geometry_changed": False, "measurements": measurements,
            "all_prongs_clear_of_body": all(not m["plastic_penetration"] for m in measurements),
        })
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"controls_passed": len(report["calibration"]), "cases": len(report["cases"]),
                      "cases_with_plastic_penetration": sum(not c["all_prongs_clear_of_body"] for c in report["cases"])}))


if __name__ == "__main__":
    main()
