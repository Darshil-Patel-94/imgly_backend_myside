import json
from pathlib import Path
from os.path import basename, splitext

def convert_to_scene_json(input_path, output_path):
    # Derive base path from filename
    base_path = Path(output_path).stem  # e.g., 'ogEAwyl0dBCAWo6ILtIBCfhgORzCIWAPVt3h0E'

    with open(input_path, "r", encoding="utf-8") as f:
        template = json.load(f)

    canvas_width = template.get("canvas_config", {}).get("width", 720)
    canvas_height = template.get("canvas_config", {}).get("height", 1280)

    video_materials = template.get("materials", {}).get("videos", [])
    mutable_materials = template.get("mutable_config", {}).get("mutable_materials", [])

    raw_image_blocks = []
    cover_base_names = set()
    x_offset = 50

    # --- Step 1: Collect all video/cover base names ---
    for vid in video_materials:
        cover_path = vid.get("cover_path")
        if cover_path and "video/cover/" in cover_path.replace("\\", "/"):
            base_name = splitext(basename(cover_path))[0]
            cover_base_names.add(base_name)

    # --- Step 2: Add video and cover image blocks ---
    for vid in video_materials:
        cover_path = vid.get("cover_path")
        video_path = vid.get("path")

        if cover_path:
            raw_image_blocks.append({
                "type": "image",
                "uri": f"{base_path}/{cover_path}",
                "source": "cover",
                "origin_path": cover_path,
                "position": {}, "scale": {}
            })

        if video_path:
            raw_image_blocks.append({
                "type": "image",
                "uri": f"{base_path}/{video_path}",
                "source": "video",
                "origin_path": video_path,
                "position": {}, "scale": {}
            })

    # --- Step 3: Add mutable materials ---
    for mat in mutable_materials:
        path = mat.get("cover_path")
        if path:
            raw_image_blocks.append({
                "type": "image",
                "uri": f"{base_path}/{path}",
                "source": "mutable",
                "origin_path": path,
                "position": {}, "scale": {}
            })

    # --- Step 4: Filter video/ blocks if same base name exists in video/cover/ ---
    final_image_blocks = []
    for block in raw_image_blocks:
        path = block["origin_path"].replace("\\", "/")
        if block["source"] == "video" and path.startswith("video/"):
            base_name = splitext(basename(path))[0]
            if base_name in cover_base_names:
                print(f"❌ Skipping video/: {path} (matched in video/cover/)")
                continue
        # Assign position and scale
        block["position"] = {"x": x_offset * (len(final_image_blocks) + 1), "y": 100}
        block["scale"] = {"x": 1.0, "y": 1.0}
        final_image_blocks.append(block)

    # --- Text blocks ---
    text_materials = template.get("materials", {}).get("texts", [])
    text_blocks = []

    for i, text in enumerate(text_materials):
        content = text.get("content", "").strip("[]")
        font_path = text.get("font_path", "")
        size = text.get("text_size", 30)

        if content:
            full_font_path = f"{base_path}/{font_path}" if font_path else ""
            text_blocks.append({
                "type": "text",
                "text": content,
                "position": {"x": 100, "y": 300 + i * 100},
                "scale": {"x": 1.0, "y": 1.0},
                "style": {
                    "font": full_font_path,
                    "fontSize": size,
                    "textAlign": "center"
                }
            })

    # --- Audio blocks ---
    audio_materials = template.get("materials", {}).get("audios", [])
    audio_blocks = []

    for audio in audio_materials:
        path = audio.get("path") or audio.get("url")
        duration = audio.get("duration", 0)
        if path:
            audio_blocks.append({
                "type": "audio",
                "uri": f"{base_path}/{path}",
                "duration": duration*(10**(-5)),
                "position": {"x": 0, "y": 0},
                "metadata": {
                    "start": 0
                }
            })

    # --- Final Scene ---
    scene_json = {
        "scene": {
            "type": "scene",
            "width": canvas_width,
            "height": canvas_height,
            "children": final_image_blocks + text_blocks + audio_blocks
        }
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(scene_json, f, indent=2)

    print(f"✅ Converted .scene file saved to: {output_path}")
