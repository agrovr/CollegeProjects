import ctypes
import math
import os

import pygame
from pygame.locals import DOUBLEBUF, FULLSCREEN, KEYDOWN, K_a, K_d, K_ESCAPE
from pygame.locals import K_b, K_DOWN, K_F10, K_F11, K_h, K_j, K_LEFT, K_m
from pygame.locals import K_n, K_q, K_r, K_RETURN, K_RIGHT, K_s
from pygame.locals import K_SPACE, K_UP, K_w
from pygame.locals import MOUSEMOTION, OPENGL, QUIT

import audio
import graphics
import maze


MAZE_WIDTH = 12
MAZE_HEIGHT = 12
CELL_SIZE = 3.0
WALL_HEIGHT = 2.8
PLAYER_RADIUS = 0.31

NORMAL_SPEED = 3.25
BOOST_SPEED = 5.35
SLOW_SPEED = 1.18
MOUSE_SENSITIVITY = 0.0024

EASTER_EGG_KEYS = (
    K_UP, K_UP, K_DOWN, K_DOWN,
    K_LEFT, K_RIGHT, K_LEFT, K_RIGHT,
    K_b, K_a,
)


def enable_high_dpi():
    os.environ["SDL_VIDEO_CENTERED"] = "1"
    os.environ["SDL_WINDOWS_DPI_AWARENESS"] = "permonitorv2"
    if os.name == "nt":
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            pass


def choose_resolutions():
    display = pygame.display.Info()
    available_width = max(480, display.current_w - 160)
    available_height = max(270, display.current_h - 180)
    presets = [(960, 540), (1280, 720), (1600, 900), (1920, 1080)]
    choices = [
        size for size in presets
        if size[0] <= available_width and size[1] <= available_height
    ]

    if not choices:
        width = available_width
        height = int(width * 9.0 / 16.0)
        if height > available_height:
            height = available_height
            width = int(height * 16.0 / 9.0)

        choices.append((width - width % 2, height - height % 2))

    return choices


def create_window(width, height, fullscreen=False):
    pygame.display.gl_set_attribute(pygame.GL_DEPTH_SIZE, 24)
    pygame.display.gl_set_attribute(pygame.GL_DOUBLEBUFFER, 1)
    pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 1)
    pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, 4)

    flags = DOUBLEBUF | OPENGL
    if fullscreen:
        flags |= FULLSCREEN
    try:
        return pygame.display.set_mode((width, height), flags, vsync=1)
    except pygame.error:
        pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 0)
        pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, 0)
        return pygame.display.set_mode((width, height), flags)


def recreate_display(width, height, fullscreen, folder, textures):
    graphics.delete_textures(textures)
    pygame.display.quit()
    pygame.display.init()
    create_window(width, height, fullscreen)
    pygame.display.set_caption(
        "Embervault: The Shifting Forge"
    )
    graphics.initialize_opengl()
    textures = graphics.load_textures(folder)
    pygame.event.set_grab(True)
    pygame.mouse.set_visible(False)
    pygame.mouse.get_rel()
    return textures


def current_time():
    return pygame.time.get_ticks() / 1000.0


def start_direction(maze_data):
    if len(maze_data["path"]) < 2:
        return 0.0

    start_x, start_y = maze_data["path"][0]
    next_x, next_y = maze_data["path"][1]
    return math.atan2(next_y - start_y, next_x - start_x)


def show_message(game, text, now, duration=2.6):
    game["message"] = text
    game["message_until"] = now + duration


def set_help_visible(game, visible, now):
    if visible == game["show_help"]:
        return

    if visible:
        game["show_help"] = True
        game["help_started"] = now
        game["moving"] = False
        return

    paused_for = max(0.0, now - game["help_started"])
    if game["finish_time"] is None:
        game["start_time"] += paused_for

    for timer_name in (
        "boost_until", "slow_until", "sight_until",
        "lift_until", "message_until", "scare_until",
    ):
        if game[timer_name] > game["help_started"]:
            game[timer_name] += paused_for

    game["last_step_time"] += paused_for
    game["show_help"] = False


def check_easter_egg(game, key, now, audio_data=None):
    if game["easter_egg"]:
        return False

    progress = game["secret_progress"]
    if key == EASTER_EGG_KEYS[progress]:
        progress += 1
        if progress == len(EASTER_EGG_KEYS):
            game["easter_egg"] = True
            game["secret_progress"] = 0
            show_message(game, "PHOENIX OVERRIDE: eternal sight", now, 4.0)
            if audio_data:
                audio.play(audio_data, "pickup")
            return True
    else:
        progress = 1 if key == EASTER_EGG_KEYS[0] else 0

    game["secret_progress"] = progress
    return False


def toggle_jumpscare(game, now):
    game["jumpscare_enabled"] = not game["jumpscare_enabled"]
    if not game["jumpscare_enabled"]:
        game["scare_until"] = 0.0
    state = "enabled" if game["jumpscare_enabled"] else "disabled"
    show_message(game, f"Jump scare {state}", now, 2.0)


def reset_player(game, now, reset_items=True):
    start_x, start_y = maze.cell_center(game["maze"]["start"], CELL_SIZE)
    game["x"] = start_x
    game["y"] = start_y
    game["yaw"] = start_direction(game["maze"])
    game["pitch"] = -0.04
    game["previous_cell"] = game["maze"]["start"]
    game["start_time"] = now
    game["finish_time"] = None
    game["won"] = False
    game["boost_until"] = 0.0
    game["slow_until"] = 0.0
    game["sight_until"] = 0.0
    game["lift_until"] = 0.0
    game["moving"] = False
    game["walk_phase"] = 0.0
    game["camera_bob"] = 0.0
    game["last_step_time"] = now
    game["scare_started"] = 0.0
    game["scare_until"] = 0.0
    game["scare_triggered"] = False

    if reset_items:
        game["collected"] = set()
        game["activated"] = set()
        game["sight_charges"] = 1


def make_game(now):
    game = {
        "maze": maze.generate_maze(MAZE_WIDTH, MAZE_HEIGHT),
        "message": "",
        "message_until": 0.0,
        "collected": set(),
        "activated": set(),
        "sight_charges": 1,
        "show_help": True,
        "help_started": now,
        "jumpscare_enabled": True,
        "easter_egg": False,
        "secret_progress": 0,
    }
    reset_player(game, now)
    show_message(game, "Find the cyan rift gate", now, 3.2)
    return game


def reset_same_maze(game, now, audio_data=None):
    reset_player(game, now)
    show_message(game, "Vault reset", now)
    if audio_data:
        audio.play(audio_data, "turn")


def generate_new_maze(game, now, audio_data=None):
    game["maze"] = maze.generate_maze(MAZE_WIDTH, MAZE_HEIGHT)
    reset_player(game, now)
    show_message(game, "The forge has shifted", now, 3.0)
    if audio_data:
        audio.play(audio_data, "turn")


def teleport_to_start(game):
    start_x, start_y = maze.cell_center(game["maze"]["start"], CELL_SIZE)
    game["x"] = start_x
    game["y"] = start_y
    game["yaw"] = start_direction(game["maze"])
    game["pitch"] = -0.04
    game["previous_cell"] = game["maze"]["start"]
    game["boost_until"] = 0.0
    game["slow_until"] = 0.0


def use_phoenix_sight(game, now, audio_data=None):
    if game["won"]:
        return
    if game["easter_egg"]:
        show_message(game, "Phoenix Override is already active", now, 1.8)
        return
    if game["sight_charges"] > 0:
        game["sight_charges"] -= 1
        game["sight_until"] = now + 7.0
        show_message(game, "Phoenix Sight reveals the route", now)
        if audio_data:
            audio.play(audio_data, "pickup")
    else:
        show_message(game, "No Phoenix Sight charges", now, 1.8)


def handle_feature(game, cell, now, audio_data=None):
    feature = game["maze"]["features"].get(cell)
    if feature is None:
        return

    if feature == "lava":
        game["slow_until"] = now + 3.4
        show_message(game, "Molten snare: movement slowed", now)
        if audio_data:
            audio.play(audio_data, "trap")

    elif feature == "curse":
        teleport_to_start(game)
        show_message(game, "Ash curse: returned to the entrance", now, 3.0)
        if audio_data:
            if game["jumpscare_enabled"] and not game["scare_triggered"]:
                audio.play(audio_data, "scare")
            else:
                audio.play(audio_data, "trap")
        if game["jumpscare_enabled"] and not game["scare_triggered"]:
            game["scare_started"] = now
            game["scare_until"] = now + 1.15
            game["scare_triggered"] = True

    elif feature == "turn" and cell not in game["activated"]:
        game["activated"].add(cell)
        game["yaw"] += math.pi / 2.0
        show_message(game, "Shift rune: view turned 90 degrees", now)
        if audio_data:
            audio.play(audio_data, "turn")

    elif feature == "speed" and cell not in game["collected"]:
        game["collected"].add(cell)
        game["boost_until"] = now + 5.5
        show_message(game, "Cinder crystal: haste gained", now)
        if audio_data:
            audio.play(audio_data, "pickup")

    elif feature == "eye" and cell not in game["collected"]:
        game["collected"].add(cell)
        game["sight_charges"] += 1
        show_message(game, "Forge eye: Phoenix Sight charge gained", now)
        if audio_data:
            audio.play(audio_data, "pickup")

    elif feature == "lift" and cell not in game["collected"]:
        game["collected"].add(cell)
        game["lift_until"] = now + 4.5
        show_message(game, "Skyforge lift: study the vault", now, 3.0)
        if audio_data:
            audio.play(audio_data, "lift")


def check_current_cell(game, now, audio_data=None):
    cell = maze.world_to_cell(game["x"], game["y"], CELL_SIZE)
    if cell == game["previous_cell"]:
        return

    game["previous_cell"] = cell

    if cell == game["maze"]["finish"]:
        game["won"] = True
        game["finish_time"] = now - game["start_time"]
        game["sight_until"] = 0.0
        game["lift_until"] = 0.0
        show_message(game, "The Embervault is complete", now, 4.0)
        if audio_data:
            audio.play(audio_data, "portal")
        return

    handle_feature(game, cell, now, audio_data)


def update_movement(game, keys, delta_time, now):
    game["moving"] = False
    if (game["won"] or now < game["lift_until"]
            or now < game["scare_until"]):
        return

    forward_amount = float(keys[K_w]) - float(keys[K_s])
    side_amount = float(keys[K_d]) - float(keys[K_a])
    if forward_amount == 0.0 and side_amount == 0.0:
        return

    forward_x = math.cos(game["yaw"])
    forward_y = math.sin(game["yaw"])
    right_x = forward_y
    right_y = -forward_x

    move_x = forward_x * forward_amount + right_x * side_amount
    move_y = forward_y * forward_amount + right_y * side_amount
    length = math.sqrt(move_x * move_x + move_y * move_y)
    if length > 0.0:
        move_x /= length
        move_y /= length

    if now < game["slow_until"]:
        speed = SLOW_SPEED
    elif now < game["boost_until"]:
        speed = BOOST_SPEED
    else:
        speed = NORMAL_SPEED

    distance = speed * delta_time
    old_x = game["x"]
    old_y = game["y"]
    game["x"], game["y"] = maze.move_with_collision(
        game["maze"], game["x"], game["y"],
        move_x * distance, move_y * distance,
        PLAYER_RADIUS, CELL_SIZE,
    )
    moved = math.hypot(game["x"] - old_x, game["y"] - old_y)
    game["moving"] = moved > 0.0001


def update_walking_effects(game, delta_time, now, audio_data):
    if game["moving"]:
        if now < game["boost_until"]:
            pace = 12.0
            step_delay = 0.36
        elif now < game["slow_until"]:
            pace = 5.4
            step_delay = 0.74
        else:
            pace = 8.4
            step_delay = 0.52

        game["walk_phase"] += delta_time * pace
        target_bob = math.sin(game["walk_phase"]) * 0.026
        if now - game["last_step_time"] >= step_delay:
            audio.play(audio_data, "step")
            game["last_step_time"] = now
    else:
        target_bob = 0.0

    smooth_amount = min(1.0, delta_time * 12.0)
    game["camera_bob"] += (target_bob - game["camera_bob"]) * smooth_amount


def update_mouse_look(game, relative_x, relative_y):
    game["yaw"] -= relative_x * MOUSE_SENSITIVITY
    game["pitch"] -= relative_y * MOUSE_SENSITIVITY
    game["pitch"] = max(-1.02, min(1.02, game["pitch"]))


def status_text(game, now):
    if now < game["lift_until"]:
        return "ASCENDING"
    if now < game["sight_until"]:
        return "PHOENIX SIGHT"
    if now < game["slow_until"]:
        return "SLOWED"
    if now < game["boost_until"]:
        return "HASTE"
    if game["easter_egg"]:
        return "OVERRIDE"
    return "NORMAL"


def elapsed_time(game, now):
    if game["finish_time"] is not None:
        return game["finish_time"]
    return now - game["start_time"]


def main():
    enable_high_dpi()
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()
    pygame.font.init()
    desktop_size = pygame.display.get_desktop_sizes()[0]
    resolutions = choose_resolutions()
    resolution_index = len(resolutions) - 1
    width, height = resolutions[resolution_index]
    fullscreen = False
    create_window(width, height, fullscreen)
    pygame.display.set_caption(
        "Embervault: The Shifting Forge"
    )

    graphics.initialize_opengl()
    folder = os.path.dirname(os.path.abspath(__file__))
    textures = graphics.load_textures(folder)
    audio_data = audio.initialize(folder)

    pygame.event.set_grab(True)
    pygame.mouse.set_visible(False)
    pygame.mouse.get_rel()

    clock = pygame.time.Clock()
    game = make_game(current_time())
    running = True

    print(f"Embervault running at {width} x {height} with 1024 px textures")
    print("WASD move | Mouse look | Q sight | H help")
    print("R reset | N new maze | M audio | J scare | F10 size")
    print("F11 fullscreen | ESC quit")

    while running:
        delta_time = min(clock.tick(60) / 1000.0, 0.05)
        now = current_time()

        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    running = False
                elif event.key == K_F10:
                    fullscreen = False
                    resolution_index = (resolution_index + 1) % len(resolutions)
                    width, height = resolutions[resolution_index]
                    textures = recreate_display(
                        width, height, fullscreen, folder, textures
                    )
                    if not game["show_help"]:
                        show_message(
                            game, f"Window size: {width} x {height}", now
                        )
                elif event.key == K_F11:
                    fullscreen = not fullscreen
                    if fullscreen:
                        width, height = desktop_size
                    else:
                        width, height = resolutions[resolution_index]
                    textures = recreate_display(
                        width, height, fullscreen, folder, textures
                    )
                    width, height = pygame.display.get_surface().get_size()
                    if not game["show_help"]:
                        mode = "Fullscreen" if fullscreen else "Windowed"
                        show_message(
                            game, f"{mode}: {width} x {height}", now
                        )
                elif game["show_help"]:
                    if event.key in (K_RETURN, K_SPACE, K_h):
                        set_help_visible(game, False, now)
                    elif event.key == K_j:
                        toggle_jumpscare(game, now)
                elif event.key == K_j:
                    toggle_jumpscare(game, now)
                elif check_easter_egg(game, event.key, now, audio_data):
                    pass
                elif event.key == K_h:
                    set_help_visible(game, True, now)
                elif event.key == K_r:
                    reset_same_maze(game, now, audio_data)
                elif event.key == K_n:
                    generate_new_maze(game, now, audio_data)
                elif event.key == K_q:
                    use_phoenix_sight(game, now, audio_data)
                elif event.key == K_m:
                    enabled = audio.toggle(audio_data)
                    show_message(game, "Audio on" if enabled else "Audio muted", now)
            elif event.type == MOUSEMOTION:
                if (not game["show_help"] and not game["won"]
                        and now >= game["lift_until"]
                        and now >= game["scare_until"]):
                    update_mouse_look(game, event.rel[0], event.rel[1])

        if not game["show_help"]:
            update_movement(game, pygame.key.get_pressed(), delta_time, now)
            update_walking_effects(game, delta_time, now, audio_data)
            check_current_cell(game, now, audio_data)
        else:
            game["moving"] = False

        display_now = game["help_started"] if game["show_help"] else now
        overhead = display_now < game["lift_until"]
        show_map = (game["easter_egg"]
                    or display_now < game["sight_until"])
        elapsed = elapsed_time(game, display_now)
        remaining_message = game["message_until"] - display_now
        message_alpha = max(0.0, min(1.0, remaining_message / 0.55))

        graphics.draw_world(
            game["maze"], textures,
            game["x"], game["y"], game["yaw"], game["pitch"],
            CELL_SIZE, WALL_HEIGHT, display_now, game["collected"], overhead,
            width, height, game["camera_bob"],
        )
        sight_display = "MAX" if game["easter_egg"] else game["sight_charges"]
        graphics.draw_hud(
            game["maze"], game["x"], game["y"], game["yaw"], elapsed,
            sight_display, status_text(game, display_now),
            game["message"], message_alpha,
            show_map, overhead, game["won"], width, height, CELL_SIZE,
            display_now,
        )
        scare_remaining = game["scare_until"] - display_now
        if scare_remaining > 0.0 and not game["show_help"]:
            graphics.draw_jumpscare(
                width, height, display_now - game["scare_started"],
                scare_remaining,
            )
        if game["show_help"]:
            graphics.draw_help_overlay(
                width, height, game["jumpscare_enabled"]
            )
        pygame.display.flip()

    audio.shutdown(audio_data)
    graphics.delete_textures(textures)
    pygame.event.set_grab(False)
    pygame.mouse.set_visible(True)
    pygame.quit()


if __name__ == "__main__":
    main()
