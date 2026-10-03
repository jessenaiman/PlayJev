"""Defender visual observations; no ROM memory reads or writes."""
import io
from PIL import Image
from .invaders import components


def geometry(frame):
    im = Image.open(io.BytesIO(frame)).convert("RGB").resize((160,210), Image.Resampling.NEAREST)
    masks = {}
    for y in range(15,190):
        for x in range(160):
            rgb = im.getpixel((x,y))
            if max(rgb) < 55:
                continue
            color = tuple((c//32)*32 for c in rgb)
            masks.setdefault(color,[]).append((x,y))
    regions = []
    for rgb, mask in sorted(masks.items()):
        for r in components(mask):
            regions.append({**r,"rgb":list(rgb)})
    regions.sort(key=lambda r:(r["box"][1],r["box"][0]))
    main = [r for r in regions if 40 <= r["box"][1] < 155 and r["pixels"] < 200]
    # Ship flashes between pale blue and pink; its wide, shallow wedge is more
    # reliable than a single color. Defender is anchored near x31 facing right.
    players = [r for r in main if 25<=r["box"][0]<=38 and 5<=r["box"][2]-r["box"][0]<=10 and r["box"][3]-r["box"][1]<=5]
    return {"coordinates":"160x210; x right, y down", "player_candidate":max(players,key=lambda r:r["pixels"],default=None),
            "main_objects":main,"background_black":max(im.getpixel((5,100)))<30,
            "scanner_regions":[r for r in regions if r["box"][3]<40 and r["pixels"]<100],
            "role_hint":"Wide shallow wedge near x31 is probably Defender; it flashes pale blue/pink. Upper scanner y12..37; main playfield y40..154; blue city below y155; lives, bombs and score below y175. Other colored sprites may be enemies, missiles or humanoids. Compare previous frames. No offscreen enemy state is read."}
