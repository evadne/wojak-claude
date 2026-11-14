import bpy
import math
from mathutils import Vector, Matrix

# ---------------------------------------------------------------
# clear scene
# ---------------------------------------------------------------
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
for me in list(bpy.data.meshes):
    if me.users == 0:
        bpy.data.meshes.remove(me)

COL = bpy.context.scene.collection


def make_mat(name, rgb):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (rgb[0], rgb[1], rgb[2], 1.0)
    return m


MAT_SKIN = make_mat('Skin', (0.93, 0.91, 0.87))
MAT_STRIP = make_mat('Strip', (0.82, 0.80, 0.74))
MAT_PLATE = make_mat('Plate', (0.97, 0.96, 0.93))
MAT_CORD = make_mat('Cord', (0.70, 0.69, 0.66))
MAT_DARK = make_mat('Dark', (0.03, 0.03, 0.03))
MAT_EYE = make_mat('EyeWhite', (1.0, 1.0, 1.0))
MAT_TEAR = make_mat('Tear', (0.15, 0.55, 0.95))
MAT_METAL = make_mat('Metal', (0.60, 0.60, 0.63))


# ---------------------------------------------------------------
# helpers
# ---------------------------------------------------------------
def loft(name, rings, mat, smooth=True):
    n = len(rings[0])
    verts = []
    faces = []
    for r in rings:
        for p in r:
            verts.append((p[0], p[1], p[2]))
    for k in range(len(rings) - 1):
        a = k * n
        b = (k + 1) * n
        for i in range(n):
            j = (i + 1) % n
            faces.append((a + i, a + j, b + j, b + i))
    faces.append(tuple(reversed(range(n))))
    last = (len(rings) - 1) * n
    faces.append(tuple(range(last, last + n)))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    if smooth:
        mesh.polygons.foreach_set('use_smooth', [True] * len(mesh.polygons))
        try:
            mesh.set_sharp_from_angle(angle=math.radians(50.0))
        except Exception:
            pass
    mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    COL.objects.link(obj)
    return obj


def ering(cx, cy, rx, ry, z, n=32, M=None):
    pts = []
    for i in range(n):
        a = 2.0 * math.pi * i / n
        v = Vector((cx + rx * math.cos(a), cy + ry * math.sin(a), z))
        if M is not None:
            v = M @ v
        pts.append(v)
    return pts


def rrect(hx, hy, r, z, s=4, M=None, ox=0.0, oy=0.0):
    pts = []
    corners = [(hx - r, hy - r, 0.0), (-(hx - r), hy - r, 90.0),
               (-(hx - r), -(hy - r), 180.0), (hx - r, -(hy - r), 270.0)]
    for (cx, cy, a0) in corners:
        for i in range(s + 1):
            a = math.radians(a0 + 90.0 * i / s)
            v = Vector((ox + cx + r * math.cos(a), oy + cy + r * math.sin(a), z))
            if M is not None:
                v = M @ v
            pts.append(v)
    return pts


def ellipsoid(name, M, radii, mat, n=28, m=14):
    phis = [-math.pi / 2 + 0.07]
    for k in range(1, m):
        phis.append(-math.pi / 2 + math.pi * k / m)
    phis.append(math.pi / 2 - 0.07)
    rings = []
    for ph in phis:
        c = math.cos(ph)
        rings.append(ering(0.0, 0.0, radii[0] * c, radii[1] * c, radii[2] * math.sin(ph), n, M))
    return loft(name, rings, mat, True)


def catmull(pts, n):
    pts = [tuple(p) for p in pts]
    ext = [pts[0]] + pts + [pts[-1]]
    out = []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        for s in range(n):
            t = s / n
            out.append(tuple(
                0.5 * ((2.0 * b) + (-a + c) * t + (2.0 * a - 5.0 * b + 4.0 * c - d) * t * t
                       + (-a + 3.0 * b - 3.0 * c + d) * t * t * t)
                for a, b, c, d in zip(p0, p1, p2, p3)))
    out.append(pts[-1])
    return out


def tube(name, pts, radius, mat, segs=12):
    P = [Vector(p) for p in pts]
    n = len(P)
    T = []
    for i in range(n):
        d = P[min(i + 1, n - 1)] - P[max(i - 1, 0)]
        if d.length < 1e-8:
            d = Vector((0.0, 0.0, 1.0))
        T.append(d.normalized())
    t0 = T[0]
    ref = Vector((0.0, 1.0, 0.0)) if abs(t0.y) < 0.9 else Vector((1.0, 0.0, 0.0))
    nrm = (ref - t0 * ref.dot(t0)).normalized()
    rings = []
    for i in range(n):
        t = T[i]
        q = nrm - t * nrm.dot(t)
        if q.length < 1e-6:
            ref = Vector((0.0, 1.0, 0.0)) if abs(t.y) < 0.9 else Vector((1.0, 0.0, 0.0))
            q = ref - t * ref.dot(t)
        nrm = q.normalized()
        b = t.cross(nrm)
        ring = []
        for k in range(segs):
            a = 2.0 * math.pi * k / segs
            ring.append(P[i] + radius * (math.cos(a) * nrm + math.sin(a) * b))
        rings.append(ring)
    return loft(name, rings, mat, True)


def frame(origin, zdir, hint):
    z = Vector(zdir).normalized()
    h = Vector(hint)
    y = h - z * h.dot(z)
    if y.length < 1e-6:
        h = Vector((1.0, 0.0, 0.0))
        y = h - z * h.dot(z)
    y.normalize()
    x = y.cross(z)
    o = Vector(origin)
    return Matrix(((x.x, y.x, z.x, o.x),
                   (x.y, y.y, z.y, o.y),
                   (x.z, y.z, z.z, o.z),
                   (0.0, 0.0, 0.0, 1.0)))


# ---------------------------------------------------------------
# body: gourd-like mound (head/torso) + hunched shoulder + base
# ---------------------------------------------------------------
# (z, centre x, radius x, radius y)
PROFILE = [
    (0.5, 10.5, 17.0, 13.0),
    (4.0, 11.0, 18.6, 15.5),
    (12.0, 11.5, 19.2, 17.0),
    (22.0, 11.8, 19.2, 17.2),
    (31.0, 12.0, 18.0, 16.0),
    (38.0, 12.3, 16.0, 13.5),
    (44.0, 12.8, 11.5, 9.5),
    (49.0, 13.4, 8.2, 6.0),
    (54.0, 14.2, 5.5, 2.8),
]
prof = catmull(PROFILE, 4)
loft('BodyMound', [ering(p[1], 0.0, p[2], p[3], p[0], 40) for p in prof], MAT_SKIN, True)

ellipsoid('Shoulder',
          Matrix.Translation((-8.0, 1.0, 24.0)) @ Matrix.Rotation(math.radians(12.0), 4, 'Y'),
          (21.0, 15.0, 24.0), MAT_SKIN, 36, 18)
ellipsoid('ShoulderBridge', Matrix.Translation((3.0, 0.5, 36.0)), (13.0, 10.0, 13.5), MAT_SKIN, 32, 16)
ellipsoid('Base', Matrix.Translation((1.0, -1.0, 3.5)), (36.0, 22.0, 3.5), MAT_SKIN, 40, 10)


def prof_at(z):
    if z <= prof[0][0]:
        return prof[0]
    for a, b in zip(prof, prof[1:]):
        if b[0] > a[0] and a[0] <= z <= b[0]:
            t = (z - a[0]) / (b[0] - a[0])
            return tuple(a[k] + (b[k] - a[k]) * t for k in range(4))
    return prof[-1]


def front_y(x, z):
    p = prof_at(z)
    d = max(-0.97, min(0.97, (x - p[1]) / p[2]))
    return -p[3] * math.sqrt(1.0 - d * d)


def snormal(x, z):
    e = 0.05
    fx = (front_y(x + e, z) - front_y(x - e, z)) / (2.0 * e)
    fz = (front_y(x, z + e) - front_y(x, z - e)) / (2.0 * e)
    return Vector((fx, -1.0, fz)).normalized()


def surf(x, z, off=0.0):
    return Vector((x, front_y(x, z), z)) + snormal(x, z) * off


def feature(name, x, z, radii, mat, off):
    M = frame(surf(x, z, off), snormal(x, z), Vector((0.0, 0.0, 1.0)))
    return ellipsoid(name, M, radii, mat, 18, 8)


def surf_tube(name, pts_xz, radius, mat, off=0.25, n=6):
    samples = catmull(pts_xz, n)
    return tube(name, [surf(p[0], p[1], off) for p in samples], radius, mat, 8)


# ---------------------------------------------------------------
# face on the front of the mound
# ---------------------------------------------------------------
# eyes
feature('EyeL', 6.6, 36.0, (2.4, 1.3, 0.6), MAT_EYE, 0.15)
feature('PupilL', 7.1, 36.0, (1.15, 0.95, 0.5), MAT_DARK, 0.55)
feature('EyeR', 14.9, 38.2, (1.9, 1.1, 0.55), MAT_EYE, 0.15)
feature('PupilR', 14.6, 38.1, (0.95, 0.8, 0.45), MAT_DARK, 0.5)
# brows / lids
surf_tube('BrowL', [(3.4, 37.6), (5.5, 38.1), (8.0, 37.7), (9.6, 36.6)], 0.38, MAT_DARK, 0.35)
surf_tube('LidL', [(4.4, 35.1), (6.6, 34.5), (8.8, 35.0)], 0.25, MAT_DARK, 0.3)
surf_tube('BrowR', [(12.7, 39.4), (14.8, 39.9), (17.0, 39.3)], 0.38, MAT_DARK, 0.35)
surf_tube('LidR', [(13.4, 37.1), (15.0, 36.8), (16.6, 37.2)], 0.25, MAT_DARK, 0.3)
# nose
feature('Nose', 12.4, 35.2, (1.2, 2.3, 1.5), MAT_SKIN, 0.0)
surf_tube('NoseLine', [(11.3, 38.0), (11.0, 35.4), (11.6, 33.5), (13.4, 33.3)], 0.25, MAT_DARK, 0.3)
# mouth and chin
surf_tube('Mouth', [(8.2, 31.3), (10.0, 32.0), (12.0, 31.9), (13.5, 31.1)], 0.33, MAT_DARK, 0.3)
surf_tube('Chin', [(9.6, 29.9), (10.6, 29.7), (11.6, 29.9)], 0.22, MAT_DARK, 0.3)
# tears
surf_tube('TearL', [(5.6, 34.8), (5.2, 32.0), (5.5, 29.5), (5.3, 27.5)], 0.45, MAT_TEAR, 0.3)
surf_tube('TearR1', [(14.8, 36.8), (15.0, 32.0), (15.2, 26.0), (15.0, 21.0)], 0.45, MAT_TEAR, 0.3)
surf_tube('TearR2', [(16.8, 37.0), (17.2, 34.5), (17.0, 32.0)], 0.4, MAT_TEAR, 0.3)

# ---------------------------------------------------------------
# power strip rising from the neck
# ---------------------------------------------------------------
SM = (Matrix.Translation((13.6, 0.0, 49.5))
      @ Matrix.Rotation(math.radians(8.5), 4, 'Y')
      @ Matrix.Rotation(math.radians(-28.0), 4, 'Z'))

strip_rings = [
    rrect(6.75, 3.5, 1.2, 0.0, 4, SM),
    rrect(6.75, 3.5, 1.2, 35.5, 4, SM),
    rrect(6.3, 3.1, 1.2, 36.6, 4, SM),
    rrect(5.2, 2.2, 1.0, 37.0, 4, SM),
]
loft('PowerStrip', strip_rings, MAT_STRIP, True)

for idx, zc in enumerate((27.5, 17.5)):
    PM = SM @ Matrix.Translation((0.0, -3.5, zc)) @ Matrix.Rotation(math.radians(90.0), 4, 'X')
    loft('OutletPlate%d' % idx,
         [rrect(4.6, 4.5, 1.5, -0.3, 4, PM), rrect(4.6, 4.5, 1.5, 0.45, 4, PM),
          rrect(4.2, 4.1, 1.3, 0.6, 4, PM)],
         MAT_PLATE, True)
    for sx in (-1.7, 1.7):
        loft('OutletSlot%d' % idx,
             [rrect(0.45, 1.35, 0.15, 0.3, 2, PM, sx, 1.1), rrect(0.45, 1.35, 0.15, 0.85, 2, PM, sx, 1.1)],
             MAT_DARK, False)
    loft('OutletGround%d' % idx,
         [ering(0.0, -2.2, 0.85, 0.85, 0.3, 14, PM), ering(0.0, -2.2, 0.85, 0.85, 0.85, 14, PM)],
         MAT_DARK, False)

# strain relief at the top of the strip
relief = [(36.6, 2.7), (37.9, 2.7), (37.9, 2.1), (38.4, 2.1), (38.4, 2.5), (39.3, 2.5),
          (39.3, 1.9), (39.8, 1.9), (39.8, 2.2), (40.6, 2.2), (40.6, 1.5), (41.4, 1.3)]
loft('StrainRelief', [ering(0.0, 0.0, r, r, z, 16, SM) for (z, r) in relief], MAT_CORD, False)

# ---------------------------------------------------------------
# plug (pointing at the base of the strip) and looping cord
# ---------------------------------------------------------------
PLUG_A = Vector((-3.5, 0.0, 62.4))
PLUG_DIR = Vector((11.0, 0.0, -4.4)).normalized()
PLM = frame(PLUG_A, PLUG_DIR, Vector((0.0, 1.0, 0.0)))

plug_prof = [(0.0, 1.3, 1.3, 1.0), (2.5, 1.9, 1.6, 1.0), (5.5, 3.4, 2.1, 1.0),
             (9.5, 3.7, 2.2, 1.0), (10.3, 3.2, 1.8, 0.8)]
loft('Plug', [rrect(hx, hy, r, z, 4, PLM) for (z, hx, hy, r) in plug_prof], MAT_CORD, True)
for sx in (-1.5, 1.5):
    loft('Prong',
         [rrect(0.22, 0.9, 0.08, 10.0, 1, PLM, sx, 0.0), rrect(0.22, 0.9, 0.08, 13.2, 1, PLM, sx, 0.0)],
         MAT_METAL, False)

cord_pts = [
    SM @ Vector((0.0, 0.0, 35.0)),
    SM @ Vector((0.0, 0.0, 40.5)),
    Vector((18.6, 0.0, 94.0)),
    Vector((14.0, 0.0, 97.2)),
    Vector((6.4, 0.0, 98.4)),
    Vector((-1.6, 0.0, 96.2)),
    Vector((-8.0, 0.0, 90.6)),
    Vector((-12.0, 0.0, 83.2)),
    Vector((-13.3, 0.0, 75.2)),
    Vector((-11.8, 0.0, 68.5)),
    Vector((-8.2, 0.0, 64.3)),
    PLUG_A,
    PLUG_A + PLUG_DIR * 1.5,
]
tube('Cord', catmull(cord_pts, 8), 1.1, MAT_CORD, 14)
