import bpy
import math
from mathutils import Vector, Matrix

# ---------- clear scene ----------
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
for m in list(bpy.data.meshes):
    if m.users == 0:
        bpy.data.meshes.remove(m)


# ---------- helpers ----------
def make_mat(name, col):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (col[0], col[1], col[2], 1.0)
    try:
        nt = mat.node_tree
        if nt is not None:
            for nd in nt.nodes:
                if nd.type == 'BSDF_PRINCIPLED':
                    nd.inputs['Base Color'].default_value = (col[0], col[1], col[2], 1.0)
    except Exception:
        pass
    return mat


def new_obj(name, verts, faces, mat, smooth=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata([(v[0], v[1], v[2]) for v in verts], [], faces)
    me.update()
    if smooth:
        me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    me.materials.append(mat)
    return ob


def frame(center, d):
    # local z along d, local y close to world Y, local x in the remaining direction
    d = Vector(d).normalized()
    p = Vector((0.0, 1.0, 0.0)).cross(d)
    if p.length < 1e-6:
        p = Vector((1.0, 0.0, 0.0))
    p.normalize()
    yv = d.cross(p).normalized()
    c = Vector(center)
    return Matrix(((p.x, yv.x, d.x, c.x),
                   (p.y, yv.y, d.y, c.y),
                   (p.z, yv.z, d.z, c.z),
                   (0.0, 0.0, 0.0, 1.0)))


def make_box(name, size, M, mat, bevel=0.0, local=(0.0, 0.0, 0.0)):
    x = size[0] * 0.5
    y = size[1] * 0.5
    z = size[2] * 0.5
    lo = Vector(local)
    raw = [(-x, -y, -z), (x, -y, -z), (x, y, -z), (-x, y, -z),
           (-x, -y, z), (x, -y, z), (x, y, z), (-x, y, z)]
    verts = [M @ (Vector(v) + lo) for v in raw]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    ob = new_obj(name, verts, faces, mat, smooth=False)
    if bevel > 0.0:
        mod = ob.modifiers.new('Bevel', 'BEVEL')
        mod.width = bevel
        mod.segments = 3
    return ob


def make_tube(name, pts, radius, mat, seg=12, radii=None):
    pts = [Vector(p) for p in pts]
    n = len(pts)
    verts = []
    faces = []
    prev_n = None
    for i in range(n):
        if i == 0:
            t = pts[1] - pts[0]
        elif i == n - 1:
            t = pts[n - 1] - pts[n - 2]
        else:
            t = pts[i + 1] - pts[i - 1]
        if t.length < 1e-9:
            t = Vector((0.0, 0.0, 1.0))
        t.normalize()
        if prev_n is None:
            a = Vector((0.0, 1.0, 0.0)) if abs(t.y) < 0.9 else Vector((1.0, 0.0, 0.0))
            nrm = t.cross(a).normalized()
        else:
            nrm = prev_n - t * prev_n.dot(t)
            if nrm.length < 1e-6:
                a = Vector((0.0, 1.0, 0.0)) if abs(t.y) < 0.9 else Vector((1.0, 0.0, 0.0))
                nrm = t.cross(a)
            nrm.normalize()
        b = t.cross(nrm).normalized()
        prev_n = nrm
        r = radii[i] if radii is not None else radius
        for j in range(seg):
            ang = 2.0 * math.pi * j / seg
            verts.append(pts[i] + (nrm * math.cos(ang) + b * math.sin(ang)) * r)
    for i in range(n - 1):
        for j in range(seg):
            j2 = (j + 1) % seg
            faces.append((i * seg + j, i * seg + j2, (i + 1) * seg + j2, (i + 1) * seg + j))
    faces.append(tuple(reversed(range(seg))))
    faces.append(tuple(range((n - 1) * seg, n * seg)))
    return new_obj(name, verts, faces, mat, smooth=True)


def make_ellipsoid(name, center, scale, mat, rotz=0.0, rings=12, segs=24):
    M = Matrix.Translation(Vector(center)) @ Matrix.Rotation(rotz, 4, 'Z') @ Matrix.Diagonal((scale[0], scale[1], scale[2], 1.0))
    verts = [M @ Vector((0.0, 0.0, 1.0))]
    for i in range(1, rings):
        phi = math.pi * i / rings
        for j in range(segs):
            th = 2.0 * math.pi * j / segs
            verts.append(M @ Vector((math.sin(phi) * math.cos(th), math.sin(phi) * math.sin(th), math.cos(phi))))
    verts.append(M @ Vector((0.0, 0.0, -1.0)))
    faces = []
    for j in range(segs):
        j2 = (j + 1) % segs
        faces.append((0, 1 + j, 1 + j2))
    for i in range(rings - 2):
        for j in range(segs):
            j2 = (j + 1) % segs
            a = 1 + i * segs
            b = 1 + (i + 1) * segs
            faces.append((a + j, b + j, b + j2, a + j2))
    last = 1 + (rings - 2) * segs
    bot = len(verts) - 1
    for j in range(segs):
        j2 = (j + 1) % segs
        faces.append((bot, last + j2, last + j))
    return new_obj(name, verts, faces, mat, smooth=True)


def catmull(pts, sub):
    out = []
    n = len(pts)
    for i in range(n - 1):
        p0 = pts[max(i - 1, 0)]
        p1 = pts[i]
        p2 = pts[i + 1]
        p3 = pts[min(i + 2, n - 1)]
        for s in range(sub):
            t = s / sub
            q = (p1 * 2.0 + (p2 - p0) * t + (p0 * 2.0 - p1 * 5.0 + p2 * 4.0 - p3) * (t * t) + (p1 * 3.0 - p0 - p2 * 3.0 + p3) * (t * t * t)) * 0.5
            out.append(q)
    out.append(pts[n - 1].copy())
    return out


# ---------- materials ----------
MAT_BODY = make_mat('Body', (0.93, 0.92, 0.9))
MAT_STRIP = make_mat('Strip', (0.85, 0.85, 0.82))
MAT_CABLE = make_mat('Cable', (0.78, 0.78, 0.76))
MAT_PLATE = make_mat('Plate', (0.97, 0.97, 0.97))
MAT_DARK = make_mat('Dark', (0.02, 0.02, 0.02))
MAT_WHITE = make_mat('EyeWhite', (1.0, 1.0, 1.0))
MAT_TEAR = make_mat('Tear', (0.12, 0.5, 0.9))
MAT_METAL = make_mat('Metal', (0.55, 0.55, 0.58))

# ---------- body (lathe with elliptical, shifting rings) ----------
# each ring: (z, rx, ry, cx)
RINGS = [
    (0.0, 33.0, 25.0, -3.0),
    (1.3, 34.0, 26.0, -3.0),
    (3.8, 27.5, 21.5, -2.2),
    (8.0, 20.5, 17.0, -0.8),
    (13.0, 21.5, 18.0, 0.4),
    (19.0, 24.5, 20.0, 0.8),
    (27.0, 25.5, 21.0, 0.6),
    (35.0, 25.0, 20.5, 0.5),
    (42.0, 22.5, 18.5, 1.2),
    (47.0, 18.0, 14.5, 3.2),
    (50.5, 12.5, 9.5, 7.6),
    (54.0, 9.0, 6.0, 10.8),
    (59.0, 7.0, 4.3, 12.2),
]
DENSE = catmull([Vector(r) for r in RINGS], 5)
SEG = 64
bverts = []
bfaces = []
for r in DENSE:
    for j in range(SEG):
        a = 2.0 * math.pi * j / SEG
        bverts.append((r[3] + r[1] * math.cos(a), r[2] * math.sin(a), r[0]))
nr = len(DENSE)
for i in range(nr - 1):
    for j in range(SEG):
        j2 = (j + 1) % SEG
        bfaces.append((i * SEG + j, i * SEG + j2, (i + 1) * SEG + j2, (i + 1) * SEG + j))
bfaces.append(tuple(reversed(range(SEG))))
bfaces.append(tuple(range((nr - 1) * SEG, nr * SEG)))
new_obj('Body', bverts, bfaces, MAT_BODY, smooth=True)


def ring_at(z):
    if z <= DENSE[0][0]:
        return DENSE[0]
    for i in range(len(DENSE) - 1):
        a = DENSE[i]
        b = DENSE[i + 1]
        if a[0] <= z <= b[0]:
            t = (z - a[0]) / (b[0] - a[0]) if b[0] > a[0] else 0.0
            return a.lerp(b, t)
    return DENSE[-1]


def surf_y(x, z):
    r = ring_at(z)
    t = max(-0.98, min(0.98, (x - r[3]) / r[1]))
    return -r[2] * math.sqrt(1.0 - t * t)


def surf_path(pts2d, off, n=10):
    out = []
    for k in range(len(pts2d) - 1):
        x0, z0 = pts2d[k]
        x1, z1 = pts2d[k + 1]
        for s in range(n):
            t = s / n
            x = x0 + (x1 - x0) * t
            z = z0 + (z1 - z0) * t
            out.append(Vector((x, surf_y(x, z) - off, z)))
    x, z = pts2d[-1]
    out.append(Vector((x, surf_y(x, z) - off, z)))
    return out


def face_frame(x, z):
    y = surf_y(x, z)
    dydx = (surf_y(x + 0.3, z) - surf_y(x - 0.3, z)) / 0.6
    a = math.atan(dydx)
    nrm = Vector((math.sin(a), -math.cos(a), 0.0))
    return Vector((x, y, z)), a, nrm


# ---------- face ----------
def make_eye(name, x, z, rim, white, pupil, pshift):
    c, a, nrm = face_frame(x, z)
    tan = Vector((math.cos(a), math.sin(a), 0.0))
    make_ellipsoid(name + '_Rim', c, rim, MAT_DARK, rotz=a)
    make_ellipsoid(name + '_White', c + nrm * 0.15, white, MAT_WHITE, rotz=a)
    make_ellipsoid(name + '_Pupil', c + nrm * 0.6 + tan * pshift, pupil, MAT_DARK, rotz=a)


make_eye('EyeL', 4.6, 36.0, (2.9, 0.5, 1.8), (2.4, 0.7, 1.35), (1.1, 0.5, 1.05), 0.4)
make_eye('EyeR', 14.2, 38.0, (2.1, 0.5, 1.2), (1.7, 0.7, 0.85), (0.75, 0.5, 0.7), -0.2)

# brows
make_tube('BrowL', surf_path([(1.2, 38.9), (4.5, 38.7), (7.8, 38.0)], 0.2), 0.38, MAT_DARK, seg=8)
make_tube('BrowR', surf_path([(12.0, 39.7), (14.4, 40.1), (16.8, 40.4)], 0.2), 0.38, MAT_DARK, seg=8)

# nose
nc, na, nn = face_frame(10.0, 34.6)
make_ellipsoid('Nose', nc + nn * 0.2, (1.25, 2.0, 2.4), MAT_BODY, rotz=na)
make_tube('NoseLine', surf_path([(8.6, 32.3), (10.0, 32.0), (11.5, 32.3)], 0.25), 0.32, MAT_DARK, seg=8)
make_tube('NoseBridge', surf_path([(11.6, 37.2), (11.7, 34.6), (11.5, 32.6)], 0.25), 0.28, MAT_DARK, seg=8)

# mouth and chin crease
make_tube('Mouth', surf_path([(5.8, 30.4), (9.2, 29.8), (12.6, 30.5)], 0.2), 0.36, MAT_DARK, seg=8)
make_tube('Chin', surf_path([(7.8, 28.3), (10.6, 28.3)], 0.2), 0.3, MAT_DARK, seg=8)

# tears
def make_tear(name, x0, z0, x1, z1, drop):
    pts = surf_path([(x0, z0), (x1, z1)], 0.25, n=14)
    make_tube(name, pts, 0.45, MAT_TEAR, seg=8)
    if drop:
        make_ellipsoid(name + '_Drop', pts[-1], (0.75, 0.6, 1.0), MAT_TEAR)


make_tear('TearL1', 3.2, 34.3, 3.5, 27.5, True)
make_tear('TearL2', 5.6, 34.2, 5.8, 31.2, False)
make_tear('TearR1', 13.7, 36.8, 14.3, 22.0, True)
make_tear('TearR2', 15.7, 36.9, 16.0, 32.5, False)

# ---------- power strip (the head / neck) ----------
STRIP_D = Vector((0.184, 0.0, 0.983)).normalized()
STRIP_TOP = Vector((17.3, 0.0, 86.4))
STRIP_LEN = 36.0
STRIP_W = 13.0
STRIP_DEPTH = 7.5
STRIP_C = STRIP_TOP - STRIP_D * (STRIP_LEN * 0.5)
MS = frame(STRIP_C, STRIP_D)
make_box('PowerStrip', (STRIP_W, STRIP_DEPTH, STRIP_LEN), MS, MAT_STRIP, bevel=1.2)

front_y = -STRIP_DEPTH * 0.5
for idx, zc in enumerate((9.0, -0.5)):
    make_box('OutletPlate%d' % idx, (8.6, 0.7, 8.2), MS, MAT_PLATE, bevel=0.25, local=(0.0, front_y - 0.15, zc))
    for sx in (-1.9, 1.9):
        make_box('OutletSlot%d' % idx, (0.9, 0.5, 2.8), MS, MAT_DARK, local=(sx, front_y - 0.5, zc + 1.2))
    g0 = MS @ Vector((0.0, front_y - 0.3, zc - 2.1))
    g1 = MS @ Vector((0.0, front_y - 0.75, zc - 2.1))
    make_tube('OutletGround%d' % idx, [g0, g1], 0.85, MAT_DARK, seg=16)

# strain relief at the top of the strip
sr0 = STRIP_TOP - STRIP_D * 0.5
sr1 = STRIP_TOP + STRIP_D * 4.2
make_tube('StrainRelief', [sr0, sr1], 2.2, MAT_CABLE, seg=16, radii=[2.6, 1.7])
for k in range(3):
    a0 = STRIP_TOP + STRIP_D * (0.6 + k * 1.1)
    a1 = a0 + STRIP_D * 0.5
    rr = 2.85 - k * 0.3
    make_tube('ReliefRidge%d' % k, [a0, a1], rr, MAT_CABLE, seg=16)

# ---------- plug ----------
PLUG_D = Vector((0.83, 0.0, -0.55)).normalized()
PLUG_FRONT = Vector((0.5, 0.0, 56.0))
PLUG_LEN = 10.0
PLUG_C = PLUG_FRONT - PLUG_D * (PLUG_LEN * 0.5)
PLUG_BACK = PLUG_FRONT - PLUG_D * PLUG_LEN
MP = frame(PLUG_C, PLUG_D)
make_box('PlugBody', (8.0, 5.0, PLUG_LEN), MP, MAT_CABLE, bevel=1.0)
for sx in (-2.0, 2.0):
    make_box('PlugProng', (0.5, 2.2, 4.5), MP, MAT_METAL, local=(sx, 0.0, PLUG_LEN * 0.5 + 1.6))
make_tube('PlugCollar', [PLUG_BACK + PLUG_D * 0.6, PLUG_BACK - PLUG_D * 3.0], 2.0, MAT_CABLE, seg=16, radii=[2.9, 1.5])

# ---------- cable loop from strip top over to the plug ----------
cable_ctrl = [
    STRIP_TOP.copy(),
    STRIP_TOP + STRIP_D * 5.0,
    Vector((16.2, 0.0, 95.3)),
    Vector((10.5, 0.0, 97.6)),
    Vector((2.4, 0.0, 98.2)),
    Vector((-6.5, 0.0, 95.0)),
    Vector((-12.5, 0.0, 87.0)),
    Vector((-14.7, 0.0, 77.5)),
    Vector((-13.8, 0.0, 69.5)),
    Vector((-11.3, 0.0, 64.3)),
    PLUG_BACK.copy(),
]
make_tube('Cable', catmull(cable_ctrl, 10), 1.2, MAT_CABLE, seg=14)
