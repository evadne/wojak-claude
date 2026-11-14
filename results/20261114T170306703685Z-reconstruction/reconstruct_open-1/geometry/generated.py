import bpy
import math
from mathutils import Vector, Matrix

scene = bpy.context.scene
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
for coll in (bpy.data.meshes, bpy.data.curves, bpy.data.materials):
    for b in list(coll):
        if b.users == 0:
            coll.remove(b)


def material(name, rgb):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (rgb[0], rgb[1], rgb[2], 1.0)
    try:
        if m.node_tree is None:
            m.use_nodes = True
        for n in m.node_tree.nodes:
            if n.type == 'BSDF_PRINCIPLED':
                n.inputs['Base Color'].default_value = (rgb[0], rgb[1], rgb[2], 1.0)
    except Exception:
        pass
    return m


MAT_SKIN = material('Skin', (0.93, 0.90, 0.85))
MAT_STRIP = material('Strip', (0.97, 0.97, 0.95))
MAT_CORD = material('Cord', (0.84, 0.84, 0.84))
MAT_PLATE = material('Plate', (0.78, 0.78, 0.78))
MAT_DARK = material('Dark', (0.02, 0.02, 0.02))
MAT_WHITE = material('EyeWhite', (1.0, 1.0, 1.0))
MAT_BLUE = material('Tear', (0.12, 0.50, 0.92))
MAT_METAL = material('Prong', (0.60, 0.60, 0.55))


def make_obj(name, verts, faces, mat, matrix=None, smooth=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.update()
    if smooth:
        try:
            me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
        except Exception:
            pass
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    scene.collection.objects.link(ob)
    if matrix is not None:
        ob.matrix_world = matrix
    return ob


def catmull(pts, n):
    pts = [Vector(p) for p in pts]
    P = [pts[0]] + pts + [pts[-1]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for j in range(n):
            t = j / n
            v = (p1 * 2.0 + (p2 - p0) * t + (p0 * 2.0 - p1 * 5.0 + p2 * 4.0 - p3) * (t * t) + (p1 * 3.0 - p0 - p2 * 3.0 + p3) * (t * t * t)) * 0.5
            out.append(v)
    out.append(pts[-1].copy())
    return out


def resample(vals, n):
    out = []
    for i in range(n):
        f = i * (len(vals) - 1) / max(1, n - 1)
        k = min(int(f), len(vals) - 2)
        u = f - k
        out.append(vals[k] * (1.0 - u) + vals[k + 1] * u)
    return out


def tube(name, pts, radii, mat, seg=12, matrix=None, smooth=True):
    pts = [Vector(p) for p in pts]
    if not isinstance(radii, (list, tuple)):
        radii = [radii] * len(pts)
    verts = []
    faces = []
    n_prev = None
    for i, p in enumerate(pts):
        if i == 0:
            t = pts[1] - pts[0]
        elif i == len(pts) - 1:
            t = pts[-1] - pts[-2]
        else:
            t = pts[i + 1] - pts[i - 1]
        t.normalize()
        if n_prev is None:
            ref = Vector((0.0, 1.0, 0.0)) if abs(t.y) < 0.9 else Vector((1.0, 0.0, 0.0))
            n = ref - t * ref.dot(t)
        else:
            n = n_prev - t * n_prev.dot(t)
        n.normalize()
        n_prev = n
        b = t.cross(n)
        r = radii[i]
        for j in range(seg):
            a = 2.0 * math.pi * j / seg
            verts.append(p + (n * math.cos(a) + b * math.sin(a)) * r)
    nr = len(pts)
    for i in range(nr - 1):
        for j in range(seg):
            j2 = (j + 1) % seg
            faces.append((i * seg + j, i * seg + j2, (i + 1) * seg + j2, (i + 1) * seg + j))
    c0 = len(verts)
    verts.append(pts[0])
    c1 = len(verts)
    verts.append(pts[-1])
    last = (nr - 1) * seg
    for j in range(seg):
        j2 = (j + 1) % seg
        faces.append((c0, j2, j))
        faces.append((c1, last + j, last + j2))
    return make_obj(name, verts, faces, mat, matrix, smooth)


def ellipsoid(name, center, radii, mat, rot=None, seg=20, rings=12):
    verts = [(0.0, 0.0, 1.0)]
    faces = []
    for i in range(1, rings):
        th = math.pi * i / rings
        for j in range(seg):
            ph = 2.0 * math.pi * j / seg
            verts.append((math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th)))
    verts.append((0.0, 0.0, -1.0))
    bottom = len(verts) - 1
    for j in range(seg):
        j2 = (j + 1) % seg
        faces.append((0, 1 + j, 1 + j2))
        base = 1 + (rings - 2) * seg
        faces.append((bottom, base + j2, base + j))
    for i in range(rings - 2):
        for j in range(seg):
            j2 = (j + 1) % seg
            a = 1 + i * seg
            b = 1 + (i + 1) * seg
            faces.append((a + j, b + j, b + j2, a + j2))
    m = Matrix.Translation(Vector(center))
    if rot is not None:
        m = m @ rot
    m = m @ Matrix.Diagonal((radii[0], radii[1], radii[2], 1.0))
    return make_obj(name, verts, faces, mat, m, True)


def box(name, size, matrix, mat, bevel=0.0, seg=3):
    sx, sy, sz = size[0] / 2.0, size[1] / 2.0, size[2] / 2.0
    verts = [(-sx, -sy, -sz), (sx, -sy, -sz), (sx, sy, -sz), (-sx, sy, -sz),
             (-sx, -sy, sz), (sx, -sy, sz), (sx, sy, sz), (-sx, sy, sz)]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    ob = make_obj(name, verts, faces, mat, matrix, False)
    if bevel > 0.0:
        try:
            mod = ob.modifiers.new('Bevel', 'BEVEL')
            mod.width = bevel
            mod.segments = seg
        except Exception:
            pass
    return ob


# ---------------- body (torso + neck) as a loft of horizontal ellipses ----------------
# each ring: (z, centre x, radius x, radius y)
RINGS = [
    (0.0, -3.0, 21.0, 13.0),
    (1.5, -3.0, 24.0, 15.5),
    (6.0, -2.5, 25.5, 16.5),
    (14.5, -1.2, 26.0, 17.0),
    (23.0, 0.7, 26.2, 17.0),
    (31.5, 1.9, 25.3, 16.0),
    (38.0, 2.8, 22.3, 14.0),
    (43.4, 4.0, 18.5, 11.5),
    (48.5, 11.5, 11.0, 8.5),
    (53.5, 15.5, 8.5, 6.5),
    (57.0, 16.5, 7.5, 5.8),
]
DENSE = catmull([Vector(r) for r in RINGS], 4)


def ring_at(z):
    if z <= DENSE[0][0]:
        return DENSE[0]
    for i in range(len(DENSE) - 1):
        a = DENSE[i]
        b = DENSE[i + 1]
        if b[0] >= z and b[0] > a[0]:
            u = (z - a[0]) / (b[0] - a[0])
            u = max(0.0, min(1.0, u))
            return a * (1.0 - u) + b * u
    return DENSE[-1]


def surf(x, z, off=0.0):
    r = ring_at(z)
    cx, rx, ry = r[1], r[2], r[3]
    u = max(-0.97, min(0.97, (x - cx) / rx))
    y = -ry * math.sqrt(1.0 - u * u)
    n = Vector((u / rx, (y / ry) / ry, 0.0))
    n.normalize()
    p = Vector((cx + u * rx, y, z)) + n * off
    yaw = math.atan2(n.x, -n.y)
    return p, yaw


def build_body():
    seg = 36
    verts = []
    faces = []
    for r in DENSE:
        for j in range(seg):
            a = 2.0 * math.pi * j / seg
            verts.append((r[1] + r[2] * math.cos(a), r[3] * math.sin(a), r[0]))
    nr = len(DENSE)
    for i in range(nr - 1):
        for j in range(seg):
            j2 = (j + 1) % seg
            faces.append((i * seg + j, i * seg + j2, (i + 1) * seg + j2, (i + 1) * seg + j))
    c0 = len(verts)
    verts.append((DENSE[0][1], 0.0, DENSE[0][0]))
    c1 = len(verts)
    verts.append((DENSE[-1][1], 0.0, DENSE[-1][0]))
    last = (nr - 1) * seg
    for j in range(seg):
        j2 = (j + 1) % seg
        faces.append((c0, j2, j))
        faces.append((c1, last + j, last + j2))
    make_obj('Body', verts, faces, MAT_SKIN)


build_body()

# left shoulder, arm and hand resting on the ground
ellipsoid('Shoulder', (-13.0, 0.0, 35.0), (10.0, 12.0, 9.5), MAT_SKIN)
arm_pts = catmull([(-16.0, -1.0, 36.0), (-21.0, -2.0, 24.0), (-25.5, -3.0, 12.0), (-28.5, -4.0, 5.0)], 5)
arm_r = resample([8.5, 7.5, 6.0, 4.5], len(arm_pts))
tube('Arm', arm_pts, arm_r, MAT_SKIN, seg=20)
ellipsoid('Hand', (-30.5, -4.5, 2.6), (6.5, 6.0, 2.6), MAT_SKIN)

# ---------------- power strip head ----------------
TILT = math.radians(9.6)
YAW = math.radians(-35.0)
STRIP_C = Vector((17.9, 0.0, 63.3))
STRIP_L = 40.0
STRIP_W = 12.0
STRIP_D = 9.0
M_STRIP = Matrix.Translation(STRIP_C) @ Matrix.Rotation(TILT, 4, 'Y') @ Matrix.Rotation(YAW, 4, 'Z')
box('PowerStrip', (STRIP_W, STRIP_D, STRIP_L), M_STRIP, MAT_STRIP, bevel=1.3, seg=4)

ROT_FACE = Matrix.Rotation(math.radians(90.0), 4, 'X')
for idx, oz in enumerate((10.5, 0.5)):
    front = -STRIP_D / 2.0
    m_plate = M_STRIP @ Matrix.Translation(Vector((0.0, front - 0.1, oz))) @ ROT_FACE @ Matrix.Diagonal((3.6, 4.3, 1.0, 1.0))
    tube('OutletPlate%d' % idx, [(0.0, 0.0, -0.4), (0.0, 0.0, 0.4)], 1.0, MAT_PLATE, seg=28, matrix=m_plate, smooth=False)
    for sx in (-1.3, 1.3):
        m_slot = M_STRIP @ Matrix.Translation(Vector((sx, front - 0.5, oz + 1.0)))
        box('OutletSlot%d' % idx, (0.7, 0.6, 2.4), m_slot, MAT_DARK)
    m_gnd = M_STRIP @ Matrix.Translation(Vector((0.0, front - 0.5, oz - 2.0))) @ ROT_FACE
    tube('OutletGround%d' % idx, [(0.0, 0.0, -0.3), (0.0, 0.0, 0.3)], 0.75, MAT_DARK, seg=16, matrix=m_gnd, smooth=False)

# strain relief on top of the strip
AXIS = (M_STRIP.to_3x3() @ Vector((0.0, 0.0, 1.0))).normalized()
TOP = M_STRIP @ Vector((0.0, 0.0, STRIP_L / 2.0))
tube('StrainRelief', [TOP - AXIS * 0.5, TOP + AXIS * 4.5], [2.4, 1.7], MAT_CORD, seg=16)
for k, s in enumerate((1.0, 2.2, 3.4)):
    tube('ReliefRidge%d' % k, [TOP + AXIS * s, TOP + AXIS * (s + 0.6)], 2.7 - 0.2 * k, MAT_CORD, seg=16, smooth=False)

# ---------------- cord looping over to the plug ----------------
P0 = Vector((-7.0, -4.0, 58.8))
cord_ctrl = [
    TOP + AXIS * 1.0,
    TOP + AXIS * 6.0,
    Vector((20.5, 0.0, 94.0)),
    Vector((14.0, 0.0, 97.0)),
    Vector((3.5, -0.5, 96.0)),
    Vector((-6.0, -1.0, 90.5)),
    Vector((-12.0, -2.0, 81.0)),
    Vector((-14.0, -3.0, 70.5)),
    Vector((-12.0, -3.5, 63.0)),
    P0,
]
tube('Cord', catmull(cord_ctrl, 8), 1.3, MAT_CORD, seg=12)

# ---------------- plug ----------------
D = Vector((0.873, 0.0, -0.488)).normalized()
RQ = D.to_track_quat('Z', 'Y').to_matrix().to_4x4()
tube('PlugCollar', [P0 - D * 0.5, P0 + D * 3.4], [1.5, 3.1], MAT_STRIP, seg=16)
box('PlugBody', (5.0, 8.0, 11.0), Matrix.Translation(P0 + D * 8.5) @ RQ, MAT_STRIP, bevel=1.2, seg=3)
for k, oy in enumerate((-1.8, 1.8)):
    m_pr = Matrix.Translation(P0 + D * 15.2) @ RQ @ Matrix.Translation(Vector((0.0, oy, 0.0)))
    box('Prong%d' % k, (2.4, 0.5, 3.0), m_pr, MAT_METAL)

# ---------------- face on the chest ----------------

def surf_line(name, xz, radius, mat, off=0.1, n=6):
    ctrl = [Vector((p[0], 0.0, p[1])) for p in xz]
    sm = catmull(ctrl, n)
    pts = [surf(p.x, p.z, off)[0] for p in sm]
    return tube(name, pts, radius, mat, seg=8)


def eye(name, x, z, w, h, pupil_dx):
    p, yaw = surf(x, z, 0.0)
    R = Matrix.Rotation(yaw, 4, 'Z')
    R3 = R.to_3x3()
    ellipsoid(name + 'Rim', p, (w + 0.4, 0.5, h + 0.4), MAT_DARK, R)
    ellipsoid(name + 'White', p + R3 @ Vector((0.0, -0.25, 0.0)), (w, 0.6, h), MAT_WHITE, R)
    ellipsoid(name + 'Pupil', p + R3 @ Vector((pupil_dx, -0.6, 0.0)), (h * 0.62, 0.4, h * 0.78), MAT_DARK, R)


eye('EyeL', 6.8, 30.6, 2.9, 1.6, 0.4)
eye('EyeR', 15.4, 32.6, 2.1, 1.15, -0.3)

surf_line('BrowL', [(3.0, 33.4), (6.8, 33.9), (10.6, 32.5)], 0.45, MAT_DARK)
surf_line('BrowR', [(12.8, 34.3), (15.5, 35.2), (18.4, 35.0)], 0.45, MAT_DARK)
surf_line('BagL', [(4.6, 28.3), (7.0, 27.8), (9.2, 28.4)], 0.28, MAT_DARK)
surf_line('BagR', [(13.9, 30.8), (15.6, 30.5), (17.4, 31.0)], 0.28, MAT_DARK)

# nose
pn, yawn = surf(12.3, 29.4, 0.0)
ellipsoid('NoseBump', pn, (1.3, 1.7, 1.9), MAT_SKIN, Matrix.Rotation(yawn, 4, 'Z'))
surf_line('NoseLine', [(11.6, 31.6), (11.0, 29.0), (11.6, 27.6), (13.4, 27.6)], 0.35, MAT_DARK, off=0.9)

# mouth (frown) and lower lip
surf_line('Mouth', [(8.4, 25.2), (11.4, 26.0), (14.6, 25.0)], 0.4, MAT_DARK)
surf_line('Lip', [(10.2, 23.8), (11.6, 23.6), (13.0, 23.9)], 0.3, MAT_DARK)

# tears
surf_line('TearL1', [(5.4, 28.2), (5.1, 25.0), (5.7, 21.5)], 0.45, MAT_BLUE, off=0.2)
surf_line('TearL2', [(7.6, 28.0), (7.8, 26.6), (7.6, 25.4)], 0.4, MAT_BLUE, off=0.2)
surf_line('TearR1', [(16.9, 30.8), (17.1, 26.0), (16.3, 20.0), (16.6, 14.5)], 0.45, MAT_BLUE, off=0.2)
surf_line('TearR2', [(14.6, 30.6), (15.0, 28.8), (15.2, 27.2)], 0.4, MAT_BLUE, off=0.2)
for k, (tx, tz) in enumerate(((5.7, 21.2), (16.6, 14.2), (7.6, 25.2), (15.2, 27.0))):
    pt, yawt = surf(tx, tz, 0.25)
    ellipsoid('TearDrop%d' % k, pt, (0.7, 0.5, 0.95), MAT_BLUE, Matrix.Rotation(yawt, 4, 'Z'), seg=12, rings=8)
