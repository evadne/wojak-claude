import bpy
from mathutils import Vector

# All values are exact model units; nothing is rescaled.
BLOCK_X, BLOCK_Y, BLOCK_Z = 32.0, 16.0, 24.0
CAV_CENTRES_X = (-5.0, 5.0)
CAV_CENTRE_Z = 0.0
CAV_W, CAV_H, CAV_DEPTH = 2.4, 6.4, 8.0
PIN_X, PIN_Y, PIN_Z = 2.0, 7.0, 6.0
PIN_CENTRES = (
    ('pin_left', (-5.0, -4.5, 0.0)),
    ('pin_right', (5.0, -4.5, 0.0)),
)


def clear_scene():
    try:
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
    except Exception:
        pass
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for coll in list(bpy.data.collections):
        bpy.data.collections.remove(coll)
    for store in (bpy.data.meshes, bpy.data.curves, bpy.data.lights,
                  bpy.data.cameras, bpy.data.materials):
        for block in list(store):
            if block.users == 0:
                store.remove(block)


def add_quad(verts, faces, idx, want):
    # Append a quad, flipping its winding if needed so the normal follows 'want'.
    idx = list(idx)
    a = Vector(verts[idx[0]])
    b = Vector(verts[idx[1]])
    c = Vector(verts[idx[2]])
    n = (b - a).cross(c - b)
    if n.dot(Vector(want)) < 0.0:
        idx.reverse()
    faces.append(tuple(idx))


def build_socket_mesh(name):
    # Block with two blind cavities built directly as one closed manifold mesh.
    # The front and back faces share an X/Z grid so that no T-junctions occur.
    hx, hy, hz = BLOCK_X / 2.0, BLOCK_Y / 2.0, BLOCK_Z / 2.0
    y_front = -hy
    y_back = hy
    y_end = y_front + CAV_DEPTH

    xs = [-hx]
    for cx in sorted(CAV_CENTRES_X):
        xs.append(cx - CAV_W / 2.0)
        xs.append(cx + CAV_W / 2.0)
    xs.append(hx)
    zs = [-hz, CAV_CENTRE_Z - CAV_H / 2.0, CAV_CENTRE_Z + CAV_H / 2.0, hz]
    nx, nz = len(xs), len(zs)
    holes = set((1 + 2 * k, 1) for k in range(len(CAV_CENTRES_X)))

    verts = []
    for y in (y_front, y_back):
        for j in range(nz):
            for i in range(nx):
                verts.append((xs[i], y, zs[j]))

    def f(i, j):
        return j * nx + i

    def b(i, j):
        return nx * nz + j * nx + i

    faces = []

    # Front face (Y = -8) with the two receptacle openings left open,
    # and the back face (Y = +8) fully closed.
    for j in range(nz - 1):
        for i in range(nx - 1):
            if (i, j) not in holes:
                add_quad(verts, faces,
                         [f(i, j), f(i + 1, j), f(i + 1, j + 1), f(i, j + 1)],
                         (0.0, -1.0, 0.0))
            add_quad(verts, faces,
                     [b(i, j), b(i + 1, j), b(i + 1, j + 1), b(i, j + 1)],
                     (0.0, 1.0, 0.0))

    # Bottom and top faces.
    for i in range(nx - 1):
        add_quad(verts, faces,
                 [f(i, 0), f(i + 1, 0), b(i + 1, 0), b(i, 0)],
                 (0.0, 0.0, -1.0))
        add_quad(verts, faces,
                 [f(i, nz - 1), f(i + 1, nz - 1), b(i + 1, nz - 1), b(i, nz - 1)],
                 (0.0, 0.0, 1.0))

    # Left and right faces.
    for j in range(nz - 1):
        add_quad(verts, faces,
                 [f(0, j), f(0, j + 1), b(0, j + 1), b(0, j)],
                 (-1.0, 0.0, 0.0))
        add_quad(verts, faces,
                 [f(nx - 1, j), f(nx - 1, j + 1), b(nx - 1, j + 1), b(nx - 1, j)],
                 (1.0, 0.0, 0.0))

    # Blind cavities: four walls and an end cap at Y = 0, normals facing the void.
    for (i, j) in sorted(holes):
        ring = [f(i, j), f(i + 1, j), f(i + 1, j + 1), f(i, j + 1)]
        base = len(verts)
        for r in ring:
            verts.append((verts[r][0], y_end, verts[r][2]))
        end = [base + k for k in range(4)]
        cx = (xs[i] + xs[i + 1]) / 2.0
        cz = (zs[j] + zs[j + 1]) / 2.0
        for k in range(4):
            k2 = (k + 1) % 4
            va, vb = ring[k], ring[k2]
            mx = (verts[va][0] + verts[vb][0]) / 2.0
            mz = (verts[va][2] + verts[vb][2]) / 2.0
            add_quad(verts, faces, [va, vb, end[k2], end[k]],
                     (cx - mx, 0.0, cz - mz))
        add_quad(verts, faces, end, (0.0, -1.0, 0.0))

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.validate()
    mesh.update()
    return mesh


def build_box_mesh(name, sx, sy, sz):
    hx, hy, hz = sx / 2.0, sy / 2.0, sz / 2.0
    verts = [(ix * hx, iy * hy, iz * hz)
             for ix in (-1.0, 1.0)
             for iy in (-1.0, 1.0)
             for iz in (-1.0, 1.0)]
    faces = []
    add_quad(verts, faces, [0, 1, 3, 2], (-1.0, 0.0, 0.0))
    add_quad(verts, faces, [4, 5, 7, 6], (1.0, 0.0, 0.0))
    add_quad(verts, faces, [0, 1, 5, 4], (0.0, -1.0, 0.0))
    add_quad(verts, faces, [2, 3, 7, 6], (0.0, 1.0, 0.0))
    add_quad(verts, faces, [0, 2, 6, 4], (0.0, 0.0, -1.0))
    add_quad(verts, faces, [1, 3, 7, 5], (0.0, 0.0, 1.0))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.validate()
    mesh.update()
    return mesh


def make_object(name, mesh, location):
    obj = bpy.data.objects.new(name, mesh)
    obj.location = location
    bpy.context.scene.collection.objects.link(obj)
    obj.name = name
    return obj


def main():
    clear_scene()

    make_object('socket_body', build_socket_mesh('socket_body'), (0.0, 0.0, 0.0))
    for pin_name, centre in PIN_CENTRES:
        make_object(pin_name, build_box_mesh(pin_name, PIN_X, PIN_Y, PIN_Z), centre)

    bpy.context.view_layer.update()

    expected = ['pin_left', 'pin_right', 'socket_body']
    found = sorted(o.name for o in bpy.data.objects)
    if found != expected or any(o.type != 'MESH' for o in bpy.data.objects):
        raise RuntimeError('Unexpected final objects: %r' % (found,))


main()
