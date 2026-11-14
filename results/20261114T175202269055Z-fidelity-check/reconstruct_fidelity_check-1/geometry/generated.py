import bpy
import math
from mathutils import Vector, Matrix

# ---------------------------------------------------------------
# Clear the starting scene
# ---------------------------------------------------------------
for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob, do_unlink=True)
for me in list(bpy.data.meshes):
    bpy.data.meshes.remove(me)
for ma in list(bpy.data.materials):
    bpy.data.materials.remove(ma)

COL = bpy.context.scene.collection


def make_mat(name, rgb):
    m = bpy.data.materials.new(name)
    rgba = (rgb[0], rgb[1], rgb[2], 1.0)
    m.diffuse_color = rgba
    try:
        m.use_nodes = True
    except Exception:
        pass
    try:
        nt = m.node_tree
        if nt is not None:
            for node in nt.nodes:
                if node.type == 'BSDF_PRINCIPLED':
                    node.inputs['Base Color'].default_value = rgba
    except Exception:
        pass
    return m


MAT_BODY = make_mat('Body', (0.95, 0.93, 0.90))
MAT_STRIP = make_mat('Strip', (0.90, 0.90, 0.86))
MAT_PLATE = make_mat('OutletPlate', (0.80, 0.80, 0.77))
MAT_CORD = make_mat('Cord', (0.78, 0.78, 0.76))
MAT_BLACK = make_mat('Black', (0.02, 0.02, 0.02))
MAT_WHITE = make_mat('EyeWhite', (1.0, 1.0, 1.0))
MAT_BLUE = make_mat('Tears', (0.10, 0.50, 0.95))
MAT_METAL = make_mat('Prongs', (0.35, 0.35, 0.38))
MAT_BASE = make_mat('Table', (0.70, 0.70, 0.70))


# ---------------------------------------------------------------
# Geometry helpers (pure from_pydata lofts)
# ---------------------------------------------------------------
def loft(name, rings, mat, matrix=None, smooth=True, caps=True, zmin=None):
    n = len(rings[0])
    verts = []
    for r in rings:
        for p in r:
            v = Vector((p[0], p[1], p[2]))
            if matrix is not None:
                v = matrix @ v
            z = v.z
            if zmin is not None and z < zmin:
                z = zmin
            verts.append((v.x, v.y, z))
    faces = []
    for i in range(len(rings) - 1):
        a = i * n
        b = (i + 1) * n
        for j in range(n):
            k = (j + 1) % n
            faces.append((a + j, a + k, b + k, b + j))
    if caps:
        faces.append(tuple(range(n - 1, -1, -1)))
        last = (len(rings) - 1) * n
        faces.append(tuple(range(last, last + n)))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    if smooth:
        try:
            me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
        except Exception:
            pass
    if mat is not None:
        me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    COL.objects.link(ob)
    return ob


def ellipsoid(name, center, radii, mat, matrix=None, seg=24, nr=12, zmin=None):
    rings = []
    for i in range(nr + 1):
        lat = -1.55 + 3.10 * i / nr
        cr = math.cos(lat)
        sz = math.sin(lat)
        ring = []
        for j in range(seg):
            a = 2.0 * math.pi * j / seg
            ring.append((center[0] + radii[0] * cr * math.cos(a),
                         center[1] + radii[1] * cr * math.sin(a),
                         center[2] + radii[2] * sz))
        rings.append(ring)
    return loft(name, rings, mat, matrix=matrix, zmin=zmin)


def tube(name, pts, radii, mat, seg=16, round_ends=True, zmin=None):
    pts = [Vector((p[0], p[1], p[2])) for p in pts]
    n = len(pts)
    if isinstance(radii, (int, float)):
        radii = [float(radii)] * n
    tans = []
    for i in range(n):
        a = pts[max(i - 1, 0)]
        b = pts[min(i + 1, n - 1)]
        t = b - a
        if t.length < 1e-9:
            t = Vector((0.0, 0.0, 1.0))
        t.normalize()
        tans.append(t)
    t0 = tans[0]
    ref = Vector((0.0, 0.0, 1.0)) if abs(t0.z) < 0.9 else Vector((1.0, 0.0, 0.0))
    nrm = ref - t0 * ref.dot(t0)
    nrm.normalize()
    frames = []
    for i in range(n):
        t = tans[i]
        nrm = nrm - t * nrm.dot(t)
        if nrm.length < 1e-6:
            nrm = t.orthogonal()
        nrm.normalize()
        frames.append((nrm.copy(), t.cross(nrm)))

    def ring(c, r, nv, bv):
        out = []
        for j in range(seg):
            a = 2.0 * math.pi * j / seg
            out.append(c + (nv * math.cos(a) + bv * math.sin(a)) * r)
        return out

    rings = []
    steps = 5
    if round_ends:
        for k in range(1, steps):
            a = (k / steps) * math.pi * 0.5
            rings.append(ring(pts[0] - tans[0] * radii[0] * math.cos(a), radii[0] * math.sin(a), frames[0][0], frames[0][1]))
    for i in range(n):
        rings.append(ring(pts[i], radii[i], frames[i][0], frames[i][1]))
    if round_ends:
        for k in range(steps - 1, 0, -1):
            a = (k / steps) * math.pi * 0.5
            rings.append(ring(pts[-1] + tans[-1] * radii[-1] * math.cos(a), radii[-1] * math.sin(a), frames[-1][0], frames[-1][1]))
    return loft(name, rings, mat, zmin=zmin)


def smooth_path(pts, sub=6):
    P = [Vector(p) for p in pts]
    out = []
    m = len(P)
    for i in range(m - 1):
        p0 = P[max(i - 1, 0)]
        p1 = P[i]
        p2 = P[i + 1]
        p3 = P[min(i + 2, m - 1)]
        for s in range(sub):
            t = s / sub
            v = (p1 * 2.0 + (p2 - p0) * t + (p0 * 2.0 - p1 * 5.0 + p2 * 4.0 - p3) * (t * t) + (p1 * 3.0 - p0 - p2 * 3.0 + p3) * (t * t * t)) * 0.5
            out.append(v)
    out.append(P[-1].copy())
    return out


def rrect(hw, hd, r, z, k=5):
    lim = min(hw, hd) * 0.999
    r = max(min(r, lim), 0.01)
    pts = []
    corners = [(hw - r, hd - r, 0.0), (-(hw - r), hd - r, 90.0), (-(hw - r), -(hd - r), 180.0), (hw - r, -(hd - r), 270.0)]
    for cx, cy, a0 in corners:
        for i in range(k + 1):
            a = math.radians(a0 + 90.0 * i / k)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a), z))
    return pts


def prism(name, hw, hd, r, z0, z1, mat, matrix, smooth=False):
    return loft(name, [rrect(hw, hd, r, z0), rrect(hw, hd, r, z1)], mat, matrix=matrix, smooth=smooth)


def frame(origin, zdir):
    z = Vector(zdir).normalized()
    up = Vector((0.0, 1.0, 0.0))
    x = up.cross(z)
    if x.length < 1e-6:
        x = Vector((1.0, 0.0, 0.0))
    x.normalize()
    y = z.cross(x)
    return Matrix(((x.x, y.x, z.x, origin[0]),
                   (x.y, y.y, z.y, origin[1]),
                   (x.z, y.z, z.z, origin[2]),
                   (0.0, 0.0, 0.0, 1.0)))


# ---------------------------------------------------------------
# Table / ground slab (the horizontal line the figure slumps on)
# ---------------------------------------------------------------
prism('Table', 46.0, 30.0, 6.0, 0.0, 1.0, MAT_BASE, Matrix.Translation((0.0, -2.0, 0.0)), smooth=False)

# ---------------------------------------------------------------
# Torso: hunched blob, broad shoulders, flat seat on the table
# profile entries: (z, centre x, radius x)
# ---------------------------------------------------------------
PROFILE = [
    (0.0, 8.0, 23.0),
    (5.0, 8.0, 24.5),
    (13.0, 7.0, 26.0),
    (22.0, 5.0, 27.5),
    (31.0, 4.0, 28.5),
    (38.0, 3.5, 27.0),
    (43.0, 3.5, 23.0),
    (46.5, 5.0, 16.0),
    (48.5, 7.0, 8.0),
]
TY = 2.0
TRY = 0.7


def torso_at(z):
    if z <= PROFILE[0][0]:
        return PROFILE[0][1], PROFILE[0][2]
    for i in range(len(PROFILE) - 1):
        z0, c0, r0 = PROFILE[i]
        z1, c1, r1 = PROFILE[i + 1]
        if z <= z1:
            t = (z - z0) / (z1 - z0)
            return c0 + (c1 - c0) * t, r0 + (r1 - r0) * t
    return PROFILE[-1][1], PROFILE[-1][2]


torso_rings = []
for z, cx, rx in PROFILE:
    ring = []
    for j in range(40):
        a = 2.0 * math.pi * j / 40
        ring.append((cx + rx * math.cos(a), TY + rx * TRY * math.sin(a), z))
    torso_rings.append(ring)
loft('Torso', torso_rings, MAT_BODY)

# left shoulder hump (viewer's left)
ellipsoid('ShoulderHump', (-15.5, 0.0, 36.5), (9.5, 11.0, 8.0), MAT_BODY)

# slumped arm: upper arm drops from the shoulder to an elbow on the table,
# forearm lies along the table across the front, tapering to the right
arm_ctrl = [
    (-16.0, -2.0, 37.0, 8.5),
    (-19.0, -7.0, 25.0, 9.0),
    (-23.0, -12.0, 12.0, 8.5),
    (-22.0, -15.0, 8.0, 7.5),
    (-12.0, -18.0, 7.0, 6.3),
    (0.0, -19.0, 5.2, 4.6),
    (11.0, -19.0, 3.2, 2.6),
]
arm_s = smooth_path(arm_ctrl, 5)
tube('Arm', [(v[0], v[1], v[2]) for v in arm_s], [v[3] for v in arm_s], MAT_BODY, seg=20, zmin=0.0)

# ---------------------------------------------------------------
# Power strip head: tilted, 3/4 turned, flaring at its base into the torso (neck)
# local frame: z along the strip, outlet face is local -Y
# ---------------------------------------------------------------
SM = Matrix.Translation((16.0, 1.0, 64.0)) @ Matrix.Rotation(math.radians(15.0), 4, 'Y') @ Matrix.Rotation(math.radians(-50.0), 4, 'Z')
SHW = 6.0
SHD = 5.5
SR = 1.8
srings = []
for z, s in [(-30.0, 2.0), (-26.0, 1.85), (-23.0, 1.65), (-20.0, 1.42), (-17.0, 1.22), (-14.0, 1.08), (-11.0, 1.0), (19.0, 1.0)]:
    srings.append(rrect(SHW * s, SHD * s, SR * s, z))
for adeg in (30.0, 60.0, 88.0):
    ar = math.radians(adeg)
    inset = 1.5 * (1.0 - math.cos(ar))
    srings.append(rrect(SHW - inset, SHD - inset, max(SR - inset * 0.6, 0.3), 19.0 + 1.5 * math.sin(ar)))
loft('PowerStripNeck', srings, MAT_STRIP, matrix=SM)

# two outlets on the front face of the strip (each with two slots and a ground hole)
for idx, zc in enumerate((11.5, 1.0)):
    FM = SM @ Matrix.Translation((0.0, -SHD, zc)) @ Matrix.Rotation(math.radians(90.0), 4, 'X')
    loft('OutletPlate_%d' % idx, [rrect(4.6, 4.3, 1.5, -0.3), rrect(4.6, 4.3, 1.5, 0.45), rrect(4.3, 4.0, 1.3, 0.6)], MAT_PLATE, matrix=FM, smooth=False)
    prism('OutletSlotL_%d' % idx, 0.42, 1.5, 0.15, 0.3, 0.9, MAT_BLACK, FM @ Matrix.Translation((-1.8, 1.2, 0.0)))
    prism('OutletSlotR_%d' % idx, 0.42, 1.5, 0.15, 0.3, 0.9, MAT_BLACK, FM @ Matrix.Translation((1.8, 1.2, 0.0)))
    prism('OutletGround_%d' % idx, 0.9, 0.9, 0.89, 0.3, 0.9, MAT_BLACK, FM @ Matrix.Translation((0.0, -2.3, 0.0)))

# ribbed strain relief where the cord leaves the top of the strip
loft('StrainBase', [rrect(3.0, 3.0, 2.99, 20.0), rrect(2.2, 2.2, 2.19, 22.2)], MAT_CORD, matrix=SM, smooth=False)
prism('StrainCore', 1.45, 1.45, 1.44, 20.0, 26.8, MAT_CORD, SM)
for i, (z0, rr) in enumerate([(22.3, 2.4), (23.4, 2.2), (24.5, 2.0), (25.6, 1.8)]):
    prism('StrainRib_%d' % i, rr, rr, rr * 0.995, z0, z0 + 0.7, MAT_CORD, SM)

# ---------------------------------------------------------------
# Cord: leaves the strip top, loops up and over to the left, comes back down
# and ends in a plug pushed into the lower-left of the strip (plugged into itself)
# ---------------------------------------------------------------
PLUG_S = Vector((-7.0, -4.0, 61.0))
PLUG_T = Vector((12.6, 1.0, 51.4))
plug_dir = (PLUG_T - PLUG_S).normalized()

c0 = SM @ Vector((0.0, 0.0, 19.5))
c1 = SM @ Vector((0.0, 0.0, 27.0))
cord_ctrl = [
    (c0.x, c0.y, c0.z),
    (c1.x, c1.y, c1.z),
    (21.2, 1.0, 94.6),
    (15.5, 1.0, 97.5),
    (7.0, 1.0, 98.5),
    (-1.7, 1.0, 96.6),
    (-8.6, 1.0, 91.2),
    (-12.4, 1.0, 83.4),
    (-13.4, 0.5, 75.7),
    (-12.2, -1.0, 68.5),
    (-10.0, -3.0, 63.8),
    (PLUG_S.x, PLUG_S.y, PLUG_S.z),
]
cord_pts = smooth_path(cord_ctrl, 8)
tube('Cord', cord_pts, 1.2, MAT_CORD, seg=14)

PM = frame(PLUG_S, plug_dir)
plug_sections = [
    (-0.6, 1.5, 1.5, 1.45),
    (2.5, 1.9, 1.8, 1.6),
    (5.5, 3.6, 2.5, 1.4),
    (8.5, 4.7, 3.0, 1.2),
    (12.4, 4.8, 3.0, 1.0),
    (13.0, 4.3, 2.6, 0.8),
]
loft('Plug', [rrect(hw, hd, r, z) for z, hw, hd, r in plug_sections], MAT_STRIP, matrix=PM)
prism('PlugCollar', 2.0, 2.0, 1.99, 0.2, 1.0, MAT_CORD, PM)
prism('ProngA', 0.3, 0.9, 0.1, 12.8, 17.5, MAT_METAL, PM @ Matrix.Translation((-1.7, 0.0, 0.0)))
prism('ProngB', 0.3, 0.9, 0.1, 12.8, 17.5, MAT_METAL, PM @ Matrix.Translation((1.7, 0.0, 0.0)))


# ---------------------------------------------------------------
# Crying face on the chest (front of torso, facing -Y)
# ---------------------------------------------------------------
def face_mat(x, z, lift=0.0):
    cx, rx = torso_at(z)
    ry = rx * TRY
    u = max(-0.95, min(0.95, (x - cx) / rx))
    y = TY - ry * math.sqrt(1.0 - u * u)
    nx = (x - cx) / (rx * rx)
    ny = (y - TY) / (ry * ry)
    l = math.hypot(nx, ny)
    nx /= l
    ny /= l
    phi = math.atan2(nx, -ny)
    return Matrix.Translation((x + nx * lift, y + ny * lift, z)) @ Matrix.Rotation(phi, 4, 'Z')


def tilt(deg):
    return Matrix.Rotation(math.radians(deg), 4, 'Y')


# viewer-left eye: larger, heavy pupil
EL = face_mat(6.9, 31.8) @ tilt(8.0)
ellipsoid('EyeL_Rim', (0.0, 0.0, 0.0), (3.3, 0.5, 2.0), MAT_BLACK, matrix=EL, seg=20, nr=8)
ellipsoid('EyeL_White', (0.0, 0.0, 0.0), (2.9, 0.75, 1.6), MAT_WHITE, matrix=EL, seg=20, nr=8)
ellipsoid('EyeL_Pupil', (0.3, -0.6, 0.0), (1.5, 0.5, 1.35), MAT_BLACK, matrix=EL, seg=16, nr=8)

# viewer-right eye: smaller, squinting, sits a little higher
ER = face_mat(15.5, 33.9) @ tilt(-10.0)
ellipsoid('EyeR_Rim', (0.0, 0.0, 0.0), (2.4, 0.5, 1.5), MAT_BLACK, matrix=ER, seg=20, nr=8)
ellipsoid('EyeR_White', (0.0, 0.0, 0.0), (2.05, 0.75, 1.15), MAT_WHITE, matrix=ER, seg=20, nr=8)
ellipsoid('EyeR_Pupil', (-0.2, -0.6, -0.1), (1.0, 0.5, 0.95), MAT_BLACK, matrix=ER, seg=16, nr=8)

# brows
ellipsoid('BrowL', (0.0, -0.2, 0.0), (3.5, 0.45, 0.45), MAT_BLACK, matrix=face_mat(7.0, 35.5) @ tilt(8.0), seg=12, nr=8)
ellipsoid('BrowR', (0.0, -0.2, 0.0), (2.6, 0.45, 0.4), MAT_BLACK, matrix=face_mat(15.8, 36.8) @ tilt(-14.0), seg=12, nr=8)

# nose, nostril line, mouth, lower lip line
ellipsoid('Nose', (0.0, -0.3, 0.0), (1.2, 1.6, 2.4), MAT_BODY, matrix=face_mat(12.4, 30.6) @ tilt(-8.0), seg=16, nr=8)
ellipsoid('NoseLine', (0.0, -0.3, 0.0), (1.3, 0.5, 0.3), MAT_BLACK, matrix=face_mat(12.2, 28.4) @ tilt(5.0), seg=12, nr=6)
ellipsoid('Mouth', (0.0, -0.1, 0.0), (2.7, 0.45, 0.4), MAT_BLACK, matrix=face_mat(11.2, 26.4) @ tilt(-6.0), seg=12, nr=6)
ellipsoid('LipLine', (0.0, -0.1, 0.0), (1.4, 0.35, 0.28), MAT_BLACK, matrix=face_mat(11.6, 24.8) @ tilt(-4.0), seg=12, nr=6)

# blue tears running down from both eyes
tear_paths = [
    [(4.9, 30.0), (4.7, 27.5), (5.0, 24.5), (5.3, 22.0)],
    [(17.4, 32.0), (17.3, 27.0), (16.9, 21.0), (16.6, 15.5)],
    [(15.0, 31.8), (15.3, 28.5), (15.4, 25.5)],
]
for i, path in enumerate(tear_paths):
    pts3 = [face_mat(x, z, 0.15).to_translation() for x, z in path]
    pts3 = smooth_path([(p.x, p.y, p.z) for p in pts3], 4)
    tube('Tear_%d' % i, pts3, 0.45, MAT_BLUE, seg=10)
    ex, ez = path[-1]
    ellipsoid('TearDrop_%d' % i, (0.0, 0.0, 0.0), (0.7, 0.6, 0.95), MAT_BLUE, matrix=face_mat(ex, ez, 0.2), seg=12, nr=8)
