"""Unified Atari challenges: python -m playjev.challenge --help."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import io
import json
import math
import os
import random
import shutil
import subprocess
import threading
import time
import urllib.request
from urllib.parse import urlparse
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from PIL import Image, ImageOps
from playwright.async_api import async_playwright

from .atari import ROOT, Server, observe
from .invaders import geometry, motion
from .defender import geometry as defender_geometry

ASSETS = ROOT.parent / "EmulatorJS/node_modules/@emulatorjs/emulatorjs/data"
ROMS = Path.home() / "Games/roms/Atari 2600 Champion Collection"
SCHEMA = "jev-challenge-v1"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def asset_digest(path):
    """Pin the exact library/core bytes, not a mutable version label."""
    h = hashlib.sha256()
    for file in sorted(p for p in path.rglob("*") if p.is_file()):
        h.update(str(file.relative_to(path)).encode())
        with file.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                h.update(block)
    return h.hexdigest()


class GameAdapter(ABC):
    """New games inherit the same challenge, timing, recording and scoring contract."""
    id: str
    rom_name: str
    goal: str
    actions: dict[str, list[int]]
    hints: str
    # Player-one HUD crop, normalized to screenshot size.
    score_crop: tuple[float, float, float, float]

    def observation(self, frame, mode):
        result = observe(frame)
        result["role_hint"] = self.hints
        if mode == "compact":
            result["foreground_regions"] = [r for r in result["foreground_regions"] if r["pixels"] >= 4]
        return result

    def score_candidate(self, frame):
        """OCR is a candidate ONLY; a human confirms against the final HUD."""
        if not shutil.which("tesseract"):
            return None
        im = Image.open(io.BytesIO(frame)).convert("L")
        box = tuple(round(v * (im.width if i % 2 == 0 else im.height)) for i, v in enumerate(self.score_crop))
        crop = ImageOps.invert(im.crop(box).point(lambda p: 255 if p > 50 else 0)).resize((600, 100))
        buf = io.BytesIO()
        crop.save(buf, "PNG")
        proc = subprocess.run(["tesseract", "stdin", "stdout", "--psm", "7", "-c", "tessedit_char_whitelist=0123456789"],
                              input=buf.getvalue(), capture_output=True, timeout=10)
        text = proc.stdout.decode().strip()
        return int(text) if proc.returncode == 0 and text.isdigit() else None


class SpaceInvaders(GameAdapter):
    id = "space-invaders"
    rom_name = "Space Invaders (NA).a26"
    goal = "Shoot aliens, avoid descending projectiles, and maximize player-one score."
    actions = {"left": [6], "right": [7], "fire": [0], "left+fire": [6, 0], "right+fire": [7, 0], "noop": []}
    hints = "Player is the small wide region near the bottom. Upper small regions are aliens; thin regions may be projectiles; large lower regions are shields. Roles are inferred, not verified."
    score_crop = (0, 0.025, 0.43, 0.10)

    def observation(self, frame, mode):
        return geometry(frame)


class Freeway(GameAdapter):
    id = "freeway"
    rom_name = "Freeway (NA).a26"
    goal = "Move the player-one chicken up across traffic to reach the top repeatedly. Avoid cars; maximize successful crossings."
    actions = {"up": [4], "down": [5], "noop": []}
    hints = "Player one is the chicken on the left side, near x=45 in a 160-wide view. Cars occupy horizontal lanes. Compare previous and current boxes to infer car motion. Roles are inferred, not verified."
    score_crop = (0.15, 0, 0.43, 0.12)

    def observation(self, frame, mode):
        # Exclude gray road and white lane markings; keep colored cars/chickens.
        result = observe(frame, colored_only=True)
        result["role_hint"] = self.hints
        result["foreground_regions"] = [r for r in result["foreground_regions"]
                                        if r["box"][3] - r["box"][1] >= 2]
        if mode == "compact":
            result["foreground_regions"] = [r for r in result["foreground_regions"] if r["pixels"] >= 4]
        return result


class Defender(GameAdapter):
    id = "defender"
    rom_name = "Defender (NA).a26"
    goal = "Maximize player-one Defender high score: shoot hostile ships, avoid enemy missiles/mines, and protect/rescue humanoids."
    directions = {"left":[6], "right":[7], "up":[4], "down":[5],
                  "up-left":[4,6], "up-right":[4,7], "down-left":[5,6], "down-right":[5,7]}
    actions = {"noop":[], "fire":[0], **directions, **{k+"+fire":v+[0] for k,v in directions.items()}}
    hints = "Horizontal scrolling shooter. Joystick moves in eight directions; fire shoots in the facing direction."
    score_crop = (0.32,0.83,0.68,0.90)

    def observation(self, frame, mode):
        return defender_geometry(frame)


GAMES = {g.id: g() for g in (SpaceInvaders, Freeway, Defender)}


class Player(ABC):
    """Policies choose; only the runner may advance the game."""
    @abstractmethod
    async def decide(self, state, game): ...


class JevPlayer(Player):
    def __init__(self, question=None, model="jev-latest"):
        self.question = question
        self.model = model

    async def decide(self, state, game):
        question = self.question or (f"Which short controller action should player one take next? {game.goal} "
                                    "Use the observed geometry and previous observation to infer motion. Choose exactly one action.")
        body = {"model": self.model, "state": state, "questions": {"move": {
            "type": "choice", "instructions": question,
            "criteria": {k: ("Hold " + k.replace("+", " and ") if k != "noop" else "Release controls, wait") for k in game.actions}}}}
        result = await self.request(body)
        answer = self.validate_choice(result["answers"]["move"], game.actions)
        return {"request": body, "response": result, "choice": answer["choice"], "confidence": answer["confidence"]}

    async def request(self, body):
        def send():
            req = urllib.request.Request("https://api.typesafe.ai/v1/systemone", json.dumps(body).encode(),
                {"Authorization": "Bearer " + os.environ["TYPESAFE_API_KEY"], "Content-Type": "application/json"})
            # No hidden retries or fallback policy: failed requests stop and mark run incomplete.
            with urllib.request.urlopen(req, timeout=45) as response:
                return json.load(response)
        return await asyncio.to_thread(send)

    @staticmethod
    def validate_choice(answer, options):
        if answer.get("choice") not in options:
            raise ValueError("Invalid action from Jev")
        probabilities = answer.get("probabilities", {})
        if set(probabilities) != set(options) or any(not isinstance(p, (int, float)) or not math.isfinite(p) or not 0 <= p <= 1 for p in probabilities.values()):
            raise ValueError("Invalid probability distribution from Jev")
        if abs(sum(probabilities.values()) - 1) > 0.02:
            raise ValueError("Probabilities do not sum to one")
        confidence = answer.get("confidence")
        if not isinstance(confidence, (int, float)) or not math.isfinite(confidence) or not 0 <= confidence <= 1:
            raise ValueError("Invalid confidence from Jev")
        return answer


class ComposedJevPlayer(JevPlayer):
    """Independent movement and trigger judgments, combined as controller input."""
    async def decide(self, state, game):
        if game.id != "space-invaders":
            raise ValueError("jev-composed currently supports Space Invaders only")
        if self.question:
            raise ValueError("jev-composed uses its recorded component questions, not --question")
        questions = {
            "movement": {
                "type": "choice",
                "instructions": "Which horizontal movement should player one make during the next action_frames to maximize Space Invaders high score? Compare current and previous geometry. Dodge nearby descending projectiles first, otherwise align underneath remaining aliens. Firing is decided separately, so do not choose stay merely to shoot.",
                "criteria": {"left": "Move left to dodge or align a shot", "right": "Move right to dodge or align a shot", "stay": "Keep the current horizontal position; already safe and aligned or insufficient evidence to move"}},
            "trigger": {
                "type": "choice",
                "instructions": "Should player one hold fire during the next action_frames to maximize Space Invaders high score? Movement may happen simultaneously and is decided independently. Shooting is normally useful when aliens remain.",
                "criteria": {"fire": "Hold fire to shoot remaining enemies", "release": "Release fire when shooting is not useful"}}
        }
        body = {"model": self.model, "state": state, "questions": questions}
        result = await self.request(body)
        components = {key: self.validate_choice(result["answers"][key], q["criteria"]) for key, q in questions.items()}
        movement, trigger = components["movement"]["choice"], components["trigger"]["choice"]
        parts = ([] if movement == "stay" else [movement]) + (["fire"] if trigger == "fire" else [])
        choice = "+".join(parts) or "noop"
        if choice not in game.actions:
            raise ValueError("Composed action is not permitted")
        return {"request": body, "response": result, "choice": choice,
                "confidence": min(a["confidence"] for a in components.values()),
                "components": components, "composition": "movement+trigger; confidence=min-component-v1"}


class GatedJevPlayer(JevPlayer):
    """Jev selects target and safety gates; code performs bounded geometry control."""
    def __init__(self, question=None, model="jev-latest"):
        super().__init__(question, model)
        self.last_player = None
        self.last_seen = None
        self.velocity = 0

    async def decide(self, state, game):
        if game.id != "space-invaders" or self.question:
            raise ValueError("jev-gates requires Space Invaders and its built-in gate questions")
        current, previous = state["current"], state.get("previous")
        now, count = state["game_frame"], state["action_frames"]
        if current["player"]:
            self.last_player, self.last_seen = current["player"], now
        elif current.get("life_indicator_visible"):
            self.last_player, self.last_seen = None, None
        player = self.last_player if self.last_seen is not None and now - self.last_seen <= 120 else None
        px = (player["box"][0] + player["box"][2]) / 2 if player else None
        if previous and len(previous["columns"]) == len(current["columns"]) and current["columns"]:
            shifts = sorted(b["x"] - a["x"] for a, b in zip(previous["columns"], current["columns"]))
            measured = shifts[len(shifts)//2] / max(1, state.get("previous_action_frames", count))
            if abs(measured) < 0.5:
                self.velocity = measured
        candidates = {}
        for col in current["columns"]:
            # Approximate shot travel time in observed coordinates, explicitly logged.
            lead = self.velocity * max(0, (190 - col["lowest_y"]) / 2.5)
            aim_x = max(12, min(148, col["x"] + max(-12, min(12, lead))))
            candidates[col["id"]] = {**col, "aim_x": round(aim_x, 2),
                                      "horizontal_error": round(aim_x - px, 2) if px is not None else None,
                                      "lane_relation": "unknown" if px is None else "already aligned" if abs(aim_x-px)<=3 else "nearby" if abs(aim_x-px)<=12 else "far away",
                                      "travel_direction": "unknown" if px is None else "left" if aim_x < px-2 else "right" if aim_x > px+2 else "stay"}
        projectiles = current.get("projectile_motion", [])
        for p in projectiles:
            p["near_player_lane"] = px is not None and abs(p["x"] - px) <= 10
            p["impact_within_action"] = p["direction"] == "down" and p["vy"] > 0 and 0 <= (190-p["y"])/p["vy"] <= count + 12
            p["threatens_staying"] = p["near_player_lane"] and p["impact_within_action"]
        paths = {}
        for direction, speed in (("left",-0.5),("right",0.5),("stay",0)):
            conflicts = []
            for p in projectiles:
                if p["direction"] == "up":
                    continue
                vy = p["vy"] if p["direction"] == "down" else 0.4
                if vy <= 0 or px is None:
                    continue
                impact = max(0, (183-p["y"])/vy)
                future_x = max(12, min(148, px + speed*min(impact,18)))
                if impact <= count + 12 and abs(future_x-p["x"]) <= 6:
                    conflicts.append({"laser_x":p["x"],"impact_in_frames":round(impact,1),"tracked":p["direction"]=="down"})
            paths[direction] = {"movement":direction,"predicted_collisions":conflicts,"collision_predicted":bool(conflicts),
                                "edge_blocked":px is None or (direction=="left" and px<=14) or (direction=="right" and px>=146)}
        # Keep raw images/geometry in runner logs; the model needs derived motion,
        # collision paths and firing lanes, not duplicate current/previous sprites.
        gate_state = {"game":game.id,"game_frame":now,"action_frames":count,
                      "control": {"player_x": px, "player_age_frames": now - self.last_seen if player else None,
                      "projectile_tracks": projectiles, "immediate_threat": any(p["threatens_staying"] for p in projectiles),
                      "escape_paths":paths,
                      "alien_velocity_x_per_frame": self.velocity, "targets": candidates,
                      "screen_bounds": [12, 148], "previous_action": state.get("previous_action"),
                      "lead_estimate": "shot speed approx 2.5 y pixels/frame, capped 12 x pixels; inference only"}}
        questions = {
            "threat": {"type": "choice", "instructions": "Is a descending enemy projectile likely to hit player one during the next action_frames? Use control.projectile_tracks and immediate_threat. Tracks are measured over nearby frames: down is an enemy bomb, up is our shot. threatens_staying=true means dodge now. Consider untracked low projectiles near the player too. Do not treat upward shots or distant bullets as threats.",
                       "criteria": {"danger": "An approaching descending projectile near the player's x threatens impact soon", "safe": "No immediate evidence of impact; continue targeting aliens"}},
            "dodge": {"type": "choice", "instructions": "If an enemy projectile threatens player one, choose an escape path without predicted collisions or blocked edges from control.escape_paths. Prefer moving away from the threatening laser. Collision timing and paths are already computed; do not redo the arithmetic. Stay only if it is safe or no moving path is safer.", "criteria": paths},
            "target": {"type": "choice", "instructions": "Which firing lane gives player one a useful chance to hit an alien? control.targets summarizes observed alien-colored pixels along each lane, with motion-adjusted aim_x. Prefer already aligned lanes that still have targets, otherwise nearby lanes. Avoid far away lanes when a nearer useful lane exists. This chooses a lane, not controller direction; code times alignment. Hold only when player or targets are unknown.",
                       "criteria": {**{k: "Choose firing lane described in control.targets."+k for k in candidates}, "hold": "No reliable target or player position; keep position"}},
            "trigger": {"type": "choice", "instructions": "Should player one fire to clear the Space Invaders wave? Hold fire while any aliens remain, including while dodging or repositioning; release only if no useful enemies are visible.",
                        "criteria": {"fire": "Shoot remaining enemies", "release": "No useful enemies visible"}}
        }
        body = {"model": self.model, "state": gate_state, "questions": questions}
        result = await self.request(body)
        gates = {key: self.validate_choice(result["answers"][key], q["criteria"]) for key, q in questions.items()}
        danger = gates["threat"]["choice"] == "danger" or paths["stay"]["collision_predicted"]
        target = candidates.get(gates["target"]["choice"])
        error = target["horizontal_error"] if target and px is not None else None
        movement = gates["dodge"]["choice"] if danger else ("stay" if error is None or abs(error) <= 2 else "right" if error > 0 else "left")
        movement_frames = min(count, 18) if danger else min(count, max(0, round(abs(error or 0) / 0.5)))
        guard = None
        if danger and paths[movement]["collision_predicted"]:
            safe = [k for k, p in paths.items() if not p["collision_predicted"] and not p["edge_blocked"]]
            if safe:
                movement = max(safe, key=lambda k:gates["dodge"]["probabilities"][k])
                movement_frames = min(count,18) if movement != "stay" else 0
                guard = "collision-veto; highest-Jev-probability-safe-path"
        if px is None:
            movement, movement_frames, guard = "stay", 0, "player-position-unknown"
        elif movement != "stay":
            edge_distance = px - 12 if movement == "left" else 148 - px
            capped = min(movement_frames, max(0, int(edge_distance / 0.5)))
            if capped != movement_frames:
                guard = "screen-edge-frame-cap"
            movement_frames = capped
            if not movement_frames:
                movement = "stay"
        fire = gates["trigger"]["choice"] == "fire"
        parts = ([] if movement == "stay" else [movement]) + (["fire"] if fire else [])
        choice = "+".join(parts) or "noop"
        confidence = min(gates[k]["confidence"] for k in ("threat", "dodge" if danger else "target", "trigger"))
        return {"request": body, "response": result, "choice": choice, "confidence": confidence,
                "components": gates, "composition": "threat?dodge:target-servo; independent-fire; bounded-movement-v1",
                "movement_frames": movement_frames if movement != "stay" else 0,
                "rest_choice": "fire" if fire else "noop", "guard": guard,
                "safety_gate":danger,
                "target_x": target["aim_x"] if target else None}


class DefenderJevPlayer(JevPlayer):
    """Same gate composition, Defender's two-dimensional joystick instead of a servo."""
    async def decide(self, state, game):
        if self.question:
            raise ValueError("Defender gates use their recorded component questions, not --question")
        directions = {"stay":"Keep position", **{k:"Move "+k.replace("-"," and ") for k in game.directions}}
        questions = {
            "movement": {"type":"choice", "instructions":"Which joystick direction should the Defender ship take next? Use current and previous colored regions to infer the player's position and missiles. Dodge incoming fire, otherwise align vertically with hostile ships and fly toward them. Keep moving to avoid pursuit. The upper radar and lower city are not enemy ships. Stay if the player is not observable during a respawn.", "criteria":directions},
            "trigger": {"type":"choice", "instructions":"Should Defender fire now? Fire starts the initial game if no ship has appeared yet. Once active, fire when facing enemies in the main playfield. Firing below the city consumes a limited smart bomb; firing behind the upper scanner triggers hyperspace. Avoid those unless escape or clearing many nearby threats warrants it. Humanoids are immune to our missiles in this Atari version.",
                        "criteria":{"fire":"Hold fire to shoot or deliberately use the normal in-game escape/bomb mechanic", "release":"Release fire to conserve bombs or avoid unnecessary hyperspace"}}
        }
        body = {"model":self.model,"state":state,"questions":questions}
        result = await self.request(body)
        gates = {k:self.validate_choice(result["answers"][k],q["criteria"]) for k,q in questions.items()}
        direction = gates["movement"]["choice"]
        parts = ([] if direction=="stay" else [direction]) + (["fire"] if gates["trigger"]["choice"]=="fire" else [])
        choice = "+".join(parts) or "noop"
        return {"request":body,"response":result,"components":gates,"choice":choice,
                "confidence":min(g["confidence"] for g in gates.values()),
                "composition":"Defender-2D-movement+independent-trigger-v1"}


class OllayaGatedPlayer(GatedJevPlayer):
    """Identical gates/controller; only the inference transport/model changes."""
    def __init__(self, question=None, model="kev:0.8b", endpoint="http://127.0.0.1:11435"):
        super().__init__(question, model)
        url = urlparse(endpoint)
        if url.scheme != "http" or url.hostname not in ("127.0.0.1","localhost","::1") or url.username or url.password or url.query or url.fragment or url.path not in ("","/"):
            raise ValueError("Ollaya endpoint must be a plain loopback HTTP URL")
        self.endpoint = endpoint.rstrip("/")

    async def request(self, body):
        def send():
            headers = {"Content-Type":"application/json"}
            if os.environ.get("OLLAYA_API_KEY"):
                headers["Authorization"] = "Bearer " + os.environ["OLLAYA_API_KEY"]
            # Explicit loopback transport: never send the TypeSafe credential
            # locally, never use a system proxy, never silently fall back to Jev.
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            answers, responses, subrequests = {}, [], []
            for key, question in body["questions"].items():
                # The 6GB GPU cannot fit four long question contexts together.
                # Questions are independent; preserve their exact state/rubrics
                # while serializing inference. Never truncate or change controls.
                part = {**body,"questions":{key:question}}
                req = urllib.request.Request(self.endpoint+"/v1/systemone",json.dumps(part).encode(),headers)
                with opener.open(req,timeout=180) as response:
                    result = json.load(response)
                answers.update(result["answers"])
                responses.append(result)
                subrequests.append(part)
            return {"model":responses[0]["model"],"answers":answers,
                    "usage":{k:sum(r["usage"][k] for r in responses) for k in ("input_tokens","output_tokens")},
                    "transport":"sequential-single-question","subrequests":subrequests,"subresponses":responses}
        return await asyncio.to_thread(send)


class BaselinePlayer(Player):
    def __init__(self, policy, seed=0):
        self.policy, self.rng = policy, random.Random(seed)

    async def decide(self, state, game):
        choice = self.rng.choice(list(game.actions)) if self.policy == "random" else next(k for k in ("fire", "up") if k in game.actions)
        return {"choice": choice, "confidence": None, "baseline": self.policy}


class EmulatorSession:
    """All execution goes through EmulatorJS's browser API."""
    def __init__(self, assets, rom, visible=False, video_dir=None, speed=0.25):
        self.assets, self.rom, self.visible, self.video_dir, self.speed = assets, rom, visible, video_dir, speed

    async def __aenter__(self):
        self.server = Server(self.assets, self.rom)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.pw = await async_playwright().start()
        try:
            self.browser = await self.pw.chromium.launch(headless=not self.visible,
                args=["--autoplay-policy=no-user-gesture-required", "--enable-unsafe-swiftshader"])
            opts = {"viewport": {"width": 640, "height": 520}}
            if self.video_dir:
                opts.update(record_video_dir=str(self.video_dir), record_video_size={"width": 640, "height": 520})
            self.context = await self.browser.new_context(**opts)
            self.started_wall = time.monotonic()
            self.page = await self.context.new_page()
            await self.page.add_init_script("""(() => {
                const raf = window.requestAnimationFrame.bind(window);
                window.frameTarget = null; window.frameDelay = 0;
                window.requestAnimationFrame = cb => raf(t => {
                    const run = () => {
                        cb(t);
                        const e = window.EJS_emulator;
                        if (window.frameTarget !== null && e?.gameManager && e.gameManager.getFrameNum() >= window.frameTarget) {
                            e.pause(); window.frameTarget = null;
                            window.finishFrames?.(); window.finishFrames = null;
                        }
                    };
                    if (window.frameTarget !== null && window.frameDelay) setTimeout(run, window.frameDelay);
                    else run();
                });
            })();""")
            await self.page.goto(f"http://127.0.0.1:{self.server.server_port}/")
            await self.page.wait_for_function("window.started === true", timeout=120000)
            await self.page.evaluate("EJS_emulator.pause()")
            return self
        except BaseException:
            await self.__aexit__(None, None, None)
            raise

    async def __aexit__(self, *exc):
        try:
            if hasattr(self, "context"):
                await self.context.close()  # flush video before browser exits
            if hasattr(self, "browser"):
                await self.browser.close()
            if hasattr(self, "pw"):
                await self.pw.stop()
        finally:
            self.server.shutdown()
            self.server.server_close()

    async def frames(self, buttons, count, slow=True):
        result = await self.page.evaluate("""async ({buttons, count, delay}) => {
            const e = EJS_emulator, gm = e.gameManager;
            const before = gm.getFrameNum();
            window.frameDelay = delay; window.frameTarget = before + count;
            for (const b of buttons) gm.simulateInput(0,b,1);
            try {
                await new Promise((resolve, reject) => {
                    const timer = setTimeout(() => { e.pause(); window.frameTarget=null; reject(new Error('Frame advance timed out')); }, 30000);
                    window.finishFrames = () => { clearTimeout(timer); resolve(); };
                    e.play();
                });
            } finally {
                e.pause(); for (const b of buttons) gm.simulateInput(0,b,0);
            }
            return gm.getFrameNum() - before;
        }""", {"buttons": buttons, "count": count, "delay": (1000/60 * (1/self.speed - 1)) if slow else 0})
        if result != count:
            raise RuntimeError(f"Requested {count} emulator frames, got {result}; run cannot be ranked")
        return result

    async def capture(self):
        return await self.page.locator("canvas.ejs_canvas").screenshot()

    async def save(self):
        return bytes(await self.page.evaluate("Array.from(EJS_emulator.gameManager.getState())"))

    async def restore(self, data):
        await self.page.evaluate("data => EJS_emulator.gameManager.loadState(new Uint8Array(data))", list(data))

    async def restore_matching(self, snapshot, expected):
        # loadState queues a core command: its first callback can load without
        # advancing, or load and advance once. Stop at exact canonical state,
        # not at an assumed number of renderer callbacks. Setup only.
        await self.restore(snapshot)
        for frames in range(1, 9):
            await self.frames([], 1, slow=False)
            ready = await self.save()
            if digest(ready) == expected:
                return ready, frames
        raise ValueError("Canonical restored emulator state was not reached; run cannot be ranked")


async def create(args):
    game = GAMES[args.game]
    rom = args.rom or ROMS / game.rom_name
    args.directory.mkdir(parents=True, exist_ok=False)
    async with EmulatorSession(args.assets, rom, speed=1) as env:
        await env.frames([3], 9, slow=False)
        await env.frames([], 30, slow=False)
        snapshot = await env.save()
        (args.directory / "start.state").write_bytes(snapshot)
        # Canonical first frame after restore, also used by every run.
        await env.restore(snapshot)
        await env.frames([], 3, slow=False)
        initial = await env.capture()
        (args.directory / "start.png").write_bytes(initial)
        ready = await env.save()
        (args.directory / "ready.state").write_bytes(ready)
    contract = {"schema": SCHEMA, "game": game.id, "rom_sha256": digest(rom.read_bytes()),
                "assets_sha256": asset_digest(args.assets), "state_sha256": digest(snapshot),
                "initial_frame_sha256": digest(initial), "budget_frames": round(args.seconds * 60),
                "ready_state_sha256": digest(ready),
                "fps": 60, "scoring": "human-confirmed-player-one-high-score-v1"}
    metadata = {**contract, "challenge_id": digest(json.dumps(contract, sort_keys=True).encode()),
                "rom_path": str(rom.resolve()), "assets_path": str(args.assets.resolve())}
    (args.directory / "challenge.json").write_text(json.dumps(metadata, indent=2))
    print(f"Challenge saved: {args.directory} ({contract['budget_frames']} frames)")


def replay_html(directory, summary, records):
    payload = json.dumps({"summary": summary, "records": records}).replace("<", "\\u003c")
    (directory / "replay.html").write_text("""<!doctype html><meta charset='utf-8'><title>Jev replay</title>
<style>body{background:#151515;color:#eee;font:16px monospace;max-width:1000px;margin:24px auto}video{width:640px;max-width:100%}pre{white-space:pre-wrap}button{margin:8px}</style>
<h1>Atari benchmark replay — paused inference, not continuous live play</h1><p id='outcome'></p><video id='video' controls src='replay.webm'></video>
<p>Playback speed <select id='speed'><option>0.25</option><option>0.5</option><option selected>1</option><option>2</option></select>
<button id='prev'>Previous decision</button><button id='next'>Next decision</button></p><pre id='info'></pre><details><summary>Run metadata</summary><pre id='meta'></pre></details>
<script>const data=""" + payload + """;
const video=document.getElementById('video'), info=document.getElementById('info');
document.getElementById('meta').textContent=JSON.stringify(data.summary,null,2);
if(data.summary.playback_mode==='continuous')document.querySelector('h1').textContent='Continuous Atari replay — asynchronous Jev decisions';
document.getElementById('outcome').textContent=data.summary.game_over_candidate?'Stopped or padded after a suspected game over; visual review required.':data.summary.status==='complete'?'Test frame budget reached. This does not mean the game was completed.':'Test ended before its frame budget.';
if(data.summary.playback_mode==='continuous')document.getElementById('outcome').textContent=data.summary.game_over_candidate?'Stopped at a suspected game over; not automatically verified.':'Stopped by user or explicit smoke-test cap. No game-completion claim.';
document.getElementById('speed').onchange=e=>video.playbackRate=Number(e.target.value);
function index(){let i=0;data.records.forEach((r,j)=>{if(r.video_time_s<=video.currentTime)i=j});return i}
video.ontimeupdate=()=>{const r=data.records[index()];info.textContent=r?JSON.stringify({step:r.step,game_time_s:r.game_frame/60,action:r.decision.choice,confidence:r.decision.confidence,gates:r.decision.components,guard:r.decision.guard,terminal_hold:r.decision.terminal_hold,executed_segments:r.executed_segments,inference_s:r.latency_s,frames:r.frames},null,2):'No decisions recorded'};
for(const [id,d] of [['prev',-1],['next',1]]) document.getElementById(id).onclick=()=>{const i=Math.max(0,Math.min(data.records.length-1,index()+d));if(data.records[i])video.currentTime=data.records[i].video_time_s};
video.onloadedmetadata=()=>{if(data.records.length)video.currentTime=data.records[0].video_time_s};
</script>""")


async def run(args, player=None):
    metadata = json.loads((args.challenge / "challenge.json").read_text())
    if metadata["schema"] != SCHEMA:
        raise ValueError("Unknown challenge schema")
    game = GAMES[metadata["game"]]
    rom, assets = Path(metadata["rom_path"]), Path(metadata["assets_path"])
    snapshot = (args.challenge / "start.state").read_bytes()
    for label, actual in (("rom", digest(rom.read_bytes())), ("assets", asset_digest(assets)), ("state", digest(snapshot))):
        if actual != metadata[label + "_sha256"]:
            raise ValueError(f"Challenge {label} bytes changed")
    load_dotenv(ROOT.parent / ".env", override=False)
    hosted = args.player in ("jev", "jev-composed", "jev-gates")
    if args.player == "ollaya-gates" and args.model == "jev-latest":
        args.model = "kev:0.8b"
    if player is None and hosted and not os.environ.get("TYPESAFE_API_KEY"):
        raise ValueError("TYPESAFE_API_KEY is required")
    question = args.question.read_text() if args.question else None
    player = player or (OllayaGatedPlayer(question,args.model,getattr(args,"ollaya_url","http://127.0.0.1:11435")) if args.player == "ollaya-gates" else
                        DefenderJevPlayer(question,args.model) if args.player == "jev-gates" and game.id == "defender" else
                        GatedJevPlayer(question, args.model) if args.player == "jev-gates" else
                        ComposedJevPlayer(question, args.model) if args.player == "jev-composed" else
                        JevPlayer(question, args.model) if hosted else BaselinePlayer(args.player, args.seed))
    out = args.out or ROOT / "runs/challenges" / f"{metadata['game']}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}-{os.urandom(3).hex()}"
    out.mkdir(parents=True, exist_ok=False)
    config = {"player": args.player, "player_class": type(player).__name__, "model": args.model if hosted or args.player=="ollaya-gates" else None, "observation": args.observation,
              "question": question, "action_frames": args.action_frames, "speed": args.speed, "watch_delay": args.watch_delay, "seed": args.seed}
    config["source_sha256"] = {name:digest((ROOT/"playjev"/name).read_bytes()) for name in ("challenge.py","invaders.py","defender.py")}
    config["policy_version"] = "laser-gates-compact-v2" if args.player in ("jev-gates","ollaya-gates") and game.id=="space-invaders" else None
    if args.player=="ollaya-gates":
        config["ollaya_url"] = player.endpoint
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(player.endpoint+"/api/tags",timeout=10) as response:
            tags = json.load(response)["models"]
        config["model_manifest"] = next((r for r in tags if r["name"]==args.model), None)
    summary = {"schema": SCHEMA, "challenge_id": metadata["challenge_id"], "game": game.id,
               "budget_frames": metadata["budget_frames"], "config": config, "status": "incomplete", "score": None,
               "metric": "highest-observed-player-one-hud-score",
               "score_candidate": None, "score_verified": False, "game_frames": 0, "decisions": 0}
    records, previous, elapsed = [], None, 0
    terminal = False
    recent_motion = []
    min_aliens = None
    try:
        async with EmulatorSession(assets, rom, args.visible, out / "video", args.speed) as env:
            await env.frames([], 40, slow=False)  # finish core/video initialization before loading state
            ready, setup_frames = await env.restore_matching(snapshot, metadata["ready_state_sha256"])
            frame = await env.capture()
            (out / "restored.png").write_bytes(frame)
            summary["restore_setup_callbacks"] = setup_frames
            (out / "restored.state").write_bytes(ready)
            if digest(ready) != metadata["ready_state_sha256"]:
                raise ValueError("Restored emulator state differs; run cannot be ranked")
            (out / "start.png").write_bytes(frame)
            with (out / "decisions.jsonl").open("w") as log:
                while elapsed < metadata["budget_frames"]:
                    current = game.observation(frame, args.observation)
                    if game.id == "space-invaders":
                        current["projectile_motion"] = recent_motion
                    count = min(args.action_frames, metadata["budget_frames"] - elapsed)
                    if args.player in ("jev-gates","ollaya-gates") and any(p["direction"] != "up" and p["y"] > 145 for p in recent_motion):
                        count = min(count, 12)  # more frequent Jev decisions near low incoming lasers
                    state = {"game": game.id, "goal": game.goal, "current": current,
                             "previous": previous if args.observation != "single" else None,
                             "game_frame": elapsed, "action_frames": count, "emulator_paused_during_inference": True}
                    state["previous_action"] = records[-1]["decision"]["choice"] if records else None
                    state["previous_action_frames"] = records[-1]["frames"] if records else None
                    await env.page.locator("#status").evaluate("(el,text)=>el.textContent=text", f"{args.player} | {elapsed/60:.2f}s | choosing…")
                    wall = time.monotonic() - env.started_wall
                    t0 = time.monotonic()
                    decision = ({"choice":"noop","confidence":None,"terminal_hold":"Observed game-over color cycle; no fire/restart allowed"}
                                if terminal else await player.decide(state, game))
                    latency = time.monotonic() - t0
                    record = {"step": len(records), "game_frame": elapsed, "frames": count, "video_time_s": wall,
                              "latency_s": latency, "state": state, "decision": decision}
                    component_text = " | " + ", ".join(f"{k}={v['choice']} ({v['confidence']:.2f})" for k, v in decision.get("components", {}).items()) if decision.get("components") else ""
                    safety_text = f" | DODGE={decision['safety_gate']}" if "safety_gate" in decision else ""
                    await env.page.locator("#status").evaluate("(el,text)=>el.textContent=text", f"{args.player} | {elapsed/60:.2f}s | {decision['choice']} | confidence {decision['confidence']}" + safety_text + component_text)
                    await asyncio.sleep(args.watch_delay)
                    record["action_video_time_s"] = time.monotonic() - env.started_wall
                    moving = decision.get("movement_frames", count)
                    if not isinstance(moving, int) or not 0 <= moving <= count:
                        raise ValueError("Invalid bounded movement duration")
                    actual = 0
                    plan = [(decision["choice"], moving)]
                    if moving < count:
                        plan.append((decision["rest_choice"], count-moving))
                    record["executed_segments"] = []
                    for selected, duration in plan:
                        if terminal:
                            break
                        while duration:
                            chunk = min(6, duration)
                            before_image = frame
                            executed = "noop" if terminal else selected
                            actual += await env.frames(game.actions[executed], chunk)
                            frame = await env.capture()
                            if game.id == "space-invaders":
                                observed = geometry(frame)
                                recent_motion = motion(geometry(before_image), observed, chunk)
                                if not observed["background_black"] and not terminal:
                                    terminal = True
                                    summary["game_over_candidate"] = {"step":len(records),"game_frame":elapsed+actual,"reason":"background-color-cycle"}
                                    (out/"game-over.png").write_bytes(frame)
                            elif game.id == "defender" and not defender_geometry(frame)["background_black"] and not terminal:
                                terminal = True
                                summary["game_over_candidate"] = {"step":len(records),"game_frame":elapsed+actual,"reason":"background-color-cycle"}
                                (out/"game-over.png").write_bytes(frame)
                            record["executed_segments"].append({"choice":executed,"frames":chunk})
                            duration -= chunk
                            if terminal:
                                break
                    record["actual_frames"] = actual
                    elapsed += actual
                    frame = await env.capture()
                    (out / f"frame-{len(records):04}.png").write_bytes(frame)
                    record["after_frame_sha256"] = digest(frame)
                    if game.id == "defender" and not defender_geometry(frame)["background_black"] and not terminal:
                        terminal = True
                        summary["game_over_candidate"] = {"step":len(records),"game_frame":elapsed,"reason":"background-color-cycle"}
                    if game.id == "space-invaders":
                        after = geometry(frame)
                        n = after["alien_count"]
                        record["alien_count"] = n
                        record["projectile_motion"] = recent_motion
                        # Candidate only: reviewer must inspect disappearance and fresh wave.
                        if min_aliens is not None and min_aliens <= 3 and n >= 30 and "stage_clear_candidate" not in summary:
                            summary["stage_clear_candidate"] = {"step": len(records), "game_frame": elapsed,
                                                                 "before_minimum": min_aliens, "new_aliens": n,
                                                                 "verified": False}
                        min_aliens = n if min_aliens is None else min(min_aliens, n)
                    record["score_candidate"] = await asyncio.to_thread(game.score_candidate, frame)
                    candidate = record["score_candidate"]
                    if candidate is not None and (summary["score_candidate"] is None or candidate > summary["score_candidate"]):
                        summary["score_candidate"] = candidate
                    records.append(record)
                    log.write(json.dumps(record) + "\n")
                    log.flush()
                    previous = current
                    print(f"{elapsed/60:.2f}s / {metadata['budget_frames']/60:.2f}s: {decision['choice']} confidence={decision['confidence']}", flush=True)
                    if terminal:
                        break
            (out / "final.png").write_bytes(frame)
            summary["status"] = "complete" if elapsed == metadata["budget_frames"] else "terminated"
            summary["outcome"] = "suspected-game-over-review-required" if terminal else "test-budget-reached"
            summary["game_completed"] = False
            summary["playback_mode"] = "paused-inference-benchmark"
    except BaseException as exc:
        summary["error"] = type(exc).__name__ + ": " + str(exc)
        raise
    finally:
        summary.update(game_frames=elapsed, decisions=len(records))
        summary["api_requests"] = sum(len(r["decision"].get("response",{}).get("subrequests",[])) or int("request" in r["decision"]) for r in records)
        videos = list((out / "video").glob("*.webm"))
        if videos:
            videos[0].rename(out / "replay.webm")
        (out / "summary.json").write_text(json.dumps(summary, indent=2))
        replay_html(out, summary, records)
        print(f"Run saved: {out}\nReplay: {out / 'replay.html'}")


def confirm_score(args):
    file = args.run / "summary.json"
    summary = json.loads(file.read_text())
    evidence = (args.run / args.frame).resolve()
    if not evidence.is_relative_to(args.run.resolve()) or evidence.suffix != ".png" or not evidence.is_file():
        raise ValueError("Score evidence must be a saved PNG inside the run folder")
    if summary["status"] != "complete":
        raise ValueError("Only completed runs may be scored")
    summary.update(score=args.value, score_verified=True,
                   score_review={"method": "reviewed-high-score-hud", "reviewer": args.reviewer, "note": args.note,
                                 "evidence": args.frame, "evidence_sha256": digest(evidence.read_bytes()),
                                 "at": datetime.now(timezone.utc).isoformat()})
    file.write_text(json.dumps(summary, indent=2))
    records = [json.loads(line) for line in (args.run / "decisions.jsonl").read_text().splitlines()]
    replay_html(args.run, summary, records)
    print(f"Confirmed player-one high score: {args.value}")


def compare(args):
    rows = [(p, json.loads((p / "summary.json").read_text())) for p in args.runs]
    groups = {}
    for path, row in rows:
        groups.setdefault(row["challenge_id"], []).append((path, row))
    for challenge, items in groups.items():
        print(f"\nChallenge {challenge[:12]} (scores never ranked across games/challenges)")
        eligible = [(p, r) for p, r in items if r["status"] == "complete" and r["game_frames"] == r["budget_frames"] and r["score_verified"]]
        for rank, (path, row) in enumerate(sorted(eligible, key=lambda x: x[1]["score"], reverse=True), 1):
            print(f"{rank}. {row['score']}  {path}  {json.dumps(row['config'])}")
        for path, row in items:
            if (path, row) not in eligible:
                print(f"Unranked: {path} ({row['status']}; confirmed score={row['score_verified']}; OCR candidate={row['score_candidate']})")


async def experiment(args):
    variants = json.loads(args.config.read_text())
    allowed = {"name", "player", "model", "observation", "action_frames", "question", "seed"}
    if not isinstance(variants, list) or not variants:
        raise ValueError("Experiment config must be a nonempty list")
    names = set()
    for variant in variants:
        if not isinstance(variant, dict) or set(variant) - allowed:
            raise ValueError("Unknown experiment settings")
        name = variant.get("name", "")
        if not name or Path(name).name != name or name in (".", ".."):
            raise ValueError("Variant name must be a single directory name")
        if name in names:
            raise ValueError("Variant names must be unique")
        names.add(name)
    for variant in variants:
        settings = argparse.Namespace(challenge=args.challenge, out=args.out / variant["name"], visible=args.visible,
            speed=args.speed, watch_delay=args.watch_delay, player="jev", model="jev-latest", observation="regions",
            action_frames=6, question=None, seed=0)
        for key, value in variant.items():
            if key != "name":
                setattr(settings, key, (args.config.parent / value) if key == "question" else value)
        validate_run(settings)
        await run(settings)


def validate_run(a):
    if a.player not in ("jev", "jev-composed", "jev-gates", "ollaya-gates", "fixed", "random") or a.observation not in ("regions", "compact", "single"):
        raise ValueError("Unknown player or observation mode")
    if not isinstance(a.action_frames, int) or not 1 <= a.action_frames <= 60 or not 0 < a.speed <= 1 or not 0 <= a.watch_delay <= 10:
        raise ValueError("action-frames: 1..60; speed: (0,1]; watch-delay: 0..10")


def cli():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    c = sub.add_parser("create", help="Save an immutable ROM/state/frame-budget challenge")
    c.add_argument("game", choices=GAMES)
    c.add_argument("directory", type=Path)
    c.add_argument("--seconds", type=float, default=30)
    c.add_argument("--rom", type=Path)
    c.add_argument("--assets", type=Path, default=ASSETS)
    r = sub.add_parser("run", help="Play and record one challenge; default watch speed is 0.25x")
    r.add_argument("challenge", type=Path)
    r.add_argument("--player", choices=("jev", "jev-composed", "jev-gates", "ollaya-gates", "fixed", "random"), default="jev")
    r.add_argument("--model", default="jev-latest")
    r.add_argument("--ollaya-url", default="http://127.0.0.1:11435", help="Loopback Ollaya server; never receives the TypeSafe key")
    r.add_argument("--observation", choices=("regions", "compact", "single"), default="regions")
    r.add_argument("--question", type=Path)
    r.add_argument("--action-frames", type=int, default=6)
    r.add_argument("--seed", type=int, default=0)
    r.add_argument("--out", type=Path)
    for cmd in (r,):
        cmd.add_argument("--visible", action="store_true")
        cmd.add_argument("--speed", type=float, default=0.25)
        cmd.add_argument("--watch-delay", type=float, default=0.25)
    e = sub.add_parser("experiment", help="Run a JSON list of variants on the same challenge")
    e.add_argument("challenge", type=Path)
    e.add_argument("config", type=Path)
    e.add_argument("--out", type=Path, required=True)
    e.add_argument("--visible", action="store_true")
    e.add_argument("--speed", type=float, default=0.25)
    e.add_argument("--watch-delay", type=float, default=0.25)
    s = sub.add_parser("score", help="Confirm player-one high score against a saved HUD frame/replay")
    s.add_argument("run", type=Path)
    s.add_argument("value", type=int)
    s.add_argument("--note", required=True)
    s.add_argument("--frame", default="final.png", help="Saved PNG showing the highest observed score")
    s.add_argument("--reviewer", choices=("human","assistant"), default="human")
    co = sub.add_parser("compare", help="Rank confirmed scores only within matching challenges")
    co.add_argument("runs", nargs="+", type=Path)
    board = sub.add_parser("leaderboard", help="Build local high-score board with evidence links")
    board.add_argument("runs", nargs="*", type=Path, help="Default: discover all run summaries under runs/")
    board.add_argument("--out", type=Path, default=ROOT/"runs/scoreboard")
    a = p.parse_args()
    if a.command == "create":
        if not math.isfinite(a.seconds) or not 1 <= a.seconds <= 120:
            p.error("seconds must be between 1 and 120")
        asyncio.run(create(a))
    elif a.command == "run":
        validate_run(a)
        asyncio.run(run(a))
    elif a.command == "experiment":
        asyncio.run(experiment(a))
    elif a.command == "score":
        if a.value < 0:
            p.error("score must be nonnegative")
        confirm_score(a)
    elif a.command == "leaderboard":
        from .scoreboard import build
        build(a.runs or [p.parent for p in (ROOT/"runs").rglob("summary.json")], a.out)
    else:
        compare(a)


if __name__ == "__main__":
    cli()
