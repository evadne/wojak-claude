import bpy
import math
from mathutils import Vector, Matrix

# ---------- clear scene ----------
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
for m in list(bpy.data.meshes):
    bpy.data.meshes.remove(m)

S = 100.0 / 575.0
COL = bpy.context.scene.collection


def P(px, py, y=0.0):
    # drawing pixel coords -> world (front view, X right, Z up)
    return Vector(((px - 205.0) * S, y, (585.0 - py) * S))


def make_mat(name, rgba):
    m = bpy.data.materials.new(name)
    m.diffuse_color = rgba
    return m


MAT_BODY = make_mat('BodyWhite', (0.93, 0.93, 0.90, 1.0))
MAT_STRIP = make_mat('StripWhite', (0.97, 0.97, 0.95, 1.0))
MAT_DARK = make_mat('InkDark', (0.03, 0.03, 0.03, 1.0))
MAT_BLUE = make_mat('TearBlue', (0.10, 0.50, 0.90, 1.0))
MAT_METAL = make_mat('Metal', (0.60, 0.60, 0.62, 1.0))


def finish(o, name, mat, smooth=True):
    o.name = name
    o.data.materials.append(mat)
    if smooth:
        for p in o.data.polygons:
            p.use_smooth = True
    return o


def mesh_obj(name, verts, faces, mat, smooth=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.update()
    o = bpy.data.objects.new(name, me)
    COL.objects.link(o)
    return finish(o, name, mat, smooth)


def ellipsoid(name, c, radii, mat):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=1.0, location=tuple(c))
    o = bpy.context.active_object
    o.scale = radii
    return finish(o, name, mat)


def frustum(name, p1, p2, r1, r2, mat, verts=32):
    d = p2 - p1
    mid = (p1 + p2) * 0.5
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r1, radius2=r2, depth=d.length, location=tuple(mid))
    o = bpy.context.active_object
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = d.to_track_quat('Z', 'Y')
    return finish(o, name, mat)


def box(name, size, matrix, mat, bevel=0.0):
    x, y, z = size[0] * 0.5, size[1] * 0.5, size[2] * 0.5
    verts = [(-x, -y, -z), (x, -y, -z), (x, y, -z), (-x, y, -z),
             (-x, -y, z), (x, -y, z), (x, y, z), (-x, y, z)]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
             (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    o = mesh_obj(name, verts, faces, mat, smooth=False)
    o.matrix_world = matrix
    if bevel > 0.0:
        md = o.modifiers.new('Bevel', 'BEVEL')
        md.width = bevel
        md.segments = 3
    return o


def catmull(pts, sub=6):
    n = len(pts)
    if n < 2:
        return list(pts)
    out = []
    for i in range(n - 1):
        p0 = pts[max(i - 1, 0)]
        p1 = pts[i]
        p2 = pts[i + 1]
        p3 = pts[min(i + 2, n - 1)]
        for j in range(sub):
            t = j / sub
            q = 0.5 * (2.0 * p1 + (p2 - p0) * t
                       + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * (t * t)
                       + (3.0 * p1 - p0 - 3.0 * p2 + p3) * (t * t * t))
            out.append(q)
    out.append(pts[-1].copy())
    return out


def tube(name, pts, radius, mat, seg=12):
    n = len(pts)
    tangents = []
    for i in range(n):
        a = pts[max(i - 1, 0)]
        b = pts[min(i + 1, n - 1)]
        t = b - a
        if t.length < 1e-9:
            t = Vector((0.0, 0.0, 1.0))
        tangents.append(t.normalized())
    t0 = tangents[0]
    ref = Vector((0.0, 1.0, 0.0)) if abs(t0.y) < 0.9 else Vector((1.0, 0.0, 0.0))
    nrm = t0.cross(ref).normalized()
    verts = []
    faces = []
    for i in range(n):
        t = tangents[i]
        nrm = nrm - t * nrm.dot(t)
        if nrm.length < 1e-6:
            nrm = t.orthogonal()
        nrm.normalize()
        bn = t.cross(nrm)
        for k in range(seg):
            ang = 2.0 * math.pi * k / seg
            verts.append(pts[i] + (nrm * math.cos(ang) + bn * math.sin(ang)) * radius)
    for i in range(n - 1):
        for k in range(seg):
            k2 = (k + 1) % seg
            faces.append((i * seg + k, i * seg + k2, (i + 1) * seg + k2, (i + 1) * seg + k))
    faces.append(tuple(reversed(range(seg))))
    faces.append(tuple(range((n - 1) * seg, n * seg)))
    return mesh_obj(name, verts, faces, mat, smooth=True)


# ---------- body (hunched torso blob) ----------
ELLS = []


def body_ell(name, px, py, rx_px, rz_px, ry, y=0.0):
    c = P(px, py, y)
    radii = (rx_px * S, ry, rz_px * S)
    ELLS.append((c, radii))
    return ellipsoid(name, c, radii, MAT_BODY)


body_ell('TorsoMain', 210, 465, 150, 118, 16.0)
body_ell('TorsoUpper', 248, 368, 100, 72, 13.0)
body_ell('TorsoBridge', 165, 365, 70, 55, 11.5)
body_ell('ShoulderL', 108, 385, 55, 55, 10.5)
body_ell('ShoulderR', 325, 395, 45, 45, 9.5)

# arms (tapered capsules reaching the ground)
aL1 = P(92, 410, -2.0)
aL2 = P(40, 550, -3.0)
frustum('ArmL', aL1, aL2, 8.0, 5.5, MAT_BODY)
ellipsoid('ArmLTop', aL1, (8.0, 8.0, 8.0), MAT_BODY)
ellipsoid('HandL', aL2, (5.5, 5.5, 5.5), MAT_BODY)
aR1 = P(325, 405, -2.0)
aR2 = P(362, 552, -3.0)
frustum('ArmR', aR1, aR2, 7.0, 5.2, MAT_BODY)
ellipsoid('ArmRTop', aR1, (7.0, 7.0, 7.0), MAT_BODY)
ellipsoid('HandR', aR2, (5.2, 5.2, 5.2), MAT_BODY)

# neck flaring up into the power strip
frustum('Neck', P(265, 350), P(292, 295), 11.0, 8.0, MAT_BODY, verts=40)


def front_y(x, z):
    best = None
    for c, r in ELLS:
        q = 1.0 - ((x - c.x) / r[0]) ** 2 - ((z - c.z) / r[2]) ** 2
        if q > 0.0:
            y = c.y - r[1] * math.sqrt(q)
            if best is None or y < best:
                best = y
    if best is None:
        best = 0.0
    return best


def front(px, py, off=0.0):
    v = P(px, py)
    v.y = front_y(v.x, v.z) - off
    return v


def surf_line(name, pxpts, radius, mat, off=0.15, closed=False):
    pts2 = [Vector(p) for p in pxpts]
    if closed:
        pts2.append(pts2[0].copy())
    dense = catmull(pts2, 6)
    pts3 = [front(p.x, p.y, off) for p in dense]
    return tube(name, pts3, radius, mat, seg=10)


# ---------- power strip (head / neck) ----------
STRIP_W = 12.0
STRIP_D = 10.0
STRIP_L = 38.0
theta = math.atan2(35.0, 215.0)
strip_c = P(307, 200)
M = (Matrix.Translation(strip_c)
     @ Matrix.Rotation(theta, 4, 'Y')
     @ Matrix.Rotation(math.radians(-40.0), 4, 'Z'))
box('PowerStrip', (STRIP_W, STRIP_D, STRIP_L), M, MAT_STRIP, bevel=1.2)

fy = -STRIP_D * 0.5
idx = 0
for zc in (8.5, -2.0):
    idx += 1
    box('OutletPlate%d' % idx, (7.0, 0.5, 7.6), M @ Matrix.Translation((0.0, fy - 0.1, zc)), MAT_STRIP, bevel=0.2)
    box('OutletFrame%d' % idx, (7.6, 0.2, 8.2), M @ Matrix.Translation((0.0, fy - 0.02, zc)), MAT_DARK)
    for sx in (-1.5, 1.5):
        box('OutletSlot%d' % idx, (0.6, 0.4, 2.0), M @ Matrix.Translation((sx, fy - 0.4, zc + 1.0)), MAT_DARK)
    bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=0.65, depth=0.4)
    g = bpy.context.active_object
    g.matrix_world = (M @ Matrix.Translation((0.0, fy - 0.4, zc - 2.0))
                      @ Matrix.Rotation(math.pi * 0.5, 4, 'X'))
    finish(g, 'OutletGround%d' % idx, MAT_DARK)

# strain relief on top of the strip
axis = Vector((math.sin(theta), 0.0, math.cos(theta)))
top = strip_c + axis * (STRIP_L * 0.5)
frustum('StrainRelief', top - axis * 0.5, top + axis * 4.0, 2.7, 2.0, MAT_STRIP)
for i in range(3):
    a = top + axis * (0.8 + i * 1.0)
    frustum('StrainRib%d' % i, a, a + axis * 0.5, 3.0, 3.0, MAT_STRIP)

# ---------- cable looping over to the plug ----------
cable_ctrl = [top + axis * 2.0, top + axis * 5.5]
for px, py in ((318, 40), (295, 25), (255, 19), (212, 25), (172, 50), (142, 98),
               (126, 150), (127, 200), (145, 232), (163, 242)):
    cable_ctrl.append(P(px, py))
tube('Cable', catmull(cable_ctrl, 10), 1.5, MAT_STRIP, seg=16)

# ---------- plug stuck into the shoulder ----------
frustum('PlugCollar', P(158, 239), P(181, 250), 1.9, 3.0, MAT_STRIP)
pb1 = P(178, 248)
pb2 = P(232, 282)
pd = pb2 - pb1
plen = pd.length
PM = Matrix.Translation((pb1 + pb2) * 0.5) @ pd.to_track_quat('Z', 'Y').to_matrix().to_4x4()
box('PlugBody', (6.0, 8.5, plen), PM, MAT_STRIP, bevel=1.0)
for sy in (-1.8, 1.8):
    box('PlugProng', (1.8, 0.4, 2.6), PM @ Matrix.Translation((0.0, sy, plen * 0.5 + 1.1)), MAT_METAL)

# ---------- face on the chest ----------
LINE_R = 0.35
surf_line('EyeOutlineL', [(222, 392), (245, 390), (265, 405), (250, 418), (228, 410)], LINE_R, MAT_DARK, closed=True)
surf_line('EyeOutlineR', [(278, 385), (300, 382), (303, 392), (290, 402), (280, 396)], LINE_R, MAT_DARK, closed=True)
ellipsoid('PupilL', front(245, 405, 0.1), (1.5, 0.5, 1.2), MAT_DARK)
ellipsoid('PupilR', front(291, 391, 0.1), (1.0, 0.45, 0.85), MAT_DARK)

ellipsoid('NoseBump', front(283, 413, 0.0), (1.0, 1.1, 2.4), MAT_BODY)
surf_line('NoseLine', [(287, 400), (282, 415), (276, 426), (285, 428)], LINE_R, MAT_DARK, off=1.3)

surf_line('Mouth', [(248, 430), (262, 434), (280, 431)], LINE_R, MAT_DARK)
surf_line('LowerLip', [(256, 442), (266, 444), (276, 441)], LINE_R * 0.85, MAT_DARK)

# tears
TEAR_R = 0.45
surf_line('TearL1', [(232, 416), (230, 435), (234, 458)], TEAR_R, MAT_BLUE)
surf_line('TearL2', [(240, 421), (241, 432), (240, 442)], TEAR_R, MAT_BLUE)
surf_line('TearR1', [(292, 406), (296, 440), (294, 470), (297, 500)], TEAR_R, MAT_BLUE)
surf_line('TearR2', [(304, 400), (307, 418), (305, 432)], TEAR_R, MAT_BLUE)
