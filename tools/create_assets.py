"""Original model source and concept render. Run with Blender 4.3+:

blender --background --threads 2 --python tools/create_assets.py

This produces artist source files, not a DayZ-ready P3D/PAA asset.
"""

from pathlib import Path
import math

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets"


def material(name, color, metallic=0.0, roughness=0.4):
    result = bpy.data.materials.new(name)
    result.diffuse_color = (*color, 1)
    result.use_nodes = True
    shader = result.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color, 1)
    shader.inputs["Metallic"].default_value = metallic
    shader.inputs["Roughness"].default_value = roughness
    return result


def polygon(name, points, depth, mat):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([(x, y, depth) for x, y in points], [], [tuple(range(len(points)))])
    mesh.update()
    result = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(result)
    result.data.materials.append(mat)
    return result


def text(name, value, y, size, mat):
    curve = bpy.data.curves.new(name, "FONT")
    curve.body = value
    curve.align_x = "CENTER"
    curve.size = size
    curve.extrude = 0.000008
    curve.resolution_u = 3
    result = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(result)
    result.location = (0, y, 0.00083)
    result.data.materials.append(mat)
    return result


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    steel = material("WGZA blackened steel", (0.025, 0.035, 0.038), 0.88, 0.32)
    gold = material("WGZA brushed gold", (0.73, 0.48, 0.13), 0.8, 0.3)
    green = material("WGZA forest green", (0.06, 0.35, 0.2), 0.45, 0.35)
    lettering = material("WGZA light engraving", (0.7, 0.76, 0.72), 0.6, 0.4)
    corners = []
    # 28 x 48 x 1.6 mm plate, four 4 mm-radius corners.
    for cx, cy, start in ((0.010, 0.020, 0), (-0.010, 0.020, 90), (-0.010, -0.020, 180), (0.010, -0.020, 270)):
        for step in range(9):
            angle = math.radians(start + step * 90 / 8)
            corners.append((cx + 0.004 * math.cos(angle), cy + 0.004 * math.sin(angle)))
    count = len(corners)
    vertices = [(x, y, z) for z in (-0.0008, 0.0008) for x, y in corners]
    faces = [tuple(reversed(range(count))), tuple(range(count, count * 2))]
    for index in range(count):
        following = (index + 1) % count
        faces.append((index, following, following + count, index + count))
    mesh = bpy.data.meshes.new("WGZA rounded steel blank")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    plate = bpy.data.objects.new("WGZA tag plate", mesh)
    bpy.context.collection.objects.link(plate)
    plate.data.materials.append(steel)
    bpy.context.view_layer.objects.active = plate
    plate.select_set(True)
    bevel = plate.modifiers.new("Machined edge", "BEVEL")
    bevel.width = 0.00015
    bevel.segments = 2
    bpy.ops.object.modifier_apply(modifier=bevel.name)

    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.0017, depth=0.01, location=(0, 0.0185, 0))
    cutter = bpy.context.object
    bpy.context.view_layer.objects.active = plate
    hole = plate.modifiers.new("Chain eyelet hole", "BOOLEAN")
    hole.operation = "DIFFERENCE"
    hole.solver = "EXACT"
    hole.object = cutter
    bpy.ops.object.modifier_apply(modifier=hole.name)
    bpy.data.objects.remove(cutter, do_unlink=True)
    bpy.ops.mesh.primitive_torus_add(major_segments=32, minor_segments=8, location=(0, 0.0185, 0.0008), major_radius=0.00195, minor_radius=0.00025)
    eyelet = bpy.context.object
    eyelet.name = "WGZA gold eyelet"
    eyelet.data.materials.append(gold)

    # Original angular wolf mark. No traced or downloaded logo is used.
    wolf = [(-0.0065, 0.0125), (-0.0058, 0.0020), (-0.0034, -0.0010), (0, -0.0040), (0.0034, -0.0010), (0.0058, 0.0020), (0.0065, 0.0125), (0.0028, 0.0090), (-0.0028, 0.0090)]
    polygon("WGZA original wolf crest", wolf, 0.00084, gold)
    polygon("WGZA wolf central plane", [(0, 0.008), (0.0028, 0.009), (0.0048, 0.004), (0, -0.004)], 0.00086, green)
    polygon("WGZA left eye", [(-0.0046, 0.0055), (-0.0014, 0.0041), (-0.0027, 0.0032)], 0.00088, steel)
    polygon("WGZA right eye", [(0.0046, 0.0055), (0.0014, 0.0041), (0.0027, 0.0032)], 0.00088, steel)
    polygon("WGZA nose", [(-0.0011, -0.0008), (0.0011, -0.0008), (0, -0.002)], 0.00088, steel)
    text("WGZA main engraving", "WOLF", -0.0085, 0.0045, gold)
    text("WGZA name engraving", "G A M I N G  Z A", -0.0120, 0.0016, lettering)
    polygon("WGZA green rule", [(-0.009, -0.014), (0.009, -0.014), (0.009, -0.0144), (-0.009, -0.0144)], 0.00084, green)
    text("WGZA identity engraving", "SURVIVOR", -0.0181, 0.0023, lettering)
    text("WGZA motto engraving", "IDENTITY / MEMORY / LEGACY", -0.0211, 0.0009, gold)

    # Capture only artist geometry before creating the presentation scene.
    geometry = list(bpy.context.scene.objects)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in geometry:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = plate
    bpy.ops.object.convert(target="MESH")
    bpy.ops.wm.obj_export(filepath=str(OUTPUT / "wgza_tag.obj"), export_selected_objects=True, export_materials=True, apply_modifiers=True)

    background = material("Preview background", (0.017, 0.025, 0.027), 0.0, 0.85)
    bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, -0.002))
    bpy.context.object.name = "Preview background (not game geometry)"
    bpy.context.object.data.materials.append(background)
    bpy.ops.object.camera_add(location=(0.022, -0.032, 0.115))
    camera = bpy.context.object
    camera.rotation_euler = (Vector((0, 0, 0)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 0.069
    scene = bpy.context.scene
    scene.camera = camera
    for name, location, energy, size in (
        ("Warm key", (-0.04, 0.05, 0.08), 0.18, 0.065),
        ("Soft fill", (0.04, -0.02, 0.05), 0.09, 0.05),
    ):
        bpy.ops.object.light_add(type="AREA", location=location)
        light = bpy.context.object
        light.name = name
        light.data.energy = energy
        light.data.shape = "DISK"
        light.data.size = size
        light.rotation_euler = (-light.location).to_track_quat("-Z", "Y").to_euler()
    scene.world = bpy.data.worlds.new("WGZA studio")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs[0].default_value = (0.18, 0.2, 0.23, 1)
    scene.world.node_tree.nodes["Background"].inputs[1].default_value = 0.25
    scene.view_settings.exposure = -0.7
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 32
    # This cloud Blender build does not include OpenImageDenoise.
    scene.cycles.use_denoising = False
    scene.render.resolution_x = 720
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(OUTPUT / "wgza_tag_preview.png")
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / "wgza_tag.blend"))
    bpy.ops.render.render(write_still=True)
    print("WGZA artist sources exported. P3D/PAA conversion and game LODs remain required.")


if __name__ == "__main__":
    main()
