import bpy
import math
from mathutils import Vector, Matrix

# ---------------------------------------------------------------
# Clear the starting scene
# ---------------------------------------------------------------
scene = bpy.context.scene
for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob, do_unlink=True)
for me in list(bpy.data.meshes):
    if me.users == 0:
        bpy.data.meshes.remove(me)


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------
def make_mat(name, rgb, rough=0.6, metal=0.0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (rgb[0], rgb[1], rgb[2], 1.0)
    try:
        m.use_nodes = True
    except Exception:
        pass
    try:
        nt = m.node_tree
        if nt is not None:
            for n in nt.nodes:
                if n.type == 'BSDF_PRINCIPLED':
                    n.inputs['Base Color'].default_value = (rgb[0], rgb[1], rgb[2], 1.0)
                    n.inputs['Roughness'].default_value = rough
                    n.inputs['Metallic'].default_value = metal
    except Exception:
        pass
    return m


def T(v):
    return Matrix.Translation(Vector(v))


def S(x, y, z):
    return Matrix.Diagonal((x, y, z, 1.0))


def R(angle, axis):
    return Matrix.Rotation(angle, 4, axis)


def frame(origin, zdir, xhint=None):
    z = Vector(zdir).normalized()
    if xhint is None:
        xhint = Vector((1.0, 0.0, 0.0))
    xhint = Vector(xhint)
    x = xhint - z * xhint.dot(z)
    if x.length < 1e-5:
        xhint = Vector((0.0, 1.0, 0.0))
        x = xhint - z * xhint.dot(z)
    x.normalize()
    y = z.cross(x)
    o = Vector(origin)
    return Matrix(((x.x, y.x, z.x, o.x),
                   (x.y, y.y, z.y, o.y),
                   (x.z, y.z, z.z, o.z),
                   (0.0, 0.0, 0.0, 1.0)))


def new_obj(name, verts, faces, material, smooth=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    me.update()
    if smooth:
        me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
    me.materials.append(material)
    ob = bpy.data.objects.new(name, me)
    scene.collection.objects.link(ob)
    return ob


def sphere_data(segs=24, rings=12):
    verts = [Vector((0.0, 0.0, 1.0))]
    for i in range(1, rings):
        phi = math.pi * i / rings
        for j in range(segs):
            th = 2.0 * math.pi * j / segs
            verts.append(Vector((math.sin(phi) * math.cos(th), math.sin(phi) * math.sin(th), math.cos(phi))))
    verts.append(Vector((0.0, 0.0, -1.0)))
    faces = []
    for j in range(segs):
        faces.append((0, 1 + j, 1 + (j + 1) % segs))
    for i in range(rings - 2):
        a = 1 + i * segs
        b = a + segs
        for j in range(segs):
            faces.append((a + j, b + j, b + (j + 1) % segs, a + (j + 1) % segs))
    last = len(verts) - 1
    a = 1 + (rings - 2) * segs
    for j in range(segs):
        faces.append((last, a + (j + 1) % segs, a + j))
    return verts, faces


def box_data():
    verts = [Vector((x, y, z)) for x in (-0.5, 0.5) for y in (-0.5, 0.5) for z in (-0.5, 0.5)]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    return verts, faces


def cyl_data(segs=20, r0=1.0, r1=1.0):
    verts = []
    for j in range(segs):
        a = 2.0 * math.pi * j / segs
        verts.append(Vector((r0 * math.cos(a), r0 * math.sin(a), -0.5)))
    for j in range(segs):
        a = 2.0 * math.pi * j / segs
        verts.append(Vector((r1 * math.cos(a), r1 * math.sin(a), 0.5)))
    faces = []
    for j in range(segs):
        faces.append((j, (j + 1) % segs, segs + (j + 1) % segs, segs + j))
    faces.append(tuple(reversed(range(segs))))
    faces.append(tuple(range(segs, 2 * segs)))
    return verts, faces


def add_ellipsoid(name, M, material, segs=24, rings=12):
    v, f = sphere_data(segs, rings)
    return new_obj(name, [M @ p for p in v], f, material, True)


def add_box(name, M, material):
    v, f = box_data()
    return new_obj(name, [M @ p for p in v], f, material, False)


def add_cyl(name, M, material, r0=1.0, r1=1.0, segs=20, smooth=False):
    v, f = cyl_data(segs, r0, r1)
    return new_obj(name, [M @ p for p in v], f, material, smooth)


def add_bevel(ob, width, segments=3):
    m = ob.modifiers.new('Bevel', 'BEVEL')
    m.width = width
    m.segments = segments
    m.limit_method = 'ANGLE'
    return m


def limb(name, p0, p1, r, material):
    p0 = Vector(p0)
    p1 = Vector(p1)
    d = p1 - p0
    M = frame((p0 + p1) * 0.5, d) @ S(r, r, d.length * 0.5 + r * 0.6)
    return add_ellipsoid(name, M, material)


def catmull_list(pts, sub):
    pts = [tuple(p) for p in pts]
    out = []
    n = len(pts)
    for i in range(n - 1):
        p0 = pts[max(i - 1, 0)]
        p1 = pts[i]
        p2 = pts[i + 1]
        p3 = pts[min(i + 2, n - 1)]
        for s in range(sub):
            t = s / sub
            t2 = t * t
            t3 = t2 * t
            out.append(tuple(0.5 * ((2.0 * b) + (-a + c) * t + (2.0 * a - 5.0 * b + 4.0 * c - d) * t2 + (-a + 3.0 * b - 3.0 * c + d) * t3)
                             for a, b, c, d in zip(p0, p1, p2, p3)))
    out.append(tuple(pts[-1]))
    return out


def tube(name, pts, radius, material, segs=10, sub=6):
    P = [Vector(p) for p in catmull_list(pts, sub)]
    n = len(P)
    tang = []
    for i in range(n):
        a = P[max(i - 1, 0)]
        b = P[min(i + 1, n - 1)]
        t = b - a
        if t.length > 1e-9:
            t.normalize()
        else:
            t = Vector((0.0, 0.0, 1.0))
        tang.append(t)
    ref = Vector((0.0, 1.0, 0.0))
    if abs(tang[0].dot(ref)) > 0.9:
        ref = Vector((1.0, 0.0, 0.0))
    nrm = (ref - tang[0] * ref.dot(tang[0])).normalized()
    verts = []
    faces = []
    for i in range(n):
        t = tang[i]
        cand = nrm - t * nrm.dot(t)
        if cand.length < 1e-6:
            alt = Vector((1.0, 0.0, 0.0))
            if abs(t.dot(alt)) > 0.9:
                alt = Vector((0.0, 0.0, 1.0))
            cand = alt - t * alt.dot(t)
        nrm = cand.normalized()
        b = t.cross(nrm)
        r = radius(i / max(n - 1, 1)) if callable(radius) else radius
        for j in range(segs):
            a = 2.0 * math.pi * j / segs
            verts.append(P[i] + (nrm * math.cos(a) + b * math.sin(a)) * r)
    for i in range(n - 1):
        a0 = i * segs
        b0 = a0 + segs
        for j in range(segs):
            faces.append((a0 + j, a0 + (j + 1) % segs, b0 + (j + 1) % segs, b0 + j))
    faces.append(tuple(reversed(range(segs))))
    faces.append(tuple(range((n - 1) * segs, n * segs)))
    return new_obj(name, verts, faces, material, True)


# ---------------------------------------------------------------
# Materials
# ---------------------------------------------------------------
mat_body = make_mat('BodySkin', (0.93, 0.91, 0.87), 0.7)
mat_strip = make_mat('StripPlastic', (0.90, 0.90, 0.86), 0.45)
mat_plate = make_mat('OutletPlate', (0.98, 0.98, 0.96), 0.4)
mat_dark = make_mat('InkBlack', (0.03, 0.03, 0.03), 0.6)
mat_cord = make_mat('Cord', (0.80, 0.80, 0.78), 0.5)
mat_blue = make_mat('TearBlue', (0.15, 0.55, 0.92), 0.25)
mat_metal = make_mat('ProngMetal', (0.72, 0.72, 0.75), 0.3, 1.0)
mat_white = make_mat('EyeWhite', (1.0, 1.0, 1.0), 0.4)

# ---------------------------------------------------------------
# BODY: hunched blob torso lofted from elliptical rings.
# It narrows at the top into a neck that becomes the power strip.
# ring = (z, centre_x, radius_x, radius_y)
# ---------------------------------------------------------------
RINGS = [
    (0.0, -1.0, 24.0, 16.5),
    (1.5, -1.0, 27.2, 19.4),
    (5.0, -0.5, 27.6, 20.0),
    (13.0, 0.5, 26.9, 19.6),
    (24.0, 1.5, 26.5, 19.0),
    (33.0, 2.0, 26.0, 18.0),
    (39.0, 4.0, 23.0, 16.0),
    (43.5, 6.0, 18.5, 13.5),
    (47.0, 9.0, 14.0, 10.5),
    (49.5, 12.3, 10.4, 8.8),
    (52.0, 14.4, 9.0, 8.2),
    (55.0, 15.0, 8.2, 7.8),
]
DENSE = catmull_list(RINGS, 4)


def ring_at(z):
    if z <= DENSE[0][0]:
        return DENSE[0][1], DENSE[0][2], DENSE[0][3]
    for i in range(len(DENSE) - 1):
        z0 = DENSE[i][0]
        z1 = DENSE[i + 1][0]
        if z <= z1:
            f = (z - z0) / (z1 - z0) if z1 > z0 else 0.0
            f = max(0.0, min(1.0, f))
            a = DENSE[i]
            b = DENSE[i + 1]
            return (a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f, a[3] + (b[3] - a[3]) * f)
    return DENSE[-1][1], DENSE[-1][2], DENSE[-1][3]


def surf_point(x, z, lift=0.0):
    cx, rx, ry = ring_at(z)
    u = max(-0.98, min(0.98, (x - cx) / rx))
    w = math.sqrt(1.0 - u * u)
    n = Vector((u / rx, -w / ry, 0.0)).normalized()
    p = Vector((cx + u * rx, -ry * w, z)) + n * lift
    return p, n


def surf_frame(x, z, lift=0.0, roll=0.0):
    p, n = surf_point(x, z, lift)
    return frame(p, n, Vector((1.0, 0.0, 0.0))) @ R(roll, 'Z')


def surface_line(name, xz, radius, material, lift=0.15):
    d = catmull_list(xz, 5)
    pts = [surf_point(q[0], q[1], lift)[0] for q in d]
    return tube(name, pts, radius, material, segs=8, sub=1)


BSEG = 48
bverts = []
bfaces = []
for (z, cx, rx, ry) in DENSE:
    for j in range(BSEG):
        a = 2.0 * math.pi * j / BSEG
        bverts.append(Vector((cx + rx * math.cos(a), ry * math.sin(a), z)))
nr = len(DENSE)
for i in range(nr - 1):
    a0 = i * BSEG
    b0 = a0 + BSEG
    for j in range(BSEG):
        bfaces.append((a0 + j, a0 + (j + 1) % BSEG, b0 + (j + 1) % BSEG, b0 + j))
bfaces.append(tuple(reversed(range(BSEG))))
bfaces.append(tuple(range((nr - 1) * BSEG, nr * BSEG)))
new_obj('Body_Torso', bverts, bfaces, mat_body, True)

# Left arm: shoulder hump down the left side, forearm resting diagonally across the front base
limb('Body_UpperArm', (-19.0, -4.0, 35.0), (-20.0, -11.0, 10.0), 6.5, mat_body)
limb('Body_Forearm', (-18.0, -13.0, 12.0), (9.0, -19.5, 4.0), 4.8, mat_body)
add_ellipsoid('Body_Hand', T((10.0, -19.5, 3.6)) @ S(4.2, 3.4, 3.0), mat_body)

# ---------------------------------------------------------------
# FACE on the chest (front, -Y), right of centre: crying wojak face
# ---------------------------------------------------------------
# eyes
add_ellipsoid('Face_EyeL', surf_frame(6.5, 30.5, 0.05, math.radians(-8)) @ S(3.0, 1.6, 0.8), mat_white)
add_ellipsoid('Face_PupilL', surf_frame(7.0, 30.4, 0.5) @ S(1.5, 1.25, 0.55), mat_dark)
add_ellipsoid('Face_EyeR', surf_frame(16.0, 32.3, 0.05, math.radians(6)) @ S(2.3, 1.35, 0.8), mat_white)
add_ellipsoid('Face_PupilR', surf_frame(16.3, 32.2, 0.5) @ S(1.15, 1.05, 0.55), mat_dark)
# heavy upper lids
surface_line('Face_LidL', [(3.3, 30.9), (5.2, 32.1), (7.8, 32.0), (9.7, 30.6)], 0.38, mat_dark, 0.55)
surface_line('Face_LidR', [(13.8, 32.9), (15.5, 33.7), (17.5, 33.6), (18.5, 32.6)], 0.34, mat_dark, 0.55)
# brows (sad / furrowed)
surface_line('Face_BrowL', [(2.6, 33.4), (6.5, 33.7), (10.4, 32.4)], 0.45, mat_dark, 0.2)
surface_line('Face_BrowR', [(13.4, 34.8), (16.0, 35.6), (19.0, 35.2)], 0.42, mat_dark, 0.2)
surface_line('Face_Furrow', [(11.4, 34.6), (11.8, 33.2)], 0.28, mat_dark, 0.15)
# nose
add_ellipsoid('Face_Nose', surf_frame(12.0, 29.6, 0.4, math.radians(-6)) @ S(1.1, 2.3, 1.5), mat_body)
# frowning mouth and lower lip
surface_line('Face_Mouth', [(8.8, 25.4), (10.8, 26.2), (13.0, 26.3), (15.6, 25.6)], 0.4, mat_dark, 0.15)
surface_line('Face_LowerLip', [(10.3, 24.0), (12.3, 23.7), (14.3, 24.1)], 0.28, mat_dark, 0.15)
# blue tears running down from both eyes
surface_line('Tear_L_Long', [(5.6, 28.8), (5.4, 26.0), (5.9, 23.5), (6.1, 20.8)], 0.5, mat_blue, 0.25)
add_ellipsoid('Tear_L_Drop', surf_frame(6.1, 20.4, 0.3) @ S(0.75, 1.0, 0.6), mat_blue)
surface_line('Tear_L_Short', [(8.6, 28.6), (8.8, 26.2)], 0.42, mat_blue, 0.25)
surface_line('Tear_R_Long', [(17.2, 30.6), (16.9, 26.0), (17.2, 21.0), (17.0, 14.5)], 0.5, mat_blue, 0.25)
add_ellipsoid('Tear_R_Drop', surf_frame(17.0, 14.0, 0.3) @ S(0.75, 1.0, 0.6), mat_blue)
surface_line('Tear_R_Short', [(18.8, 30.8), (19.3, 26.5)], 0.42, mat_blue, 0.25)

# ---------------------------------------------------------------
# POWER STRIP head: tall box rising from the neck, leaning to +X,
# turned about its long axis so the outlet face looks front-left.
# ---------------------------------------------------------------
STRIP_W = 11.0   # outlet face width (local X)
STRIP_D = 13.0   # depth (local Y)
STRIP_L = 40.0   # length (local Z)
MS = T((16.5, 0.0, 67.0)) @ R(math.radians(8.0), 'Y') @ R(math.radians(-45.0), 'Z')

strip = add_box('Strip_Body', MS @ S(STRIP_W, STRIP_D, STRIP_L), mat_strip)
add_bevel(strip, 1.2, 3)
cap = add_box('Strip_EndCap', MS @ T((0.0, 0.0, 18.4)) @ S(STRIP_W + 0.5, STRIP_D + 0.5, 3.2), mat_strip)
add_bevel(cap, 1.2, 3)

fy = -STRIP_D * 0.5
for idx, zc in enumerate((8.0, -2.5)):
    plate = add_box('Outlet_Plate_%d' % idx, MS @ T((0.0, fy - 0.1, zc)) @ S(8.0, 0.5, 9.0), mat_plate)
    add_bevel(plate, 0.2, 2)
    add_box('Outlet_SlotL_%d' % idx, MS @ T((-1.6, fy - 0.4, zc + 1.3)) @ S(0.7, 0.3, 2.9), mat_dark)
    add_box('Outlet_SlotR_%d' % idx, MS @ T((1.6, fy - 0.4, zc + 1.3)) @ S(0.7, 0.3, 2.4), mat_dark)
    add_cyl('Outlet_Ground_%d' % idx, MS @ T((0.0, fy - 0.4, zc - 2.2)) @ R(math.pi * 0.5, 'X') @ S(1.0, 1.0, 0.3), mat_dark, 0.8, 0.8, 16)

# strain relief at the top end of the strip (ribbed collar)
add_cyl('Strain_Relief', MS @ T((0.0, 0.0, 22.6)) @ S(1.0, 1.0, 5.6), mat_cord, 2.9, 1.8, 20, True)
for k in range(4):
    rr = 3.2 - 0.35 * k
    add_cyl('Strain_Rib_%d' % k, MS @ T((0.0, 0.0, 20.9 + 1.2 * k)) @ S(1.0, 1.0, 0.55), mat_cord, rr, rr, 20, False)

# ---------------------------------------------------------------
# CORD: leaves the strip top, arcs up and over to the left, hangs
# down and ends in a plug pushed into the base of the neck.
# ---------------------------------------------------------------
cord_start = MS @ Vector((0.0, 0.0, 20.0))
cord_p1 = MS @ Vector((0.0, 0.0, 25.5))
plug_A = Vector((-6.0, -5.5, 58.8))
plug_d = Vector((12.5, 1.5, -10.0)).normalized()
cord_pts = [
    cord_start,
    cord_p1,
    Vector((17.5, 0.5, 96.2)),
    Vector((10.0, 1.0, 98.1)),
    Vector((0.0, 1.0, 97.5)),
    Vector((-8.0, 0.5, 93.2)),
    Vector((-12.6, 0.0, 86.0)),
    Vector((-13.8, -1.0, 77.0)),
    Vector((-13.0, -2.5, 69.0)),
    Vector((-10.2, -4.5, 63.0)),
    plug_A,
    plug_A + plug_d * 3.0,
]
tube('Cord', cord_pts, 1.25, mat_cord, segs=12, sub=8)

# plug: tapered boot, chunky head, two metal prongs entering the neck
xh = Vector((0.0, 1.0, 0.0)).cross(plug_d)
FP = frame(plug_A, plug_d, xh)
add_cyl('Plug_Boot', FP @ T((0.0, 0.0, 2.5)) @ S(1.25, 0.8, 5.4), mat_strip, 1.7, 3.2, 20, True)
head = add_box('Plug_Head', FP @ T((0.0, 0.0, 9.0)) @ S(9.0, 5.0, 8.0), mat_strip)
add_bevel(head, 1.0, 3)
add_box('Plug_ProngA', FP @ T((-2.0, 0.0, 14.5)) @ S(0.5, 2.0, 3.6), mat_metal)
add_box('Plug_ProngB', FP @ T((2.0, 0.0, 14.5)) @ S(0.5, 2.0, 3.6), mat_metal)

try:
    bpy.context.view_layer.update()
except Exception:
    pass
