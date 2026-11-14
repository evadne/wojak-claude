import bpy
import math
from mathutils import Vector, Matrix

# ---------------------------------------------------------------
# Clear the starting scene
# ---------------------------------------------------------------
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
for coll in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
    for blk in list(coll):
        try:
            coll.remove(blk)
        except Exception:
            pass

scene = bpy.context.scene
root = scene.collection
OBJS = []


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------
def make_mat(name, rgb):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (rgb[0], rgb[1], rgb[2], 1.0)
    try:
        if not m.node_tree:
            m.use_nodes = True
    except Exception:
        pass
    try:
        nt = m.node_tree
        if nt:
            for nd in nt.nodes:
                if nd.type == 'BSDF_PRINCIPLED':
                    nd.inputs['Base Color'].default_value = (rgb[0], rgb[1], rgb[2], 1.0)
                    nd.inputs['Roughness'].default_value = 0.6
    except Exception:
        pass
    return m


def add_mesh(name, verts, faces, mat, smooth=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata([(float(v[0]), float(v[1]), float(v[2])) for v in verts], [], faces)
    me.update()
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    root.objects.link(ob)
    OBJS.append(ob)
    return ob


def skin(name, rings, mat, smooth=True, xf=None, cap=True):
    m = len(rings[0])
    verts = []
    for ring in rings:
        for p in ring:
            v = Vector(p)
            if xf is not None:
                v = xf @ v
            verts.append((v.x, v.y, v.z))
    faces = []
    for i in range(len(rings) - 1):
        for j in range(m):
            a = i * m + j
            b = i * m + (j + 1) % m
            faces.append((a, b, b + m, a + m))
    if cap:
        faces.append(tuple(range(m - 1, -1, -1)))
        k = (len(rings) - 1) * m
        faces.append(tuple(range(k, k + m)))
    return add_mesh(name, verts, faces, mat, smooth)


def rrect(w, h, r, seg=5):
    r = max(min(r, w * 0.5 - 0.01, h * 0.5 - 0.01), 0.01)
    cx = w * 0.5 - r
    cy = h * 0.5 - r
    pts = []
    for c, sgn in enumerate(((1, 1), (-1, 1), (-1, -1), (1, -1))):
        for k in range(seg + 1):
            a = (c + k / seg) * math.pi * 0.5
            pts.append((sgn[0] * cx + r * math.cos(a), sgn[1] * cy + r * math.sin(a)))
    return pts


def rect(w, h):
    return [(-w * 0.5, -h * 0.5), (w * 0.5, -h * 0.5), (w * 0.5, h * 0.5), (-w * 0.5, h * 0.5)]


def circle(r, n=16):
    return [(r * math.cos(2.0 * math.pi * i / n), r * math.sin(2.0 * math.pi * i / n)) for i in range(n)]


def prof_ring(profile, z, ox=0.0, oy=0.0):
    return [(p[0] + ox, p[1] + oy, z) for p in profile]


def lathe(name, rz_list, mat, xf, n=16, ox=0.0, oy=0.0, smooth=True):
    rings = [prof_ring(circle(r, n), z, ox, oy) for (r, z) in rz_list]
    return skin(name, rings, mat, smooth=smooth, xf=xf)


def ellipsoid(name, center, radii, mat, rot=None, segs=32, rings=16, zmin=None):
    verts = []
    c = Vector(center)

    def place(x, y, z):
        v = Vector((x, y, z))
        if rot is not None:
            v = rot @ v
        v = v + c
        if zmin is not None and v.z < zmin:
            v.z = zmin
        return (v.x, v.y, v.z)

    verts.append(place(0.0, 0.0, radii[2]))
    for i in range(1, rings):
        phi = math.pi * i / rings
        for j in range(segs):
            th = 2.0 * math.pi * j / segs
            verts.append(place(radii[0] * math.sin(phi) * math.cos(th), radii[1] * math.sin(phi) * math.sin(th), radii[2] * math.cos(phi)))
    verts.append(place(0.0, 0.0, -radii[2]))
    last = len(verts) - 1
    faces = []
    for j in range(segs):
        faces.append((0, 1 + j, 1 + (j + 1) % segs))
    for i in range(rings - 2):
        for j in range(segs):
            u0 = 1 + i * segs + j
            u1 = 1 + i * segs + (j + 1) % segs
            l0 = u0 + segs
            l1 = u1 + segs
            faces.append((u0, l0, l1, u1))
    base = 1 + (rings - 2) * segs
    for j in range(segs):
        faces.append((last, base + (j + 1) % segs, base + j))
    return add_mesh(name, verts, faces, mat, True)


def catmull(points, per=8):
    pts = [Vector(p) for p in points]
    ext = [pts[0] * 2.0 - pts[1]] + pts + [pts[-1] * 2.0 - pts[-2]]
    out = []
    for i in range(1, len(ext) - 2):
        p0 = ext[i - 1]
        p1 = ext[i]
        p2 = ext[i + 1]
        p3 = ext[i + 2]
        for k in range(per):
            t = k / per
            t2 = t * t
            t3 = t2 * t
            out.append(0.5 * ((2.0 * p1) + (p2 - p0) * t + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t2 + (3.0 * p1 - p0 - 3.0 * p2 + p3) * t3))
    out.append(pts[-1].copy())
    return out


def tube(name, points, radius, mat, segs=12, per=8):
    path = catmull(points, per)
    n = len(path)
    tans = []
    for i in range(n):
        t = path[min(i + 1, n - 1)] - path[max(i - 1, 0)]
        if t.length < 1e-9:
            t = Vector((0.0, 0.0, 1.0))
        tans.append(t.normalized())
    ref = Vector((0.0, 0.0, 1.0)) if abs(tans[0].z) < 0.9 else Vector((1.0, 0.0, 0.0))
    nrm = tans[0].cross(ref).normalized()
    rings = []
    for i in range(n):
        t = tans[i]
        if i > 0:
            q = tans[i - 1].rotation_difference(t)
            nrm = q @ nrm
        nrm = nrm - t * nrm.dot(t)
        if nrm.length < 1e-9:
            nrm = t.orthogonal()
        nrm.normalize()
        bn = t.cross(nrm)
        ring = []
        for s in range(segs):
            a = 2.0 * math.pi * s / segs
            ring.append(path[i] + radius * (math.cos(a) * nrm + math.sin(a) * bn))
        rings.append(ring)
    return skin(name, rings, mat, smooth=True)


def surf(c, r, x, z, off=0.0):
    k = 1.0 - ((x - c[0]) / r[0]) ** 2 - ((z - c[2]) / r[2]) ** 2
    return Vector((x, c[1] - r[1] * math.sqrt(max(k, 0.0)) - off, z))


# ---------------------------------------------------------------
# Materials
# ---------------------------------------------------------------
SKIN = make_mat('Skin', (0.96, 0.92, 0.85))
STRIP = make_mat('StripShell', (0.86, 0.88, 0.90))
PLATE = make_mat('SocketPlate', (0.98, 0.98, 0.97))
DARK = make_mat('Ink', (0.02, 0.02, 0.02))
CABLE = make_mat('Cable', (0.70, 0.70, 0.68))
PLUG = make_mat('PlugBody', (0.55, 0.56, 0.58))
GRIP = make_mat('PlugGrip', (0.28, 0.28, 0.30))
BRASS = make_mat('Prong', (0.80, 0.65, 0.25))
TEAR = make_mat('Tear', (0.12, 0.55, 0.92))
WHITE = make_mat('EyeWhite', (1.0, 1.0, 1.0))

# ---------------------------------------------------------------
# Body: slumped torso, back hump, big drooping head
# ---------------------------------------------------------------
HC = (10.0, -3.0, 33.0)
HR = (19.0, 16.5, 19.5)
TC = (-1.0, 5.0, 2.0)
TR = (34.0, 17.0, 14.0)

ellipsoid('Head', HC, HR, SKIN)
ellipsoid('BackHump', (-13.0, 5.0, 27.0), (15.0, 14.0, 23.0), SKIN, rot=Matrix.Rotation(math.radians(12.0), 3, 'Y'))
ellipsoid('Torso', TC, TR, SKIN, zmin=0.0)
ellipsoid('ShoulderR', (26.0, 5.0, 6.0), (11.0, 12.0, 9.0), SKIN, zmin=0.0)
ellipsoid('ShoulderL', (-27.0, 4.0, 6.0), (11.0, 12.0, 12.0), SKIN, zmin=0.0)

# ---------------------------------------------------------------
# Face (on the -Y side of the head)
# ---------------------------------------------------------------
def face_line(name, xz, radius, mat, off=0.25):
    pts = [surf(HC, HR, p[0], p[1], off) for p in xz]
    return tube(name, pts, radius, mat, segs=8, per=6)


# left eye (viewer left)
ellipsoid('EyeL_Rim', surf(HC, HR, 5.6, 36.6), (3.1, 0.45, 1.9), DARK, segs=20, rings=10)
ellipsoid('EyeL_White', surf(HC, HR, 5.6, 36.6), (2.7, 0.7, 1.5), WHITE, segs=20, rings=10)
ellipsoid('EyeL_Pupil', surf(HC, HR, 6.3, 36.5, 0.55), (1.2, 0.5, 1.1), DARK, segs=16, rings=8)
face_line('BrowL', [(2.2, 39.3), (4.8, 39.7), (7.6, 39.0), (9.6, 37.6)], 0.42, DARK)
# right eye
ellipsoid('EyeR_Rim', surf(HC, HR, 15.4, 38.0), (2.4, 0.45, 1.5), DARK, segs=20, rings=10)
ellipsoid('EyeR_White', surf(HC, HR, 15.4, 38.0), (2.0, 0.7, 1.1), WHITE, segs=20, rings=10)
ellipsoid('EyeR_Pupil', surf(HC, HR, 15.0, 37.9, 0.55), (0.9, 0.5, 0.85), DARK, segs=16, rings=8)
face_line('BrowR', [(12.6, 39.0), (14.6, 40.0), (17.2, 40.2), (18.6, 39.4)], 0.42, DARK)
# nose
ellipsoid('Nose', surf(HC, HR, 11.6, 34.6), (1.3, 1.5, 2.4), SKIN, segs=16, rings=8)
face_line('NoseLine', [(10.6, 37.2), (10.1, 35.0), (10.4, 33.3), (12.4, 33.0)], 0.3, DARK, off=0.35)
# mouth and chin
face_line('Mouth', [(7.6, 30.6), (9.8, 31.4), (12.2, 31.3), (14.4, 30.5)], 0.45, DARK)
face_line('Chin', [(9.6, 28.6), (11.2, 28.3), (12.8, 28.7)], 0.3, DARK)
# tears
face_line('TearL', [(4.6, 34.9), (4.3, 32.5), (4.6, 30.0), (4.4, 27.8)], 0.5, TEAR, off=0.3)
ellipsoid('TearL_Drop', surf(HC, HR, 4.4, 27.4, 0.3), (0.8, 0.6, 1.1), TEAR, segs=12, rings=8)
face_line('TearR1', [(16.2, 36.7), (16.6, 33.0), (16.3, 29.0), (16.7, 25.0), (16.5, 22.5)], 0.5, TEAR, off=0.3)
ellipsoid('TearR1_Drop', surf(HC, HR, 16.5, 22.1, 0.3), (0.8, 0.6, 1.1), TEAR, segs=12, rings=8)
face_line('TearR2', [(14.2, 36.6), (13.9, 34.5), (14.1, 32.8)], 0.45, TEAR, off=0.3)
ellipsoid('TearR2_Drop', surf(HC, HR, 14.1, 32.5, 0.3), (0.7, 0.55, 0.9), TEAR, segs=12, rings=8)

# chest squiggle on the torso front
sq = [(-9.0, 6.5), (-6.5, 5.2), (-4.0, 5.8), (-2.5, 4.2), (-0.5, 5.6), (2.0, 5.0), (4.5, 6.2)]
tube('ChestSquiggle', [surf(TC, TR, p[0], p[1], 0.2) for p in sq], 0.35, DARK, segs=8, per=6)

# ---------------------------------------------------------------
# Power strip growing out of the head (leaning toward +X)
# Strip local frame: Z = long axis, -Y = socket (front) face
# ---------------------------------------------------------------
B = Vector((9.0, -2.0, 52.0))
TILT = math.radians(15.0)
YAW = math.radians(-20.0)
L = 38.0
W = 14.0
D = 9.0
M = Matrix.Translation(B) @ Matrix.Rotation(TILT, 4, 'Y') @ Matrix.Rotation(YAW, 4, 'Z')


def face_frame(zs):
    # canonical X -> strip X, canonical Y -> strip Z (up the strip), canonical Z -> outward normal of the front face
    return M @ Matrix.Translation((0.0, -D * 0.5, zs)) @ Matrix.Rotation(math.radians(90.0), 4, 'X')


# flared neck blending the head into the strip
skin('NeckFlare', [
    prof_ring(rrect(24.0, 19.0, 9.0), -10.0),
    prof_ring(rrect(22.0, 16.5, 7.8), -5.0),
    prof_ring(rrect(17.5, 12.0, 4.8), -0.5),
    prof_ring(rrect(14.6, 9.6, 2.4), 3.0),
    prof_ring(rrect(13.8, 8.8, 2.0), 4.0),
], SKIN, smooth=True, xf=M)

# strip housing
skin('PowerStrip', [
    prof_ring(rrect(W, D, 1.6), 0.0),
    prof_ring(rrect(W, D, 1.6), L - 0.8),
    prof_ring(rrect(W - 1.2, D - 1.2, 1.2), L),
], STRIP, smooth=False, xf=M)

# strain-relief grommet on top of the strip where the cable leaves
G = M @ Matrix.Translation((0.0, 0.0, L))
lathe('StripGrommet', [(3.3, -0.5), (3.3, 0.8), (2.9, 1.0), (2.9, 1.6), (2.6, 1.7), (2.6, 2.3), (2.9, 2.4), (2.9, 3.0), (2.5, 3.1), (2.5, 3.7), (2.2, 3.8), (2.2, 4.6), (1.8, 4.8)], STRIP, G, n=16, smooth=False)


def socket_plate(tag, F):
    skin('SocketRim_' + tag, [prof_ring(rrect(9.4, 8.4, 2.0), -0.3), prof_ring(rrect(9.4, 8.4, 2.0), 0.25)], DARK, smooth=False, xf=F)
    skin('SocketPlate_' + tag, [prof_ring(rrect(8.6, 7.6, 1.7), -0.3), prof_ring(rrect(8.6, 7.6, 1.7), 0.5)], PLATE, smooth=False, xf=F)


def socket_holes(tag, F):
    skin('SocketSlotL_' + tag, [prof_ring(rect(0.8, 2.4), 0.3, -1.8, 1.0), prof_ring(rect(0.8, 2.4), 0.65, -1.8, 1.0)], DARK, smooth=False, xf=F)
    skin('SocketSlotR_' + tag, [prof_ring(rect(0.8, 2.4), 0.3, 1.8, 1.0), prof_ring(rect(0.8, 2.4), 0.65, 1.8, 1.0)], DARK, smooth=False, xf=F)
    lathe('SocketGround_' + tag, [(0.8, 0.3), (0.8, 0.65)], DARK, F, n=14, ox=0.0, oy=-1.9, smooth=False)


# two visible empty sockets (upper part of the front face)
for idx, zs in enumerate((29.0, 19.2)):
    Fs = face_frame(zs)
    socket_plate('Empty' + str(idx + 1), Fs)
    socket_holes('Empty' + str(idx + 1), Fs)

# third (lowest) socket: occupied by the plug
PLUG_Z = 9.4
F3 = face_frame(PLUG_Z)
socket_plate('Occupied', F3)

# ---------------------------------------------------------------
# Plug: seated in the lowest socket, axis = front-face normal
# ---------------------------------------------------------------
skin('PlugBladeL', [prof_ring(rect(0.5, 2.0), -2.2, -1.8, 1.0), prof_ring(rect(0.5, 2.0), 1.0, -1.8, 1.0)], BRASS, smooth=False, xf=F3)
skin('PlugBladeR', [prof_ring(rect(0.5, 2.0), -2.2, 1.8, 1.0), prof_ring(rect(0.5, 2.0), 1.0, 1.8, 1.0)], BRASS, smooth=False, xf=F3)
lathe('PlugGroundPin', [(0.6, -2.2), (0.6, 1.0)], BRASS, F3, n=12, ox=0.0, oy=-1.9, smooth=True)
skin('PlugBody', [
    prof_ring(rrect(8.0, 7.0, 1.6), 0.5),
    prof_ring(rrect(8.0, 7.0, 1.6), 4.0),
    prof_ring(rrect(6.6, 5.8, 1.5), 6.5),
    prof_ring(rrect(4.6, 4.4, 1.4), 8.8),
], PLUG, smooth=False, xf=F3)
skin('PlugGripBand', [prof_ring(rrect(8.5, 7.5, 1.8), 1.6), prof_ring(rrect(8.5, 7.5, 1.8), 2.6)], GRIP, smooth=False, xf=F3)
lathe('PlugStrainRelief', [(2.3, 8.6), (2.3, 9.4), (1.95, 9.5), (1.95, 10.1), (2.2, 10.2), (2.2, 10.9), (1.85, 11.0), (1.85, 11.6), (2.05, 11.7), (2.05, 12.4), (1.7, 12.6)], GRIP, F3, n=16, smooth=False)

# ---------------------------------------------------------------
# Cable: from the grommet on top of the strip, looping over to the
# left and forward, returning to the rear of the plug
# ---------------------------------------------------------------
cable_pts = [
    M @ Vector((0.0, 0.0, L + 2.0)),
    M @ Vector((0.0, 0.0, L + 4.2)),
    M @ Vector((0.0, 0.0, L + 6.4)),
    Vector((20.3, -2.2, 97.9)),
    Vector((16.5, -2.7, 99.6)),
    Vector((9.5, -3.5, 100.0)),
    Vector((2.0, -5.0, 98.0)),
    Vector((-5.5, -7.5, 93.8)),
    Vector((-11.5, -11.5, 87.5)),
    Vector((-14.5, -16.5, 80.2)),
    Vector((-13.5, -22.0, 73.5)),
    Vector((-10.0, -26.5, 68.2)),
    Vector((-4.7, -28.6, 65.2)),
    Vector((0.3, -27.2, 63.8)),
    F3 @ Vector((0.0, 0.0, 17.5)),
    F3 @ Vector((0.0, 0.0, 14.2)),
    F3 @ Vector((0.0, 0.0, 11.0)),
]
tube('Cable', cable_pts, 1.5, CABLE, segs=12, per=8)

# ---------------------------------------------------------------
# Normalise: base at Z = 0, overall height = 100, centred in X/Y
# ---------------------------------------------------------------
xs = []
ys = []
zs_all = []
for ob in OBJS:
    for v in ob.data.vertices:
        xs.append(v.co.x)
        ys.append(v.co.y)
        zs_all.append(v.co.z)
zmin = min(zs_all)
zmax = max(zs_all)
cx = 0.5 * (min(xs) + max(xs))
cy = 0.5 * (min(ys) + max(ys))
s = 100.0 / max(zmax - zmin, 1e-6)
T = Matrix.Scale(s, 4) @ Matrix.Translation((-cx, -cy, -zmin))
for ob in OBJS:
    ob.data.transform(T)
    ob.data.update()
