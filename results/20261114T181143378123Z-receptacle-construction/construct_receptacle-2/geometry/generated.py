import bpy

# ---------------------------------------------------------------------------
# Parameters (exact model units, no rescaling)
# ---------------------------------------------------------------------------
BLOCK_X, BLOCK_Y, BLOCK_Z = 32.0, 16.0, 24.0
CAV_W, CAV_H, CAV_D = 2.4, 6.4, 8.0
CAV_CENTRES_X = (-5.0, 5.0)
CAV_CENTRE_Z = 0.0
PIN_X, PIN_Y, PIN_Z = 2.0, 7.0, 6.0
PIN_CENTRES = {
    'pin_left': (-5.0, -4.5, 0.0),
    'pin_right': (5.0, -4.5, 0.0),
}


def clear_scene():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for coll in list(bpy.data.collections):
        bpy.data.collections.remove(coll)
    for blocks in (bpy.data.meshes, bpy.data.curves, bpy.data.cameras,
                   bpy.data.lights, bpy.data.materials):
        for block in list(blocks):
            blocks.remove(block)


def check_closed(mesh):
    # Every edge must be shared by exactly two faces (closed manifold shell).
    counts = {}
    for poly in mesh.polygons:
        for key in poly.edge_keys:
            counts[key] = counts.get(key, 0) + 1
    bad = [k for k, c in counts.items() if c != 2]
    if bad:
        raise RuntimeError('Mesh %s is not a closed manifold (%d bad edges)' % (mesh.name, len(bad)))


def make_mesh_object(name, verts, faces, location=(0.0, 0.0, 0.0)):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.validate()
    mesh.update()
    check_closed(mesh)
    obj = bpy.data.objects.new(name, mesh)
    obj.location = location
    bpy.context.scene.collection.objects.link(obj)
    return obj


def box_geometry(sx, sy, sz):
    hx, hy, hz = sx / 2.0, sy / 2.0, sz / 2.0
    verts = [
        (-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz),
        (-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz),
    ]
    faces = [
        (0, 3, 2, 1),  # bottom (-Z)
        (4, 5, 6, 7),  # top (+Z)
        (0, 1, 5, 4),  # front (-Y)
        (1, 2, 6, 5),  # right (+X)
        (2, 3, 7, 6),  # back (+Y)
        (3, 0, 4, 7),  # left (-X)
    ]
    return verts, faces


def socket_geometry():
    # Block built directly as one closed shell with two real blind cavities.
    hx, hy, hz = BLOCK_X / 2.0, BLOCK_Y / 2.0, BLOCK_Z / 2.0
    y_front = -hy
    y_back = hy
    y_cav = y_front + CAV_D  # cavity floor, Y = 0

    xs = [-hx]
    for cx in sorted(CAV_CENTRES_X):
        xs.append(cx - CAV_W / 2.0)
        xs.append(cx + CAV_W / 2.0)
    xs.append(hx)
    zs = [-hz, CAV_CENTRE_Z - CAV_H / 2.0, CAV_CENTRE_Z + CAV_H / 2.0, hz]

    nx = len(xs)  # 6
    nz = len(zs)  # 4

    verts = []
    for z in zs:
        for x in xs:
            verts.append((x, y_front, z))
    for z in zs:
        for x in xs:
            verts.append((x, y_back, z))

    def fv(i, j):
        return i + nx * j

    def bv(i, j):
        return nx * nz + i + nx * j

    holes = [(1, 1), (3, 1)]  # (column, row) cells left open on the front face
    faces = []

    # Front face (-Y) with the two openings omitted
    for j in range(nz - 1):
        for i in range(nx - 1):
            if (i, j) in holes:
                continue
            faces.append((fv(i, j), fv(i + 1, j), fv(i + 1, j + 1), fv(i, j + 1)))

    # Back face (+Y)
    for j in range(nz - 1):
        for i in range(nx - 1):
            faces.append((bv(i, j), bv(i, j + 1), bv(i + 1, j + 1), bv(i + 1, j)))

    # Top (+Z) and bottom (-Z)
    jt = nz - 1
    for i in range(nx - 1):
        faces.append((fv(i, jt), fv(i + 1, jt), bv(i + 1, jt), bv(i, jt)))
        faces.append((fv(i, 0), bv(i, 0), bv(i + 1, 0), fv(i + 1, 0)))

    # Left (-X) and right (+X)
    ir = nx - 1
    for j in range(nz - 1):
        faces.append((fv(0, j), fv(0, j + 1), bv(0, j + 1), bv(0, j)))
        faces.append((fv(ir, j), bv(ir, j), bv(ir, j + 1), fv(ir, j + 1)))

    # Cavities: four walls plus an end cap at Y = 0, normals facing into the void
    for (c, r) in holes:
        a = fv(c, r)
        b = fv(c + 1, r)
        cc = fv(c + 1, r + 1)
        d = fv(c, r + 1)
        base = len(verts)
        verts.append((xs[c], y_cav, zs[r]))
        verts.append((xs[c + 1], y_cav, zs[r]))
        verts.append((xs[c + 1], y_cav, zs[r + 1]))
        verts.append((xs[c], y_cav, zs[r + 1]))
        a2, b2, c2, d2 = base, base + 1, base + 2, base + 3
        faces.append((a, b, b2, a2))      # cavity lower wall
        faces.append((b, cc, c2, b2))     # cavity +X wall
        faces.append((cc, d, d2, c2))     # cavity upper wall
        faces.append((d, a, a2, d2))      # cavity -X wall
        faces.append((a2, b2, c2, d2))    # blind end at Y = 0

    return verts, faces


def main():
    clear_scene()

    s_verts, s_faces = socket_geometry()
    make_mesh_object('socket_body', s_verts, s_faces, (0.0, 0.0, 0.0))

    p_verts, p_faces = box_geometry(PIN_X, PIN_Y, PIN_Z)
    for name in ('pin_left', 'pin_right'):
        make_mesh_object(name, p_verts, p_faces, PIN_CENTRES[name])

    names = sorted(o.name for o in bpy.data.objects if o.type == 'MESH')
    if names != ['pin_left', 'pin_right', 'socket_body'] or len(bpy.data.objects) != 3:
        raise RuntimeError('Unexpected final objects: %s' % names)

    bpy.context.view_layer.update()


main()
