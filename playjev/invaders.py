"""Read-only screenshot geometry for the supplied Space Invaders ROM."""
import io
from PIL import Image


def components(points):
    points = set(points)
    result = []
    while points:
        seed = points.pop()
        stack, group = [seed], [seed]
        while stack:
            x, y = stack.pop()
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    p = (x + dx, y + dy)
                    if p in points:
                        points.remove(p)
                        stack.append(p)
                        group.append(p)
        if len(group) >= 2:
            xs, ys = zip(*group)
            result.append({"box": [min(xs), min(ys), max(xs), max(ys)], "pixels": len(group)})
    return sorted(result, key=lambda r: (r["box"][1], r["box"][0]))


def geometry(frame):
    im = Image.open(io.BytesIO(frame)).convert("RGB").resize((160, 210), Image.Resampling.NEAREST)
    masks = {"aliens": [], "player": [], "projectiles": [], "shields": [], "life_indicator": []}
    for y in range(20, 199):
        for x in range(160):
            r, g, b = im.getpixel((x, y))
            if r > 100 and g > 100 and b < 60 and y < 185:
                masks["aliens"].append((x, y))
            elif g > r + 35 and g > b + 35 and y >= 175:
                masks["player"].append((x, y))
            elif min(r, g, b) > 80 and max(r, g, b) - min(r, g, b) < 20:
                masks["projectiles"].append((x, y))
            elif r > g + 50 and r > b + 50:
                masks["shields"].append((x, y))
            elif r > 140 and 100 < g < 160 and 30 < b < 80 and 180 <= y < 195:
                masks["life_indicator"].append((x, y))
    groups = {k: components(v) for k, v in masks.items()}
    groups["aliens"] = [r for r in groups["aliens"] if r["pixels"] >= 8 and r["box"][2] - r["box"][0] >= 3]
    groups["player"] = [r for r in groups["player"] if r["box"][2] - r["box"][0] >= 3]
    player = max(groups["player"], key=lambda r: r["pixels"], default=None)
    columns = []
    for alien in sorted(groups["aliens"], key=lambda r: r["box"][0]):
        x = (alien["box"][0] + alien["box"][2]) / 2
        col = next((c for c in columns if abs(c["x"] - x) < 5), None)
        if col is None:
            col = {"x": x, "aliens": []}
            columns.append(col)
        col["aliens"].append(alien)
    for i, col in enumerate(columns):
        col.update(id=f"column_{i}", remaining=len(col["aliens"]),
                   lowest_y=max(a["box"][3] for a in col["aliens"]))
        del col["aliens"]
    background = im.getpixel((5, 140))
    return {"coordinates": "160x210; x right, y down", "player": player,
            "aliens": groups["aliens"], "alien_count": len(groups["aliens"]), "columns": columns,
            "projectiles": groups["projectiles"], "shields": groups["shields"],
            "life_indicator_visible": bool(groups["life_indicator"]),
            "background_black": max(background) < 30,
            "role_hint": "Color/geometry labels are ROM-specific visual inferences. Gray projectiles may travel either way; compare previous frames. Missing player can be sprite flicker or death; do not assume a position."}


def motion(previous, current, frames):
    """Associate gray segments over a short, known interval; no emulator memory."""
    tracks = []
    remaining = list(previous["projectiles"])
    for p in current["projectiles"]:
        x = (p["box"][0] + p["box"][2]) / 2
        y = (p["box"][1] + p["box"][3]) / 2
        candidates = [q for q in remaining if abs(q["box"][0] - x) <= 3 and
                      abs((q["box"][1] + q["box"][3])/2 - y) <= frames*3 + 3]
        old = min(candidates, key=lambda q: abs((q["box"][1]+q["box"][3])/2 - y), default=None)
        if old:
            remaining.remove(old)
        vy = (y - (old["box"][1]+old["box"][3])/2) / frames if old else None
        tracks.append({"x":x, "y":y, "vy":vy,
                       "direction":"down" if vy is not None and vy > 0.05 else "up" if vy is not None and vy < -0.05 else "unknown"})
    return tracks
