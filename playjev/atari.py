"""EmulatorJS Atari Space Invaders + hosted TypeSafe Jev (no local weights)."""
import argparse
import asyncio
import io
import json
import os
import threading
import time
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from dotenv import load_dotenv
from PIL import Image
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
ACTIONS = {"left": [6], "right": [7], "fire": [0],
           "left+fire": [6, 0], "right+fire": [7, 0], "noop": []}


def observe(data, colored_only=False):
    """Connected foreground regions; geometry is observed, roles are inferred."""
    im = Image.open(io.BytesIO(data)).convert("RGB").resize((160, 210))
    pixels = im.load()
    todo = {(x, y) for y in range(20, 205) for x in range(160)
            if max(pixels[x, y]) > 65 and (not colored_only or max(pixels[x, y]) - min(pixels[x, y]) > 35)}
    regions = []
    while todo:
        start = todo.pop()
        stack, group = [start], [start]
        while stack:
            x, y = stack.pop()
            for p in ((x-1, y), (x+1, y), (x, y-1), (x, y+1)):
                if p in todo:
                    todo.remove(p)
                    stack.append(p)
                    group.append(p)
        if len(group) < 2:
            continue
        xs, ys = zip(*group)
        box = [min(xs), min(ys), max(xs), max(ys)]
        regions.append({"box": box, "pixels": len(group)})
    regions.sort(key=lambda r: (r["box"][1], r["box"][0]))
    return {"coordinates": "160x210; x increases right, y increases down",
            "foreground_regions": regions[:100],
            "role_hint": "Bottom small wide region is usually player; upper small regions are aliens; narrow regions may be projectiles; large lower regions are shields. These are hints, not confirmed labels."}


def ask(state):
    body = {"model": "jev-latest", "state": state, "questions": {"move": {
        "type": "choice", "instructions": "Which move should the Space Invaders player make next to shoot aliens and avoid descending projectiles? Compare current and previous regions to infer movement. Choose only one short controller action.",
        "criteria": {name: "Hold " + name.replace("+", " and ") if name != "noop" else "Release all controls; stay still" for name in ACTIONS}}}}
    req = urllib.request.Request("https://api.typesafe.ai/v1/systemone",
        json.dumps(body).encode(), {"Authorization": "Bearer " + os.environ["TYPESAFE_API_KEY"], "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=45) as response:
        result = json.load(response)
    answer = result["answers"]["move"]
    if answer["choice"] not in ACTIONS:
        raise ValueError("Jev returned an unknown action")
    return result


class Server(ThreadingHTTPServer):
    def __init__(self, assets, rom):
        self.assets, self.rom = assets.resolve(), rom.resolve()
        super().__init__(("127.0.0.1", 0), Handler)


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/":
            data = (ROOT / "games/emulatorjs/index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(data)
        elif path == "/rom.a26":
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.end_headers()
            self.wfile.write(self.server.rom.read_bytes())
        elif path.startswith("/data/"):
            super().do_GET()
        else:
            self.send_error(404)

    def translate_path(self, path):
        from urllib.parse import unquote
        relative = unquote(path.split("?", 1)[0]).removeprefix("/data/")
        target = (self.server.assets / relative).resolve()
        if not target.is_relative_to(self.server.assets):
            return str(self.server.assets / "__not_found__")
        return str(target)


async def main(args):
    load_dotenv(ROOT.parent / ".env", override=False)
    if not args.smoke and not os.environ.get("TYPESAFE_API_KEY"):
        raise RuntimeError("Set TYPESAFE_API_KEY in the environment or parent .env")
    if not args.rom.is_file() or not (args.assets / "loader.js").is_file():
        raise RuntimeError("ROM or EmulatorJS assets missing")
    server = Server(args.assets, args.rom)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    args.out.mkdir(parents=True, exist_ok=True)
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=not args.visible,
                args=["--autoplay-policy=no-user-gesture-required", "--enable-unsafe-swiftshader"])
            try:
                page = await browser.new_page(viewport={"width": 640, "height": 480})
                await page.goto(f"http://127.0.0.1:{server.server_port}/")
                await page.wait_for_function("window.started === true", timeout=120000)
                async def advance(buttons, seconds):
                    await page.evaluate("buttons => { const e=EJS_emulator; for (const b of buttons) e.gameManager.simulateInput(0,b,1); e.play(); }", buttons)
                    await asyncio.sleep(seconds)
                    await page.evaluate("buttons => { const e=EJS_emulator; e.pause(); for (const b of buttons) e.gameManager.simulateInput(0,b,0); }", buttons)
                await advance([3], 0.15)  # Atari console reset starts a game
                await advance([], 0.5)
                previous = None
                with (args.out / "decisions.jsonl").open("a") as log:
                    for step in range(args.steps):
                        frame = await page.locator("canvas.ejs_canvas").screenshot()
                        (args.out / f"frame-{step:04}.png").write_bytes(frame)
                        current = observe(frame)
                        state = {"game": "Atari 2600 Space Invaders", "current": current, "previous": previous,
                                 "action_duration_seconds": args.interval, "emulator_paused_during_inference": True}
                        t0 = time.monotonic()
                        result = {"answers": {"move": {"choice": "fire", "confidence": None}}} if args.smoke else await asyncio.to_thread(ask, state)
                        answer = result["answers"]["move"]
                        log.write(json.dumps({"step": step, "state": state, "response": result, "latency_s": time.monotonic()-t0}) + "\n")
                        log.flush()
                        print(f"{step}: {answer['choice']} confidence={answer['confidence']}", flush=True)
                        await advance(ACTIONS[answer["choice"]], args.interval)
                        previous = current
            finally:
                await browser.close()
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--rom", type=Path, default=Path.home()/"Games/roms/Atari 2600 Champion Collection/Space Invaders (NA).a26")
    p.add_argument("--assets", type=Path, default=ROOT.parent/"EmulatorJS/data")
    p.add_argument("--steps", type=int, default=30)
    p.add_argument("--interval", type=float, default=0.1)
    p.add_argument("--visible", action="store_true")
    p.add_argument("--smoke", action="store_true", help="Test emulator with fixed fire actions; no Jev calls")
    p.add_argument("--out", type=Path, default=ROOT/"runs/atari")
    a = p.parse_args()
    if a.steps < 1 or not 0 < a.interval <= 1:
        p.error("steps must be positive and interval must be between 0 and 1")
    asyncio.run(main(a))
