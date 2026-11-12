# Original WolfGamingZA tag source

The source uses blackened steel, gold and forest green, with an original angular
wolf crest. No artwork or model from the referenced Workshop mod is included.

- `wgza_tag.blend`: editable Blender 4.3 scene, including presentation camera/lights.
- `wgza_tag.obj` / `.mtl`: artist geometry/material interchange; dimensions are metres.
- `wgza_tag_preview.png`: concept render, not an in-game screenshot.
- Generator: `blender --background --threads 2 --python tools/create_assets.py`.

These files are **not shipped in the runtime PBO**. Before replacing the vanilla
placeholder, use DayZ Tools to finish the asset pipeline:

1. Bake the logo and lettering detail into textures and simplify the geometry
   for a small inventory item. Presentation text meshes are not game-ready LODs.
2. Add the visual, view, shadow and required physical/geometry LODs, mass and
   named selections in Object Builder. Remove the presentation background,
   camera and lights if importing the Blender scene.
3. UV unwrap and convert textures with TexView2; author the relevant RVMATs.
4. Export/binarize a P3D with the correct virtual asset paths. Add it and its
   textures/materials under `WGZA_DogTags/data/`, then update `model` in config.cpp.
5. Rebuild, sign and verify the item in hands, cargo, on the ground and in the
   dedicated player slot using the real server/client test guide.

The native engine skeleton does not gain a new visible attachment proxy from a
config slot alone. A worn, externally visible tag/chain needs separate character
proxy/model work; the first version's dedicated slot is an inventory feature.
