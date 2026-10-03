"""Run one of the Interactive Graphics projects headlessly and save frames.

The application runs unmodified. This script swaps in a fixed-step clock, scripted
keyboard and mouse input, and an offscreen OpenGL window, then reads frames back
from the GPU. It is used to regenerate the README media and, in CI, as a smoke
test that every project starts, renders and responds to input.

    python tools/render_tour.py "Interactive Graphics/Helios Orrery" tools/tours/helios-orrery.json -o out
    python tools/render_tour.py "Interactive Graphics/Helios Orrery" --smoke

A tour file is JSON:

    {
      "size": [1280, 720],            window size
      "desktop": [2560, 1440],        optional desktop size reported to the app
      "fps": 30,                      fixed simulation rate
      "frames": 300,                  frames to run before exiting
      "seed": 7,                      seeds Python's random module
      "events": {"45": [["key", "2"], ["hold", "w"], ["motion", 12, 0], ["wheel", 1]],
                 "46": [["keyup", "2"], ["release", "w"]]},
      "shots": {"104": "vortex"},     frame number -> PNG name
      "clip": [45, 345, "tour", 2],   frames start..end, every Nth, into <out>/<name>/
      "autopilot": [40, 2400]         Embervault only: walk the solved route
    }

It needs a working OpenGL driver. On Linux without a display, SDL's offscreen
driver with Mesa (llvmpipe) works: SDL_VIDEODRIVER=offscreen.
"""

import argparse
import json
import math
import os
import random
import runpy
import sys

SMOKE_TOUR = {
    "size": [960, 540],
    "desktop": [1120, 720],
    "fps": 30,
    "frames": 75,
    "events": {"30": [["key", "2"]], "31": [["keyup", "2"]], "50": [["key", "return"]], "51": [["keyup", "return"]]},
    "shots": {"74": "smoke"},
}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("project", help="project folder that contains main.py")
    parser.add_argument("tour", nargs="?", help="tour JSON file")
    parser.add_argument("-o", "--out", default="tour-output", help="output folder (default: tour-output)")
    parser.add_argument("--smoke", action="store_true", help="run a short built-in tour and check the frame")
    args = parser.parse_args()

    if args.smoke:
        tour = SMOKE_TOUR
    elif args.tour:
        with open(args.tour, encoding="utf-8") as handle:
            tour = json.load(handle)
    else:
        parser.error("give a tour file or --smoke")

    project = os.path.abspath(args.project)
    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    random.seed(tour.get("seed", 7))

    runner = TourRunner(project, tour, out)
    frames = runner.run()

    if args.smoke:
        from PIL import Image, ImageStat

        image = Image.open(os.path.join(out, "smoke.png"))
        spread = max(high - low for low, high in image.getextrema())
        if frames < tour["frames"] or spread < 24:
            print(f"FAIL {os.path.basename(project)}: {frames} frames, pixel range {spread}")
            sys.exit(1)
        mean = ImageStat.Stat(image).mean
        print(f"PASS {os.path.basename(project)}: {frames} frames, mean RGB {[round(v) for v in mean]}")
    else:
        print(f"{os.path.basename(project)}: {frames} frames written to {out}")


class TourRunner:
    def __init__(self, project, tour, out):
        self.project = project
        self.tour = tour
        self.out = out
        self.frame = 0
        self.ms = 0
        self.held = set()
        self.clip_frames = []
        self.game = None

    def run(self):
        os.chdir(self.project)
        sys.path.insert(0, self.project)
        sys.argv = [os.path.join(self.project, "main.py")]
        self.patch_pygame()
        try:
            runpy.run_path(os.path.join(self.project, "main.py"), run_name="__main__")
        except SystemExit:
            pass
        return self.frame

    # --- pygame replacements -------------------------------------------------

    def patch_pygame(self):
        import pygame

        self.pg = pygame
        step = int(1000 / self.tour.get("fps", 30))
        runner = self

        class Clock:
            def __init__(self, *args):
                pass

            def tick(self, *args):
                return step

            tick_busy_loop = tick

            def get_fps(self):
                return float(runner.tour.get("fps", 30))

            def get_time(self):
                return step

        class Pressed:
            def __getitem__(self, key):
                return key in runner.held

        real_get = pygame.event.get
        real_set_mode = pygame.display.set_mode
        real_flip = pygame.display.flip

        def get_events(*args, **kwargs):
            real_get()
            return runner.events_for(runner.frame)

        def set_mode(size=(0, 0), flags=0, *args, **kwargs):
            flags &= ~pygame.FULLSCREEN
            return real_set_mode(tuple(runner.tour.get("size", size)), flags, *args, **kwargs)

        def flip():
            runner.before_flip()
            real_flip()
            runner.after_flip(step)

        pygame.event.get = get_events
        pygame.time.Clock = Clock
        pygame.time.get_ticks = lambda: runner.ms
        pygame.display.set_mode = set_mode
        pygame.display.flip = flip
        pygame.key.get_pressed = lambda: Pressed()
        pygame.mouse.get_rel = lambda: (0, 0)
        pygame.mouse.get_pressed = lambda *args, **kwargs: (False, False, False)

        if self.tour.get("desktop"):
            width, height = self.tour["desktop"]

            class Info:
                current_w, current_h = width, height

            pygame.display.Info = lambda: Info()
            pygame.display.get_desktop_sizes = lambda: [(width, height)]

        self.update_held()

    def key(self, name):
        constant = getattr(self.pg, "K_" + name, None)
        return constant if constant is not None else self.pg.key.key_code(name)

    def events_for(self, frame):
        pygame = self.pg
        events = []
        for event in self.tour.get("events", {}).get(str(frame), []):
            kind = event[0]
            if kind in ("key", "keyup"):
                kind_id = pygame.KEYDOWN if kind == "key" else pygame.KEYUP
                text = event[1] if len(event[1]) == 1 else ""
                events.append(pygame.event.Event(kind_id, key=self.key(event[1]), unicode=text, mod=0, scancode=0))
            elif kind == "drag":
                start, end = (640, 360), (640 + event[1], 360 + event[2])
                events.append(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=start))
                events.append(pygame.event.Event(pygame.MOUSEMOTION, rel=(event[1], event[2]), pos=end, buttons=(1, 0, 0)))
                events.append(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=end))
            elif kind == "motion":
                events.append(pygame.event.Event(pygame.MOUSEMOTION, rel=(event[1], event[2]), pos=(640, 360), buttons=(0, 0, 0)))
            elif kind == "wheel":
                events.append(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=event[1], flipped=False,
                                                 precise_x=0.0, precise_y=float(event[1])))
        return events

    def update_held(self):
        for event in self.tour.get("events", {}).get(str(self.frame), []):
            if event[0] == "hold":
                self.held.add(self.key(event[1]))
            elif event[0] == "release":
                self.held.discard(self.key(event[1]))

    # --- per-frame work ------------------------------------------------------

    def before_flip(self):
        self.autopilot()
        shot = self.tour.get("shots", {}).get(str(self.frame))
        if shot:
            self.grab().save(os.path.join(self.out, shot + ".png"))
        clip = self.tour.get("clip")
        if clip and clip[0] <= self.frame < clip[1] and (self.frame - clip[0]) % (clip[3] if len(clip) > 3 else 1) == 0:
            self.clip_frames.append(self.grab())

    def after_flip(self, step):
        self.frame += 1
        self.ms += step
        self.update_held()
        if self.frame >= self.tour["frames"]:
            self.save_clip()
            raise SystemExit(0)

    def grab(self):
        from OpenGL import GL
        from PIL import Image

        width, height = self.pg.display.get_surface().get_size()
        GL.glPixelStorei(GL.GL_PACK_ALIGNMENT, 1)
        data = GL.glReadPixels(0, 0, width, height, GL.GL_RGB, GL.GL_UNSIGNED_BYTE)
        return Image.frombytes("RGB", (width, height), data).transpose(Image.FLIP_TOP_BOTTOM)

    def save_clip(self):
        clip = self.tour.get("clip")
        if not clip or not self.clip_frames:
            return
        folder = os.path.join(self.out, clip[2])
        os.makedirs(folder, exist_ok=True)
        for index, image in enumerate(self.clip_frames):
            image.save(os.path.join(folder, f"{index:04d}.png"))

    def autopilot(self):
        """Embervault: steer along the maze's solved route and keep walking."""
        span = self.tour.get("autopilot")
        if not span or not span[0] <= self.frame < span[1]:
            return
        if self.game is None:
            import gc

            self.game = next((item for item in gc.get_objects()
                              if isinstance(item, dict) and "maze" in item and "yaw" in item), None)
        game = self.game
        if not game or game.get("show_help"):
            return
        game["jumpscare_enabled"] = False
        cell_size = 3.0
        path = game["maze"]["path"]
        cell = (int(game["x"] // cell_size), int(game["y"] // cell_size))
        index = path.index(cell) if cell in path else 0
        target = path[min(index + 1, len(path) - 1)]
        target_x, target_y = (target[0] + 0.5) * cell_size, (target[1] + 0.5) * cell_size
        wanted = math.atan2(target_y - game["y"], target_x - game["x"])
        error = (wanted - game["yaw"] + math.pi) % (2 * math.pi) - math.pi
        game["yaw"] += max(-0.07, min(0.07, error))
        game["pitch"] = -0.04
        forward = self.key("w")
        if abs(error) < 0.35:
            self.held.add(forward)
        else:
            self.held.discard(forward)


if __name__ == "__main__":
    main()
