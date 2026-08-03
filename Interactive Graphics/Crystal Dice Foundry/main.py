import math
import os
import random

import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *

from geometry import create_solids
from physics import DiceSimulation, quaternion_matrix


START_SIZE = (1280, 720)
ATLAS_COLUMNS = 8
ATLAS_ROWS = 4
NUMBER_MAPS = (
    (1, 4, 2, 3),
    (1, 2, 6, 5, 3, 4),
    (1, 2, 3, 4, 5, 6, 7, 8),
    (1, 2, 3, 4, 5, 9, 6, 12, 8, 7, 11, 10),
    (1, 2, 3, 4, 5, 19, 20, 6, 7, 8, 15, 13, 14, 18, 16, 17, 9, 10, 11, 12),
)
DIE_NAMES = ("D4", "D6", "D8", "D12", "D20")
DIE_COLORS = (
    (0.72, 0.28, 0.24), (0.80, 0.58, 0.22), (0.22, 0.56, 0.46),
    (0.26, 0.46, 0.72), (0.56, 0.36, 0.72),
)


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def requested_size():
    raw = os.environ.get("PORTFOLIO_SIZE", "")
    try:
        width, height = (int(value) for value in raw.lower().split("x", 1))
        return (max(640, width), max(480, height))
    except (ValueError, TypeError):
        return START_SIZE


def texture_coordinates(number, vertex_count):
    column = (number - 1) % ATLAS_COLUMNS
    row = (number - 1) // ATLAS_COLUMNS
    u_min, u_max = column / ATLAS_COLUMNS, (column + 1) / ATLAS_COLUMNS
    v_max, v_min = 1.0 - row / ATLAS_ROWS, 1.0 - (row + 1) / ATLAS_ROWS
    if vertex_count == 4:
        local = ((0.06, 0.06), (0.94, 0.06), (0.94, 0.94), (0.06, 0.94))
    else:
        local = []
        for index in range(vertex_count):
            angle = math.pi / 2 + index * math.tau / vertex_count
            local.append((0.5 + 0.45 * math.cos(angle),
                          0.5 + 0.45 * math.sin(angle)))
    return tuple((u_min + u * (u_max - u_min), v_min + v * (v_max - v_min))
                 for u, v in local)


class DiceApp:
    def __init__(self):
        pygame.init()
        pygame.font.init()
        pygame.display.set_caption("Crystal Dice Foundry")
        self.folder = os.path.dirname(os.path.abspath(__file__))
        self.solids = create_solids()
        self.selected = int(clamp(int(os.environ.get("DICE_SELECTED", "1")), 0, 4))
        self.simulation = DiceSimulation(self.solids[self.selected], NUMBER_MAPS[self.selected])
        self.history = []
        self.recorded_result = self.simulation.result
        self.yaw = 32.0
        self.pitch = 26.0
        self.distance = 6.7
        self.dragging = False
        self.show_hud = True
        self.running = True
        self.fullscreen = os.environ.get("PORTFOLIO_FULLSCREEN") == "1"
        self.windowed_size = requested_size()
        self.clock = pygame.time.Clock()
        self.texture = None
        self.quadric = None
        self.rng = random.Random()
        self.title_font = pygame.font.SysFont("cambria", 27, bold=True)
        self.body_font = pygame.font.SysFont("segoeui", 18)
        self.data_font = pygame.font.SysFont("consolas", 16)
        self.pending_capture = False
        self.capture_path = os.environ.get("DICE_CAPTURE")
        self.capture_frame = int(os.environ.get("DICE_CAPTURE_FRAME", "120"))
        self.frames = 0
        self.auto_roll = os.environ.get("DICE_AUTO_ROLL") == "1"
        self.create_display()
        if self.auto_roll:
            self.start_roll(seed=4370)

    def create_display(self):
        flags = DOUBLEBUF | OPENGL
        size = self.windowed_size
        if self.fullscreen:
            flags |= FULLSCREEN
            size = pygame.display.get_desktop_sizes()[0]
        else:
            flags |= RESIZABLE
        try:
            pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 1)
            pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, 4)
            pygame.display.set_mode(size, flags, vsync=1)
        except pygame.error:
            pygame.display.set_mode(size, flags)
        self.width, self.height = pygame.display.get_window_size()
        self.resize(self.width, self.height)
        glClearColor(0.025, 0.022, 0.028, 1.0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_NORMALIZE)
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_LIGHT1)
        glLightfv(GL_LIGHT0, GL_AMBIENT, (0.10, 0.09, 0.12, 1.0))
        glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.92, 0.88, 0.78, 1.0))
        glLightfv(GL_LIGHT0, GL_SPECULAR, (1.0, 0.94, 0.82, 1.0))
        glLightfv(GL_LIGHT1, GL_DIFFUSE, (0.25, 0.42, 0.80, 1.0))
        glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, (0.82, 0.84, 0.90, 1.0))
        glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 68.0)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        self.texture = self.load_texture(os.path.join(self.folder, "assets", "dice_numbers_crystal.png"))
        self.quadric = gluNewQuadric()

    def resize(self, width, height):
        self.width, self.height = max(1, width), max(1, height)
        glViewport(0, 0, self.width, self.height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(43.0, self.width / self.height, 0.1, 30.0)
        glMatrixMode(GL_MODELVIEW)

    def load_texture(self, path):
        surface = pygame.image.load(path).convert_alpha()
        data = pygame.image.tostring(surface, "RGBA", True)
        texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texture)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, surface.get_width(), surface.get_height(),
                     0, GL_RGBA, GL_UNSIGNED_BYTE, data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        return texture

    def toggle_fullscreen(self):
        if not self.fullscreen:
            self.windowed_size = pygame.display.get_window_size()
        self.fullscreen = not self.fullscreen
        self.create_display()

    def select_die(self, index):
        self.selected = index
        self.simulation.set_die(self.solids[index], NUMBER_MAPS[index])
        self.recorded_result = self.simulation.result

    def start_roll(self, seed=None):
        strength = 0.9 + self.rng.random() * 0.35
        self.simulation.roll(seed=seed, strength=strength)
        self.recorded_result = None

    def handle_key(self, key):
        if key == K_ESCAPE:
            self.running = False
        elif K_1 <= key <= K_5 and not self.simulation.rolling:
            self.select_die(key - K_1)
        elif key in (K_SPACE, K_RETURN) and not self.simulation.rolling:
            self.start_roll()
        elif key == K_TAB:
            self.show_hud = not self.show_hud
        elif key == K_p:
            self.pending_capture = True
        elif key == K_F11:
            self.toggle_fullscreen()
        elif key == K_0:
            self.yaw, self.pitch, self.distance = 32.0, 26.0, 6.7

    def events(self):
        for event in pygame.event.get():
            if event.type == QUIT:
                self.running = False
            elif event.type == KEYDOWN:
                self.handle_key(event.key)
            elif event.type == VIDEORESIZE and not self.fullscreen:
                self.windowed_size = event.size
                self.resize(*event.size)
            elif event.type == MOUSEBUTTONDOWN and event.button == 1:
                self.dragging = True
            elif event.type == MOUSEBUTTONUP and event.button == 1:
                self.dragging = False
            elif event.type == MOUSEMOTION and self.dragging:
                self.yaw += event.rel[0] * 0.32
                self.pitch = clamp(self.pitch + event.rel[1] * 0.26, 5, 72)
            elif event.type == MOUSEWHEEL:
                self.distance = clamp(self.distance - event.y * 0.35, 4.4, 10.0)

    def draw_face(self, solid, face, normal, number):
        coordinates = texture_coordinates(number, len(face))
        glNormal3fv(normal)
        if len(face) in (3, 4):
            glBegin(GL_TRIANGLES if len(face) == 3 else GL_QUADS)
            for index, coordinate in zip(face, coordinates):
                glTexCoord2fv(coordinate)
                glVertex3fv(solid.vertices[index])
            glEnd()
        else:
            center = tuple(sum(solid.vertices[index][axis] for index in face) / len(face)
                           for axis in range(3))
            center_uv = tuple(sum(uv[axis] for uv in coordinates) / len(coordinates)
                              for axis in range(2))
            glBegin(GL_TRIANGLES)
            for index in range(len(face)):
                next_index = (index + 1) % len(face)
                glTexCoord2fv(center_uv); glVertex3fv(center)
                glTexCoord2fv(coordinates[index]); glVertex3fv(solid.vertices[face[index]])
                glTexCoord2fv(coordinates[next_index]); glVertex3fv(solid.vertices[face[next_index]])
            glEnd()

    def draw_die(self):
        solid = self.solids[self.selected]
        glPushMatrix()
        glTranslatef(0.0, 0.0, self.simulation.height * 1.35)
        glMultMatrixf(quaternion_matrix(self.simulation.orientation))
        glScalef(1.35, 1.35, 1.35)
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.texture)
        glTexEnvi(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_MODULATE)
        glColor3fv(DIE_COLORS[self.selected])
        for face, normal, number in zip(solid.faces, solid.normals, NUMBER_MAPS[self.selected]):
            self.draw_face(solid, face, normal, number)
        glDisable(GL_TEXTURE_2D)
        glColor4f(0.92, 0.94, 1.0, 0.60)
        glLineWidth(1.4)
        glBegin(GL_LINES)
        for first, second in solid.edges:
            glVertex3fv(solid.vertices[first]); glVertex3fv(solid.vertices[second])
        glEnd()
        glPopMatrix()

    def draw_tray(self):
        glDisable(GL_TEXTURE_2D)
        glNormal3f(0, 0, 1)
        glColor3f(0.13, 0.115, 0.14)
        glBegin(GL_QUADS)
        glVertex3f(-4.8, -4.8, 0); glVertex3f(4.8, -4.8, 0)
        glVertex3f(4.8, 4.8, 0); glVertex3f(-4.8, 4.8, 0)
        glEnd()
        glDisable(GL_LIGHTING)
        glColor4f(0.48, 0.42, 0.50, 0.38)
        for size in (3.6, 4.35):
            glBegin(GL_LINE_LOOP)
            for index in range(4):
                x = size if index in (0, 1) else -size
                y = size if index in (1, 2) else -size
                glVertex3f(x, y, 0.012)
            glEnd()
        glEnable(GL_LIGHTING)

    def draw_text(self, x, y, text, font, color):
        surface = font.render(text, True, color)
        data = pygame.image.tostring(surface, "RGBA", True)
        glDisable(GL_DEPTH_TEST); glDisable(GL_LIGHTING)
        glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glWindowPos2d(x, self.height - y - surface.get_height())
        glDrawPixels(surface.get_width(), surface.get_height(), GL_RGBA, GL_UNSIGNED_BYTE, data)
        glDisable(GL_BLEND); glEnable(GL_LIGHTING); glEnable(GL_DEPTH_TEST)

    def draw_hud(self, fps):
        glDisable(GL_DEPTH_TEST); glDisable(GL_LIGHTING)
        glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
        glOrtho(0, self.width, self.height, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
        glColor4f(0.045, 0.038, 0.050, 0.94)
        glBegin(GL_QUADS)
        glVertex2f(22, 22); glVertex2f(382, 22); glVertex2f(382, 244); glVertex2f(22, 244)
        glEnd()
        glColor4f(0.58, 0.50, 0.62, 0.72)
        glBegin(GL_LINE_LOOP)
        glVertex2f(22, 22); glVertex2f(382, 22); glVertex2f(382, 244); glVertex2f(22, 244)
        glEnd()
        glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix(); glMatrixMode(GL_MODELVIEW)
        glEnable(GL_LIGHTING); glEnable(GL_DEPTH_TEST)
        self.draw_text(42, 36, "CRYSTAL DICE FOUNDRY", self.title_font, (244, 240, 232))
        self.draw_text(42, 76, f"SELECTED  {DIE_NAMES[self.selected]}", self.body_font, (185, 153, 208))
        status = "ROLLING" if self.simulation.rolling else "SETTLED"
        self.draw_text(42, 111, f"STATE     {status}", self.data_font, (198, 194, 204))
        result = "--" if self.simulation.result is None else str(self.simulation.result)
        self.draw_text(42, 139, f"UPWARD FACE  {result:>2}", self.data_font, (225, 190, 92))
        history = "  ".join(str(value) for value in self.history[-7:]) or "NO ROLLS YET"
        self.draw_text(42, 167, f"HISTORY  {history}", self.data_font, (198, 194, 204))
        self.draw_text(42, 195, f"IMPACTS  {self.simulation.impacts:2d}     {fps:3.0f} FPS", self.data_font, (143, 203, 188))
        controls = "1-5 DIE  SPACE THROW  DRAG ORBIT  WHEEL ZOOM  TAB HUD  P CAPTURE"
        width = self.data_font.size(controls)[0]
        self.draw_text(max(18, (self.width - width) // 2), self.height - 34,
                       controls, self.data_font, (186, 178, 190))

    def capture(self, path=None):
        folder = os.path.join(self.folder, "screenshots")
        os.makedirs(folder, exist_ok=True)
        path = path or os.path.join(folder, "crystal-dice-foundry.png")
        pixels = glReadPixels(0, 0, self.width, self.height, GL_RGB, GL_UNSIGNED_BYTE)
        surface = pygame.image.fromstring(pixels, (self.width, self.height), "RGB", True)
        pygame.image.save(surface, path)

    def draw(self, fps):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        horizontal = self.distance * math.cos(math.radians(self.pitch))
        eye = (horizontal * math.sin(math.radians(self.yaw)),
               -horizontal * math.cos(math.radians(self.yaw)),
               1.3 + self.distance * math.sin(math.radians(self.pitch)))
        gluLookAt(*eye, 0, 0, 1.0, 0, 0, 1)
        glLightfv(GL_LIGHT0, GL_POSITION, (-4.0, -3.0, 7.0, 1.0))
        glLightfv(GL_LIGHT1, GL_POSITION, (3.0, 2.0, 4.0, 1.0))
        self.draw_tray()
        self.draw_die()
        if self.show_hud:
            self.draw_hud(fps)
        pygame.display.flip()

    def run(self):
        while self.running:
            delta = min(self.clock.tick(60) / 1000.0, 0.04)
            self.events()
            was_rolling = self.simulation.rolling
            self.simulation.update(delta)
            if was_rolling and not self.simulation.rolling and self.simulation.result is not None:
                self.history.append(self.simulation.result)
                self.recorded_result = self.simulation.result
            self.draw(self.clock.get_fps())
            self.frames += 1
            if self.pending_capture or (self.capture_path and self.frames == self.capture_frame):
                self.capture(self.capture_path)
                self.pending_capture = False
                if self.capture_path:
                    self.running = False
        pygame.quit()


if __name__ == "__main__":
    DiceApp().run()
