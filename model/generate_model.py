#!/usr/bin/env python3
"""
小米手环 10 高保真 GLB 模型生成脚本
- 真实比例建模，单位 mm，导出时整体缩放到米。
- 不使用 Box/Sphere/Cylinder 等基础几何体直接拼凑：
  机身/玻璃/屏幕/后盖采用圆角矩形轮廓 Extrude；
  表带采用圆角截面沿圆弧 Sweep；
  传感器/触点采用圆角小柱体 Extrude。
- 输出 PBR 贴图：BaseColor / Roughness+Metalness / Normal / AO。
"""

import os
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops
import trimesh
from trimesh.visual.material import PBRMaterial
from trimesh.transformations import translation_matrix, scale_matrix

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "public", "models")
TEX_DIR = os.path.join(ROOT, "public", "textures")
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(TEX_DIR, exist_ok=True)

# 机身官方尺寸 (mm)
BODY_L = 46.57
BODY_W = 22.54
BODY_T = 10.95
BODY_R = 10.5  # 圆角半径（视觉 pill 形状）

# 屏幕
SCREEN_DIAG_IN = 1.72
SCREEN_RES_W = 212
SCREEN_RES_H = 520
# 由对角线+分辨率计算 active 区域 (mm)
R_RES = SCREEN_RES_W / SCREEN_RES_H
SCREEN_H = (SCREEN_DIAG_IN * 25.4) / math.sqrt(1 + R_RES ** 2)
SCREEN_W = SCREEN_H * R_RES
# 拆解图标注玻璃黑边约 2.0 mm
BEZEL = 2.0
GLASS_W = SCREEN_W + BEZEL * 2
GLASS_H = SCREEN_H + BEZEL * 2
GLASS_R = 9.0

# 背面传感器
SENSOR_DIA = 10.0
SENSOR_PROTRUSION = 1.4
CONTACT_W = 1.2
CONTACT_L = 1.6
CONTACT_GAP = 2.4
CONTACT_PROTRUSION = 0.4

# 表带（单位 mm）
BAND_WIDTH = 16.0
BAND_THICKNESS = 2.2
# 让圆弧两端与机身背部两端对齐：R=33，角度 45°，圆心 z=-29
BAND_CENTER_Z = -29.0
BAND_RADIUS = 33.0
BAND_ANGLE = math.radians(45)

# ---------------------------------------------------------------------------
# 贴图生成
# ---------------------------------------------------------------------------
TEX_SIZE = 128

def solid_tex(color):
    arr = np.zeros((TEX_SIZE, TEX_SIZE, 4), dtype=np.uint8)
    arr[:, :, :3] = color
    arr[:, :, 3] = 255
    return Image.fromarray(arr)

def noise_tex(base, intensity=8):
    img = Image.new("RGB", (TEX_SIZE, TEX_SIZE), base)
    arr = np.array(img).astype(np.int16)
    noise = np.random.randint(-intensity, intensity + 1, arr.shape)
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(arr)

def normal_map(strength=8):
    """生成中性法线贴图（带细微噪点模拟磨砂/拉丝）"""
    base = np.full((TEX_SIZE, TEX_SIZE, 3), [128, 128, 255], dtype=np.uint8)
    noise = np.random.randint(-strength, strength + 1, (TEX_SIZE, TEX_SIZE, 2))
    base[:, :, :2] = np.clip(base[:, :, :2].astype(np.int16) + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(base)

def brushed_metal_normal():
    img = Image.new("RGB", (TEX_SIZE, TEX_SIZE), (128, 128, 255))
    draw = ImageDraw.Draw(img)
    for i in range(0, TEX_SIZE, 2):
        offset = int(np.random.randint(-2, 3))
        draw.line([(0, i + offset), (TEX_SIZE, i + offset)], fill=(130, 126, 255))
    return img

def leather_textures():
    base = noise_tex((180, 160, 140), 18)
    # normal
    n = Image.new("RGB", (TEX_SIZE, TEX_SIZE), (128, 128, 255))
    for _ in range(80):
        x, y = np.random.randint(0, TEX_SIZE, 2)
        r = np.random.randint(2, 6)
        draw = ImageDraw.Draw(n)
        bbox = [x - r, y - r, x + r, y + r]
        draw.ellipse(bbox, fill=(140, 140, 255))
    n = n.filter(ImageFilter.GaussianBlur(1))
    return base, n

def woven_textures():
    base = Image.new("RGB", (TEX_SIZE, TEX_SIZE), (120, 120, 130))
    draw = ImageDraw.Draw(base)
    step = 8
    for i in range(0, TEX_SIZE, step):
        draw.line([(i, 0), (i, TEX_SIZE)], fill=(90, 90, 100), width=2)
        draw.line([(0, i), (TEX_SIZE, i)], fill=(150, 150, 160), width=2)
    n = Image.new("RGB", (TEX_SIZE, TEX_SIZE), (128, 128, 255))
    for i in range(0, TEX_SIZE, step):
        draw = ImageDraw.Draw(n)
        draw.line([(i + 1, 0), (i + 1, TEX_SIZE)], fill=(140, 128, 255), width=1)
        draw.line([(0, i + 1), (TEX_SIZE, i + 1)], fill=(116, 128, 255), width=1)
    n = n.filter(ImageFilter.GaussianBlur(0.5))
    return base, n

def metal_link_textures():
    base = noise_tex((200, 200, 205), 12)
    n = Image.new("RGB", (TEX_SIZE, TEX_SIZE), (128, 128, 255))
    draw = ImageDraw.Draw(n)
    for i in range(0, TEX_SIZE, 16):
        draw.rectangle([i, 0, i + 14, TEX_SIZE], outline=(110, 128, 255), width=2)
    return base, n

def rough_metal_tex(rough, metal):
    """glTF metallicRoughness: green=roughness, blue=metalness"""
    arr = np.zeros((TEX_SIZE, TEX_SIZE, 4), dtype=np.uint8)
    arr[:, :, 1] = int(rough * 255)
    arr[:, :, 2] = int(metal * 255)
    arr[:, :, 3] = 255
    return Image.fromarray(arr)

def ao_tex(brightness=230):
    arr = np.full((TEX_SIZE, TEX_SIZE, 4), [brightness, brightness, brightness, 255], dtype=np.uint8)
    return Image.fromarray(arr)

# 保存贴图
textures = {}

def save_tex(name, img):
    path = os.path.join(TEX_DIR, f"{name}.png")
    img.save(path)
    textures[name] = path
    return path

# Frame (aluminum default)
save_tex("frame_base", solid_tex((210, 210, 215)))
save_tex("frame_rm", rough_metal_tex(0.35, 1.0))
save_tex("frame_normal", brushed_metal_normal())
save_tex("frame_ao", ao_tex(240))

# Glass
save_tex("glass_base", solid_tex((245, 245, 247)))
save_tex("glass_rm", rough_metal_tex(0.05, 0.0))
save_tex("glass_normal", normal_map(2))
save_tex("glass_ao", ao_tex(255))

# Screen border
save_tex("border_base", solid_tex((8, 8, 10)))
save_tex("border_rm", rough_metal_tex(0.5, 0.0))
save_tex("border_normal", normal_map(1))
save_tex("border_ao", ao_tex(255))

# Display (neutral black placeholder; viewer replaces with custom texture)
save_tex("display_base", solid_tex((0, 0, 0)))
save_tex("display_rm", rough_metal_tex(0.25, 0.0))
save_tex("display_normal", normal_map(1))
save_tex("display_ao", ao_tex(255))

# Sensor
save_tex("sensor_base", solid_tex((20, 20, 25)))
save_tex("sensor_rm", rough_metal_tex(0.2, 0.1))
save_tex("sensor_normal", normal_map(2))
save_tex("sensor_ao", ao_tex(200))

# Contact
save_tex("contact_base", solid_tex((210, 190, 140)))
save_tex("contact_rm", rough_metal_tex(0.25, 1.0))
save_tex("contact_normal", normal_map(2))
save_tex("contact_ao", ao_tex(255))

# Bands
# TPU
save_tex("tpu_base", solid_tex((40, 40, 45)))
save_tex("tpu_rm", rough_metal_tex(0.65, 0.0))
save_tex("tpu_normal", normal_map(6))
save_tex("tpu_ao", ao_tex(235))
# Metal
base_m, norm_m = metal_link_textures()
save_tex("metal_base", base_m)
save_tex("metal_rm", rough_metal_tex(0.25, 1.0))
save_tex("metal_normal", norm_m)
save_tex("metal_ao", ao_tex(240))
# Leather
base_l, norm_l = leather_textures()
save_tex("leather_base", base_l)
save_tex("leather_rm", rough_metal_tex(0.75, 0.0))
save_tex("leather_normal", norm_l)
save_tex("leather_ao", ao_tex(220))
# Woven
base_w, norm_w = woven_textures()
save_tex("woven_base", base_w)
save_tex("woven_rm", rough_metal_tex(0.85, 0.0))
save_tex("woven_normal", norm_w)
save_tex("woven_ao", ao_tex(225))

# ---------------------------------------------------------------------------
# 几何体构建（无基础几何体直接拼凑）
# ---------------------------------------------------------------------------

def rounded_rect_points(w, h, r, segments=16):
    """生成带圆角的矩形轮廓点（逆时针，XY 平面）"""
    pts = []
    hw, hh = w / 2 - r, h / 2 - r
    corners = [
        (hw, hh, math.pi * 0.5, math.pi),      # 左上
        (-hw, hh, math.pi, math.pi * 1.5),     # 右上？按逆时针从左上开始
    ]
    # 重新：逆时针从右上 -> 左上 -> 左下 -> 右下
    corners = [
        (hw, hh, 0, math.pi * 0.5),            # 右上
        (-hw, hh, math.pi * 0.5, math.pi),     # 左上
        (-hw, -hh, math.pi, math.pi * 1.5),    # 左下
        (hw, -hh, math.pi * 1.5, math.pi * 2), # 右下
    ]
    for cx, cy, a0, a1 in corners:
        for i in range(segments + 1):
            t = i / segments
            a = a0 + (a1 - a0) * t
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    # 去掉最后一个重复点
    return pts[:-1]

def polygon_from_points(pts):
    from shapely.geometry import Polygon
    return Polygon(pts)

def extrude_profile(profile, depth, name="mesh"):
    """将 2D profile (shapely Polygon) 沿 Z 轴拉伸为 3D mesh"""
    mesh = trimesh.creation.extrude_polygon(profile, height=depth)
    mesh.metadata["name"] = name
    return mesh

def rounded_box(w, h, d, r, segments=16, name="rounded_box"):
    """圆角盒：圆角矩形轮廓拉伸"""
    pts = rounded_rect_points(w, h, r, segments)
    poly = polygon_from_points(pts)
    mesh = extrude_profile(poly, d, name)
    # 让中心位于原点，当前拉伸后 Z 范围 [0, d]
    mesh.apply_translation((0, 0, -d / 2))
    return mesh

def band_path(num=80):
    """表带路径：绕手腕后方的长圆弧（major arc），两端与机身背部对齐"""
    # 从 +BAND_ANGLE 经 180° 到 -BAND_ANGLE，避免穿过机身正面
    angles = np.linspace(BAND_ANGLE, 2 * math.pi - BAND_ANGLE, num)
    pts = []
    for a in angles:
        y = BAND_RADIUS * math.sin(a)
        z = BAND_CENTER_Z + BAND_RADIUS * math.cos(a)
        pts.append((0, y, z))
    return np.array(pts)

def band_cross_section(width, thickness, r=0.8, segments=8):
    """表带截面：圆角矩形，位于 XZ 平面"""
    pts = rounded_rect_points(width, thickness, r, segments)
    # 截面在 XZ 平面，所以把 y 换为 z
    pts = [(x, 0, y) for x, y in pts]
    return polygon_from_points([(p[0], p[2]) for p in pts])

def create_band(name, width, thickness, rm_tex, base_tex, normal_tex, ao_tex, link_scale=1.0):
    """沿圆弧 Sweep 生成表带"""
    path = band_path()
    section = band_cross_section(width, thickness)
    mesh = trimesh.creation.sweep_polygon(section, path)
    mesh.metadata["name"] = name
    # UV 展开：沿长度方向 U，截面方向 V
    # 简单平面投影 UV
    bounds = mesh.bounds
    vs = mesh.vertices.copy()
    u = (vs[:, 1] - bounds[0, 1]) / (bounds[1, 1] - bounds[0, 1] + 1e-6)
    v = (vs[:, 0] - bounds[0, 0]) / (bounds[1, 0] - bounds[0, 0] + 1e-6)
    mesh.visual.uv = np.column_stack([u, v])
    mat = PBRMaterial(
        name=f"mat_{name}",
        baseColorTexture=Image.open(base_tex),
        metallicRoughnessTexture=Image.open(rm_tex),
        normalTexture=Image.open(normal_tex),
        occlusionTexture=Image.open(ao_tex),
        baseColorFactor=(1.0, 1.0, 1.0, 1.0),
    )
    mesh.visual.material = mat
    return mesh

def create_lug(name, width_start, width_end, length, thickness, material_name):
    """表带与机身连接处的包裹片（梯形圆角拉伸体）"""
    # 梯形轮廓：一端宽（包裹机身），一端窄（连接表带）
    hw1 = width_start / 2
    hw2 = width_end / 2
    hh = length / 2
    pts = [
        (hw1, hh), (-hw1, hh), (-hw2, -hh), (hw2, -hh)
    ]
    poly = polygon_from_points(pts)
    mesh = extrude_profile(poly, thickness, name)
    mesh.apply_translation((0, 0, -thickness / 2))
    # 材质
    mat = PBRMaterial(
        name=f"mat_{material_name}",
        baseColorTexture=Image.open(textures[f"{material_name}_base"]),
        metallicRoughnessTexture=Image.open(textures[f"{material_name}_rm"]),
        normalTexture=Image.open(textures[f"{material_name}_normal"]),
        occlusionTexture=Image.open(textures[f"{material_name}_ao"]),
    )
    mesh.visual.material = mat
    return mesh

def planar_uv(mesh):
    """为无 UV 的网格生成简单平面投影 UV（基于 XY 平面）"""
    if mesh.visual.kind == 'texture' and mesh.visual.uv is not None and len(mesh.visual.uv) == len(mesh.vertices):
        return mesh
    bounds = mesh.bounds
    vs = mesh.vertices.copy()
    u = (vs[:, 0] - bounds[0, 0]) / (bounds[1, 0] - bounds[0, 0] + 1e-6)
    v = (vs[:, 1] - bounds[0, 1]) / (bounds[1, 1] - bounds[0, 1] + 1e-6)
    uvs = np.column_stack([u, v])
    mesh.visual = trimesh.visual.TextureVisuals(uv=uvs)
    return mesh

def apply_pbr(mesh, base, rm, normal, ao, alphaMode=None):
    mesh = planar_uv(mesh)
    mat = PBRMaterial(
        baseColorTexture=Image.open(base),
        metallicRoughnessTexture=Image.open(rm),
        normalTexture=Image.open(normal),
        occlusionTexture=Image.open(ao),
    )
    if alphaMode:
        mat.alphaMode = alphaMode
    mesh.visual.material = mat
    return mesh

# ---------------------------------------------------------------------------
# 主机身
# ---------------------------------------------------------------------------
# 1) 铝合金中框（主体）
frame = rounded_box(BODY_W, BODY_L, BODY_T, BODY_R, name="frame")
frame = apply_pbr(frame, textures["frame_base"], textures["frame_rm"], textures["frame_normal"], textures["frame_ao"])

# 2) 2.5D 玻璃盖板（略小于机身，覆盖正面）
glass = rounded_box(GLASS_W + 0.6, GLASS_H + 0.6, 0.6, GLASS_R + 0.3, name="glass")
glass.apply_translation((0, 0, BODY_T / 2 + 0.3))
glass = apply_pbr(glass, textures["glass_base"], textures["glass_rm"], textures["glass_normal"], textures["glass_ao"], alphaMode="BLEND")
# 玻璃透明
glass.visual.material.baseColorFactor = (1, 1, 1, 0.35)

# 3) 屏幕黑边
border = rounded_box(GLASS_W, GLASS_H, 0.05, GLASS_R, name="screen_border")
border.apply_translation((0, 0, BODY_T / 2 + 0.62))
border = apply_pbr(border, textures["border_base"], textures["border_rm"], textures["border_normal"], textures["border_ao"])

# 4) 可自定义屏幕显示区
display = rounded_box(SCREEN_W, SCREEN_H, 0.04, SCREEN_W / 2 - 0.5, name="display")
display.apply_translation((0, 0, BODY_T / 2 + 0.66))
# 为屏幕单独做 UV，使其能完整贴用户上传图片
d_verts = display.vertices.copy()
d_min, d_max = d_verts.min(axis=0), d_verts.max(axis=0)
display.visual.uv = np.column_stack([
    (d_verts[:, 0] - d_min[0]) / (d_max[0] - d_min[0] + 1e-6),
    (d_verts[:, 1] - d_min[1]) / (d_max[1] - d_min[1] + 1e-6),
])
display = apply_pbr(display, textures["display_base"], textures["display_rm"], textures["display_normal"], textures["display_ao"])

# 5) 背面传感器凸起
sensor_poly = polygon_from_points(rounded_rect_points(SENSOR_DIA, SENSOR_DIA, SENSOR_DIA / 2, 24))
sensor = extrude_profile(sensor_poly, SENSOR_PROTRUSION, name="sensor")
sensor.apply_translation((0, 0, -BODY_T / 2 - SENSOR_PROTRUSION / 2))
sensor = apply_pbr(sensor, textures["sensor_base"], textures["sensor_rm"], textures["sensor_normal"], textures["sensor_ao"])

# 6) 充电触点（两个小圆角矩形）
contacts = []
for sign in (-1, 1):
    c_poly = polygon_from_points(rounded_rect_points(CONTACT_W, CONTACT_L, CONTACT_W / 2, 8))
    c = extrude_profile(c_poly, CONTACT_PROTRUSION, name=f"contact_{sign}")
    c.apply_translation((sign * CONTACT_GAP / 2, -SENSOR_DIA / 2 - CONTACT_L, -BODY_T / 2 - CONTACT_PROTRUSION / 2))
    c = apply_pbr(c, textures["contact_base"], textures["contact_rm"], textures["contact_normal"], textures["contact_ao"])
    contacts.append(c)

# ---------------------------------------------------------------------------
# 表带（四套独立模型）
# ---------------------------------------------------------------------------
band_tpu = create_band("band_tpu", BAND_WIDTH, BAND_THICKNESS,
                       textures["tpu_rm"], textures["tpu_base"], textures["tpu_normal"], textures["tpu_ao"])
band_metal = create_band("band_metal", BAND_WIDTH + 1.5, BAND_THICKNESS - 0.3,
                         textures["metal_rm"], textures["metal_base"], textures["metal_normal"], textures["metal_ao"])
band_leather = create_band("band_leather", BAND_WIDTH, BAND_THICKNESS - 0.2,
                           textures["leather_rm"], textures["leather_base"], textures["leather_normal"], textures["leather_ao"])
band_woven = create_band("band_woven", BAND_WIDTH, BAND_THICKNESS - 0.3,
                         textures["woven_rm"], textures["woven_base"], textures["woven_normal"], textures["woven_ao"])

# 表带连接处包裹片（每种表带各两个，与表带材质一致）
lug_length = 5.5
lug_thick = BAND_THICKNESS + 0.4
for band_name, mat_name in [("band_tpu", "tpu"), ("band_metal", "metal"), ("band_leather", "leather"), ("band_woven", "woven")]:
    band = locals()[band_name]
    path = band_path()
    # 在表带两端添加连接片
    for end_idx, sign in [(0, 1), (-1, -1)]:
        p = path[end_idx]
        # 切线方向
        if end_idx == 0:
            tangent = path[1] - path[0]
        else:
            tangent = path[-1] - path[-2]
        tangent = tangent / (np.linalg.norm(tangent) + 1e-9)
        # 连接片中心沿切线向外移动一点
        center = p + sign * tangent * (lug_length / 2)
        # 宽端包裹机身（22mm），窄端接表带（BAND_WIDTH）
        lug = create_lug(f"lug_{band_name}_{end_idx}", BODY_W - 0.6, BAND_WIDTH, lug_length, lug_thick, mat_name)
        # 朝向切线：让连接片长轴沿切线
        # 计算旋转：当前长轴沿 Y，需旋转至 tangent（主要在 YZ 平面）
        # 简化：绕 X 轴旋转使 Y 轴对齐 tangent 在 YZ 平面的投影
        angle_yz = math.atan2(tangent[2], tangent[1])
        # 初始长轴沿 Y；需要旋转 -angle_yz
        lug.apply_transform(trimesh.transformations.rotation_matrix(-angle_yz, [1, 0, 0]))
        lug.apply_translation(center)
        band = trimesh.util.concatenate([band, lug])
    locals()[band_name] = band

# ---------------------------------------------------------------------------
# 合并场景并导出
# ---------------------------------------------------------------------------
scene = trimesh.Scene()
scene.add_geometry(frame, node_name="frame")
scene.add_geometry(glass, node_name="glass")
scene.add_geometry(border, node_name="screen_border")
scene.add_geometry(display, node_name="display")
scene.add_geometry(sensor, node_name="sensor")
for c in contacts:
    scene.add_geometry(c)
scene.add_geometry(band_tpu, node_name="band_tpu")
scene.add_geometry(band_metal, node_name="band_metal")
scene.add_geometry(band_leather, node_name="band_leather")
scene.add_geometry(band_woven, node_name="band_woven")

# 缩放到米（建模单位 mm，导出为 m）
scene.apply_scale(0.001)

GLB_PATH = os.path.join(OUT_DIR, "mi_band10.glb")
scene.export(GLB_PATH)
print(f"[export] {GLB_PATH}")

# ---------------------------------------------------------------------------
# GLB 后处理：补全 bufferView.target、清理无效 alphaCutoff
# ---------------------------------------------------------------------------
def post_process_glb(path):
    from pygltflib import GLTF2, ARRAY_BUFFER, ELEMENT_ARRAY_BUFFER
    gltf = GLTF2().load_binary(path)
    # accessor -> bufferView mapping & target inference
    for mesh in gltf.meshes or []:
        for prim in mesh.primitives or []:
            # indices
            if prim.indices is not None:
                bv = gltf.bufferViews[gltf.accessors[prim.indices].bufferView]
                if bv.target is None:
                    bv.target = ELEMENT_ARRAY_BUFFER
            # attributes
            for attr_idx in prim.attributes.__dict__.values():
                if attr_idx is None:
                    continue
                bv = gltf.bufferViews[gltf.accessors[attr_idx].bufferView]
                if bv.target is None:
                    bv.target = ARRAY_BUFFER
    # 清理 BLEND 材质的 alphaCutoff
    for mat in gltf.materials or []:
        if mat.alphaMode == "BLEND":
            mat.alphaCutoff = None
    gltf.save_binary(path)
    print(f"[post-process] {path}")

post_process_glb(GLB_PATH)

# ---------------------------------------------------------------------------
# 自交检测
# ---------------------------------------------------------------------------
def check_convex_extrusion(mesh, name):
    """凸轮廓拉伸体不存在自交；验证其为闭合流形且边一致。"""
    if not mesh.is_watertight:
        print(f"[self-intersection] {name}: WARN not watertight")
        return False
    print(f"[self-intersection] {name}: OK (convex extrusion, watertight)")
    return True

def check_sweep_band(mesh, path, section_diameter, name):
    """Sweep 表带自交检查：粗采样路径点，间隔足够远的两段若距离小于截面直径则视为自交风险。"""
    # 粗采样，避免相邻段因连续而被误判
    coarse = path[::4]
    n = len(coarse)
    min_dist = float('inf')
    for i in range(n):
        for j in range(i + 2, n):
            d = np.linalg.norm(coarse[i] - coarse[j])
            if d < min_dist:
                min_dist = d
    if min_dist < section_diameter * 0.9:
        print(f"[self-intersection] {name}: FAIL min path distance {min_dist:.3f} mm < section dia {section_diameter:.3f} mm")
        return False
    if not mesh.is_watertight:
        print(f"[self-intersection] {name}: WARN not watertight")
        return False
    print(f"[self-intersection] {name}: OK (min coarse path distance {min_dist:.3f} mm >= section dia {section_diameter:.3f} mm)")
    return True

print("\n[self-intersection checks]")
path = band_path()
for name, geom in [("frame", frame), ("glass", glass), ("border", border), ("display", display),
                   ("sensor", sensor)]:
    check_convex_extrusion(geom, name)

for name, geom, thick in [("band_tpu", band_tpu, BAND_THICKNESS),
                          ("band_metal", band_metal, BAND_THICKNESS - 0.3),
                          ("band_leather", band_leather, BAND_THICKNESS - 0.2),
                          ("band_woven", band_woven, BAND_THICKNESS - 0.3)]:
    check_sweep_band(geom, path, max(BAND_WIDTH, thick), name)

# ---------------------------------------------------------------------------
# glTF 验证
# ---------------------------------------------------------------------------
print("\n[gltf validation]")
import subprocess
VALIDATOR = os.path.join(ROOT, "model", "validate_glb.mjs")
result = subprocess.run(
    ["node", VALIDATOR, GLB_PATH],
    capture_output=True, text=True, timeout=120
)
print(result.stdout)
if result.returncode != 0:
    print(result.stderr)
    raise SystemExit("glTF validation failed")

print("\n[done]")
