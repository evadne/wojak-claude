import bpy
import math
from mathutils import Vector, Quaternion


def clear_scene():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.curves, bpy.data.materials):
        for blk in list(coll):
            if blk.users == 0:
                coll.remove(blk)


clear_scene()
scene = bpy.context.scene
root = scene.collection
IDQ = Quaternion((1.0, 0.0, 0.0, 0.0))


def make_mat(name, rgb, rough=0.6, metallic=0.0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (rgb[0], rgb[1], rgb[2], 1.0)
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = getattr(m, 'node_tree', None)
    if nt is not None:
        for n in nt.nodes:
            if n.type == 'BSDF_PRINCIPLED':
                try:
                    n.inputs['Base Color'].default_value = (rgb[0], rgb[1], rgb[2], 1.0)
                    n.inputs['Roughness'].default_value = rough
                    n.inputs['Metallic'].default_value = metallic
                except Exception:
                    pass
    return m


M_SKIN = make_mat('Skin', (0.95, 0.91, 0.84))
M_STRIP = make_mat('StripBody', (0.88, 0.90, 0.93), 0.45)
M_PLATE = make_mat('SocketPlate', (0.99, 0.99, 0.97), 0.4)
M_DARK = make_mat('Dark', (0.02, 0.02, 0.02), 0.7)
M_CABLE = make_mat('Cable', (0.80, 0.82, 0.85), 0.5)
M_PLUG = make_mat('Plug', (0.93, 0.94, 0.96), 0.45)
M_METAL = make_mat('Prong', (0.78, 0.72, 0.50), 0.3, 1.0)
M_TEAR = make_mat('Tear', (0.10, 0.50, 0.95), 0.2)
M_WHITE = make_mat('EyeWhite', (1.0, 1.0, 1.0), 0.4)


def add_mesh(name, verts, faces, mat, loc=(0.0, 0.0, 0.0), rot=None, smooth=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    me.update()
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    root.objects.link(ob)
    ob.location = Vector(loc)
    ob.rotation_mode = 'QUATERNION'
    ob.rotation_quaternion = rot if rot is not None else IDQ
    return ob


def sphere(name, center, radii, mat, rot=None, segs=32, rings=16, floor=None):
    c = Vector(center)
    verts = [Vector((0.0, 0.0, radii[2]))]
    for i in range(1, rings):
        th = math.pi * i / rings
        for j in range(segs):
            ph = 2.0 * math.pi * j / segs
            verts.append(Vector((radii[0] * math.sin(th) * math.cos(ph), radii[1] * math.sin(th) * math.sin(ph), radii[2] * math.cos(th))))
    verts.append(Vector((0.0, 0.0, -radii[2])))
    last = len(verts) - 1
    if floor is not None:
        for v in verts:
            if v.z + c.z < floor:
                v.z = floor - c.z
    faces = []
    for j in range(segs):
        faces.append((0, 1 + j, 1 + (j + 1) % segs))
    for i in range(rings - 2):
        for j in range(segs):
            a = 1 + i * segs + j
            b = 1 + (i + 1) * segs + j
            cc = 1 + (i + 1) * segs + (j + 1) % segs
            d = 1 + i * segs + (j + 1) % segs
            faces.append((a, b, cc, d))
    base = 1 + (rings - 2) * segs
    for j in range(segs):
        faces.append((base + j, last, base + (j + 1) % segs))
    return add_mesh(name, verts, faces, mat, c, rot, True)


def frustum(name, center, r1, r2, depth, mat, rot=None, segs=24, smooth=True):
    if not isinstance(r1, tuple):
        r1 = (r1, r1)
    if not isinstance(r2, tuple):
        r2 = (r2, r2)
    verts = []
    for j in range(segs):
        a = 2.0 * math.pi * j / segs
        verts.append(Vector((r1[0] * math.cos(a), r1[1] * math.sin(a), -depth / 2.0)))
    for j in range(segs):
        a = 2.0 * math.pi * j / segs
        verts.append(Vector((r2[0] * math.cos(a), r2[1] * math.sin(a), depth / 2.0)))
    faces = []
    for j in range(segs):
        faces.append((j, (j + 1) % segs, segs + (j + 1) % segs, segs + j))
    faces.append(tuple(reversed(range(segs))))
    faces.append(tuple(range(segs, 2 * segs)))
    return add_mesh(name, verts, faces, mat, center, rot, smooth)


def box(name, center, size, mat, rot=None, bevel=0.0):
    hx, hy, hz = size[0] / 2.0, size[1] / 2.0, size[2] / 2.0
    verts = [(-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz), (-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz)]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    ob = add_mesh(name, verts, faces, mat, center, rot, False)
    if bevel > 0.0:
        try:
            mod = ob.modifiers.new('Bevel', 'BEVEL')
            mod.width = bevel
            mod.segments = 3
        except Exception:
            pass
    return ob


def tube(name, pts, radius, mat, sides=12, samples=8):
    pts = [Vector(p) for p in pts]
    P = [pts[0]] + pts + [pts[-1]]
    path = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for s in range(samples):
            t = s / samples
            q = 0.5 * ((2.0 * p1) + (p2 - p0) * t + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t * t + (3.0 * p1 - p0 - 3.0 * p2 + p3) * t * t * t)
            path.append(q)
    path.append(P[-2].copy())
    n_pts = len(path)
    tangents = []
    for i in range(n_pts):
        a = path[max(i - 1, 0)]
        b = path[min(i + 1, n_pts - 1)]
        d = b - a
        if d.length < 1e-9:
            d = Vector((0.0, 0.0, 1.0))
        tangents.append(d.normalized())
    t0 = tangents[0]
    ref = Vector((0.0, 0.0, 1.0)) if abs(t0.z) < 0.9 else Vector((1.0, 0.0, 0.0))
    nrm = (ref - t0 * ref.dot(t0)).normalized()
    verts = []
    for i in range(n_pts):
        t = tangents[i]
        nn = nrm - t * nrm.dot(t)
        if nn.length < 1e-6:
            ref = Vector((0.0, 0.0, 1.0)) if abs(t.z) < 0.9 else Vector((1.0, 0.0, 0.0))
            nn = ref - t * ref.dot(t)
        nrm = nn.normalized()
        bn = t.cross(nrm)
        for j in range(sides):
            a = 2.0 * math.pi * j / sides
            verts.append(path[i] + radius * (math.cos(a) * nrm + math.sin(a) * bn))
    faces = []
    for i in range(n_pts - 1):
        for j in range(sides):
            faces.append((i * sides + j, i * sides + (j + 1) % sides, (i + 1) * sides + (j + 1) % sides, (i + 1) * sides + j))
    faces.append(tuple(reversed(range(sides))))
    faces.append(tuple(range((n_pts - 1) * sides, n_pts * sides)))
    return add_mesh(name, verts, faces, mat, (0.0, 0.0, 0.0), None, True)


# ---------------- body ----------------
sphere('Torso', (-8.0, 2.0, 4.0), (32.0, 15.0, 17.0), M_SKIN, segs=40, rings=20, floor=0.0)
sphere('ShoulderLeft', (-26.0, 2.0, 8.0), (11.0, 11.0, 12.0), M_SKIN, floor=0.0)
frustum('Neck', (-3.0, 1.0, 18.0), (11.0, 10.0), (8.5, 8.0), 14.0, M_SKIN, segs=32)

# ---------------- head ----------------
HC = Vector((0.0, 0.0, 33.0))
HR = Vector((24.0, 18.0, 17.5))
sphere('Head', HC, (HR.x, HR.y, HR.z), M_SKIN, segs=48, rings=24)


def head_pt(x, z, off=0.0):
    dx = (x - HC.x) / HR.x
    dz = (z - HC.z) / HR.z
    s = max(1.0 - dx * dx - dz * dz, 0.02)
    y = HC.y - HR.y * math.sqrt(s)
    p = Vector((x, y, z))
    n = Vector(((p.x - HC.x) / (HR.x * HR.x), (p.y - HC.y) / (HR.y * HR.y), (p.z - HC.z) / (HR.z * HR.z))).normalized()
    return p + n * off, n


def face_rot(n, roll=0.0):
    return n.to_track_quat('-Y', 'Z') @ Quaternion((0.0, 1.0, 0.0), roll)


# ---------------- face ----------------
eyes = [(4.7, 35.9, -0.28), (12.2, 37.6, 0.28)]
for idx, (ex, ez, roll) in enumerate(eyes):
    p, n = head_pt(ex, ez, 0.2)
    sphere('EyeWhite_%d' % idx, p, (2.3, 0.7, 1.4), M_WHITE, rot=face_rot(n, roll * 0.3), segs=20, rings=10)
    p, n = head_pt(ex + 0.3, ez - 0.1, 0.75)
    sphere('Pupil_%d' % idx, p, (0.95, 0.5, 0.95), M_DARK, rot=face_rot(n), segs=16, rings=8)
    p, n = head_pt(ex, ez + 2.4, 0.3)
    box('Brow_%d' % idx, p, (4.4, 0.7, 0.75), M_DARK, rot=face_rot(n, roll))
    p, n = head_pt(ex, ez - 1.75, 0.2)
    box('EyeBag_%d' % idx, p, (3.4, 0.4, 0.3), M_DARK, rot=face_rot(n, -roll * 0.4))

p, n = head_pt(8.6, 33.6, 0.6)
sphere('Nose', p, (1.2, 1.6, 2.4), M_SKIN, rot=face_rot(n), segs=16, rings=10)
p, n = head_pt(8.5, 31.3, 0.25)
box('NoseLine', p, (2.2, 0.45, 0.4), M_DARK, rot=face_rot(n))

p, n = head_pt(7.8, 29.3, 0.25)
box('Mouth', p, (4.4, 0.5, 0.55), M_DARK, rot=face_rot(n, -0.06))
p, n = head_pt(5.1, 28.8, 0.25)
box('MouthCornerL', p, (1.7, 0.5, 0.5), M_DARK, rot=face_rot(n, -0.55))
p, n = head_pt(10.5, 28.9, 0.25)
box('MouthCornerR', p, (1.7, 0.5, 0.5), M_DARK, rot=face_rot(n, 0.55))

streams = [(4.0, 34.3, 3.6, 27.5), (5.8, 34.3, 6.1, 30.5), (11.3, 35.9, 10.9, 24.5), (13.2, 35.9, 13.7, 21.0)]
for idx, (x0, z0, x1, z1) in enumerate(streams):
    pts = []
    steps = 7
    for k in range(steps + 1):
        f = k / steps
        x = x0 + (x1 - x0) * f + 0.2 * math.sin(k * 1.7)
        z = z0 + (z1 - z0) * f
        q, _n = head_pt(x, z, 0.3)
        pts.append(q)
    tube('Tear_%d' % idx, pts, 0.42, M_TEAR, sides=8, samples=4)
    sphere('TearDrop_%d' % idx, pts[-1], (0.75, 0.6, 0.95), M_TEAR, segs=12, rings=8)

# ---------------- power strip (grows out of the head) ----------------
TILT = math.radians(8.0)
RQ = Quaternion((0.0, 1.0, 0.0), TILT)
SC = Vector((13.0, 0.0, 66.0))
QX90 = Quaternion((1.0, 0.0, 0.0), math.radians(90.0))
RQY = RQ @ QX90
HALF_D = 4.0
HALF_L = 22.0


def sloc(x, y, z):
    return SC + RQ @ Vector((x, y, z))


# skin flare blending the head up into the strip
frustum('NeckFlare', sloc(0.0, 0.0, -18.5), (13.0, 8.0), (7.8, 4.5), 11.0, M_SKIN, rot=RQ, segs=32)

box('PowerStrip', sloc(0.0, 0.0, 0.0), (15.0, 2.0 * HALF_D, 2.0 * HALF_L), M_STRIP, rot=RQ, bevel=1.4)

SOCKET_Z = [13.0, 3.0, -7.5]
PLUG_SOCKET = 2
for idx, sz in enumerate(SOCKET_Z):
    box('SocketPlate_%d' % idx, sloc(0.0, -HALF_D - 0.1, sz), (9.0, 0.4, 8.6), M_PLATE, rot=RQ, bevel=0.15)
    if idx != PLUG_SOCKET:
        box('SlotL_%d' % idx, sloc(-1.7, -HALF_D - 0.35, sz + 0.9), (0.7, 0.3, 2.6), M_DARK, rot=RQ)
        box('SlotR_%d' % idx, sloc(1.7, -HALF_D - 0.35, sz + 0.9), (0.7, 0.3, 2.6), M_DARK, rot=RQ)
        frustum('Ground_%d' % idx, sloc(0.0, -HALF_D - 0.35, sz - 1.9), 0.85, 0.85, 0.3, M_DARK, rot=RQY, segs=16)

# strain relief on top of the strip where the cable leaves
frustum('TopRelief', sloc(0.0, 0.0, HALF_L + 2.0), 2.8, 1.9, 4.0, M_STRIP, rot=RQ, segs=20)
for k, (rz, rr) in enumerate([(0.8, 3.2), (2.0, 2.9), (3.2, 2.6)]):
    frustum('ReliefRib_%d' % k, sloc(0.0, 0.0, HALF_L + rz), rr, rr, 0.7, M_STRIP, rot=RQ, segs=20)

# ---------------- plug seated in the lowest socket, axis = socket normal (-Y) ----------------
PZ = SOCKET_Z[PLUG_SOCKET]
face_y = -HALF_D - 0.3
box('PlugFlange', sloc(0.0, face_y - 0.5, PZ), (8.4, 1.0, 7.8), M_PLUG, rot=RQ, bevel=0.3)
box('PlugBody', sloc(0.0, face_y - 1.0 - 3.0, PZ), (7.4, 6.0, 6.8), M_PLUG, rot=RQ, bevel=1.0)
plug_back_y = face_y - 7.0
frustum('PlugRelief', sloc(0.0, plug_back_y - 2.25, PZ), 2.7, 1.7, 4.5, M_PLUG, rot=RQY, segs=20)
box('ProngL', sloc(-1.6, -3.4, PZ + 0.8), (0.35, 2.6, 1.7), M_METAL, rot=RQ)
box('ProngR', sloc(1.6, -3.4, PZ + 0.8), (0.35, 2.6, 1.7), M_METAL, rot=RQ)
frustum('ProngGround', sloc(0.0, -3.4, PZ - 1.8), 0.5, 0.5, 2.6, M_METAL, rot=RQY, segs=12)

# ---------------- cable: strip top -> big arc over the left -> plug back ----------------
sock = sloc(0.0, 0.0, PZ)
sx = sock.x
szw = sock.z
cable_pts = [
    sloc(0.0, 0.0, HALF_L + 1.0),
    sloc(0.0, 0.0, HALF_L + 5.0),
    Vector((15.2, -1.0, 95.8)),
    Vector((10.0, -3.0, 97.3)),
    Vector((2.0, -6.0, 96.5)),
    Vector((-7.0, -9.5, 92.0)),
    Vector((-13.0, -13.0, 84.0)),
    Vector((-15.5, -17.0, 74.0)),
    Vector((-13.0, -21.0, 65.5)),
    Vector((-6.0, -23.5, 60.8)),
    Vector((0.0, -24.0, szw + 0.7)),
    Vector((sx - 6.0, -23.6, szw + 0.2)),
    Vector((sx - 1.5, -22.0, szw)),
    Vector((sx, -19.0, szw)),
    Vector((sx, -15.5, szw)),
    Vector((sx, -12.5, szw)),
]
tube('Cable', cable_pts, 1.35, M_CABLE, sides=14, samples=10)
