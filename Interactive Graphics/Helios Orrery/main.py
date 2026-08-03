import math
import os
import random
from collections import deque

import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *

from simulation import BODIES, OrrerySimulation, orbital_position


START_SIZE = (1280, 720)
BODY_LOOKUP = {body.name: body for body in BODIES}
FOCUS_ORDER = ("Sun", "Mercury", "Venus", "Earth", "Mars")


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def requested_size():
    raw = os.environ.get("PORTFOLIO_SIZE", "")
    try:
        width, height = (int(value) for value in raw.lower().split("x", 1))
        return (max(640, width), max(480, height))
    except (ValueError, TypeError):
        return START_SIZE


def lerp(first, second, amount):
    return first + (second - first) * amount


class OrreryApp:
    def __init__(self):
        pygame.init()
        pygame.font.init()
        pygame.display.set_caption("Helios Orrery")
        self.simulation = OrrerySimulation()
        self.focus_index = 0
        self.target = [0.0, 0.0, 0.0]
        self.yaw = 35.0
        self.pitch = 50.0
        self.distance = 24.0
        self.diagram_scale = True
        self.show_orbits = True
        self.show_trails = True
        self.show_hud = True
        self.dragging = False
        self.running = True
        self.fullscreen = os.environ.get("PORTFOLIO_FULLSCREEN") == "1"
        self.windowed_size = requested_size()
        self.clock = pygame.time.Clock()
        self.trails = {name: deque(maxlen=220) for name in FOCUS_ORDER[1:]}
        self.starfield = self.create_starfield()
        self.quadric = None
        self.title_font = pygame.font.SysFont("cambria", 27, bold=True)
        self.body_font = pygame.font.SysFont("segoeui", 18)
        self.data_font = pygame.font.SysFont("consolas", 16)
        self.pending_capture = False
        self.capture_path = os.environ.get("ORRERY_CAPTURE")
        self.capture_frame = int(os.environ.get("ORRERY_CAPTURE_FRAME", "80"))
        self.frames = 0
        self.create_display()

    def create_starfield(self):
        rng = random.Random(4370)
        stars = []
        for _ in range(420):
            angle = rng.uniform(0, math.tau)
            z = rng.uniform(-0.92, 0.92)
            radius = 36.0
            horizontal = math.sqrt(1 - z * z)
            stars.append((radius * horizontal * math.cos(angle),
                          radius * horizontal * math.sin(angle), radius * z,
                          rng.uniform(0.35, 0.95)))
        return stars

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
        glClearColor(0.006, 0.009, 0.018, 1.0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_NORMALIZE)
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        glShadeModel(GL_SMOOTH)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_POINT_SMOOTH)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glLightfv(GL_LIGHT0, GL_AMBIENT, (0.025, 0.03, 0.05, 1.0))
        glLightfv(GL_LIGHT0, GL_DIFFUSE, (1.0, 0.88, 0.64, 1.0))
        glLightfv(GL_LIGHT0, GL_SPECULAR, (1.0, 0.92, 0.76, 1.0))
        glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, (0.45, 0.45, 0.45, 1.0))
        glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 34.0)
        self.quadric = gluNewQuadric()
        gluQuadricNormals(self.quadric, GLU_SMOOTH)

    def resize(self, width, height):
        self.width, self.height = max(1, width), max(1, height)
        glViewport(0, 0, self.width, self.height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(48.0, self.width / self.height, 0.12, 90.0)
        glMatrixMode(GL_MODELVIEW)

    def toggle_fullscreen(self):
        if not self.fullscreen:
            self.windowed_size = pygame.display.get_window_size()
        self.fullscreen = not self.fullscreen
        self.create_display()

    def handle_key(self, key):
        if key == K_ESCAPE:
            self.running = False
        elif K_1 <= key <= K_5:
            self.focus_index = key - K_1
            self.distance = 24.0 if self.focus_index == 0 else 7.0
        elif key == K_SPACE:
            self.simulation.paused = not self.simulation.paused
        elif key in (K_PLUS, K_EQUALS, K_KP_PLUS):
            self.simulation.days_per_second = clamp(self.simulation.days_per_second * 1.35, 1.0, 1200.0)
        elif key in (K_MINUS, K_KP_MINUS):
            self.simulation.days_per_second = clamp(self.simulation.days_per_second / 1.35, 1.0, 1200.0)
        elif key == K_m:
            self.diagram_scale = not self.diagram_scale
        elif key == K_o:
            self.show_orbits = not self.show_orbits
        elif key == K_t:
            self.show_trails = not self.show_trails
        elif key == K_TAB:
            self.show_hud = not self.show_hud
        elif key == K_p:
            self.pending_capture = True
        elif key == K_F11:
            self.toggle_fullscreen()
        elif key == K_0:
            self.yaw, self.pitch = 35.0, 50.0
            self.distance = 24.0 if self.focus_index == 0 else 7.0

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
                self.yaw += event.rel[0] * 0.30
                self.pitch = clamp(self.pitch + event.rel[1] * 0.28, -82, 82)
            elif event.type == MOUSEWHEEL:
                minimum = 3.3 if self.focus_index else 12.0
                maximum = 16.0 if self.focus_index else 42.0
                self.distance = clamp(self.distance - event.y * 0.8, minimum, maximum)

    def radius_for(self, body):
        if self.diagram_scale:
            return 0.25 + body.relative_radius * 0.32
        return max(0.10, body.relative_radius * 0.42)

    def draw_stars(self):
        glDisable(GL_LIGHTING)
        glDepthMask(GL_FALSE)
        glPointSize(1.7)
        glBegin(GL_POINTS)
        for x, y, z, brightness in self.starfield:
            glColor4f(0.72, 0.80, 0.92, brightness)
            glVertex3f(x, y, z)
        glEnd()
        glDepthMask(GL_TRUE)
        glEnable(GL_LIGHTING)

    def draw_orbit(self, body):
        glDisable(GL_LIGHTING)
        glColor4f(0.38, 0.46, 0.56, 0.34)
        glLineWidth(1.0)
        glBegin(GL_LINE_LOOP)
        for index in range(180):
            point = orbital_position(body, body.period_days * index / 180.0)
            glVertex3fv(point)
        glEnd()
        glEnable(GL_LIGHTING)

    def draw_trail(self, name, color):
        points = self.trails[name]
        if len(points) < 2:
            return
        glDisable(GL_LIGHTING)
        glBegin(GL_LINE_STRIP)
        total = len(points)
        for index, point in enumerate(points):
            glColor4f(*color, 0.03 + 0.32 * index / total)
            glVertex3fv(point)
        glEnd()
        glEnable(GL_LIGHTING)

    def draw_sphere(self, position, radius, color, slices=28, stacks=18):
        glPushMatrix()
        glTranslatef(*position)
        glColor3f(*color)
        gluSphere(self.quadric, radius, slices, stacks)
        glPopMatrix()

    def draw_sun(self):
        glDisable(GL_LIGHTING)
        glColor3f(1.0, 0.66, 0.16)
        gluSphere(self.quadric, 1.25, 36, 22)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE)
        glDepthMask(GL_FALSE)
        for radius, alpha in ((1.37, 0.13), (1.52, 0.06)):
            glColor4f(1.0, 0.52, 0.08, alpha)
            gluSphere(self.quadric, radius, 30, 18)
        glDepthMask(GL_TRUE)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_LIGHTING)

    def draw_text(self, x, y, text, font, color):
        surface = font.render(text, True, color)
        data = pygame.image.tostring(surface, "RGBA", True)
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_LIGHTING)
        glWindowPos2d(x, self.height - y - surface.get_height())
        glDrawPixels(surface.get_width(), surface.get_height(), GL_RGBA, GL_UNSIGNED_BYTE, data)
        glEnable(GL_LIGHTING)
        glEnable(GL_DEPTH_TEST)

    def draw_hud(self, positions, fps):
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_LIGHTING)
        glMatrixMode(GL_PROJECTION)
        glPushMatrix(); glLoadIdentity(); glOrtho(0, self.width, self.height, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix(); glLoadIdentity()
        glColor4f(0.012, 0.018, 0.032, 0.90)
        glBegin(GL_QUADS)
        glVertex2f(22, 22); glVertex2f(365, 22); glVertex2f(365, 230); glVertex2f(22, 230)
        glEnd()
        glColor4f(0.68, 0.52, 0.25, 0.72)
        glBegin(GL_LINE_LOOP)
        glVertex2f(22, 22); glVertex2f(365, 22); glVertex2f(365, 230); glVertex2f(22, 230)
        glEnd()
        glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix(); glMatrixMode(GL_MODELVIEW)
        glEnable(GL_DEPTH_TEST); glEnable(GL_LIGHTING)

        name = FOCUS_ORDER[self.focus_index]
        self.draw_text(42, 36, "HELIOS ORRERY", self.title_font, (245, 236, 214))
        self.draw_text(42, 75, f"FOCUS  {name}", self.body_font, (242, 174, 70))
        self.draw_text(42, 108, f"SIMULATION DAY  {self.simulation.elapsed_days:9.1f}", self.data_font, (184, 198, 218))
        self.draw_text(42, 136, f"RATE  {self.simulation.days_per_second:7.1f} DAYS / SEC", self.data_font, (184, 198, 218))
        self.draw_text(42, 164, f"SCALE  {'DIAGRAM' if self.diagram_scale else 'RELATIVE'}", self.data_font, (184, 198, 218))
        status = "PAUSED" if self.simulation.paused else f"LIVE  {fps:3.0f} FPS"
        self.draw_text(42, 192, status, self.data_font, (122, 190, 222))
        controls = "1-5 FOCUS  DRAG ORBIT  WHEEL ZOOM  +/- TIME  M SCALE  O ORBITS  T TRAILS"
        width = self.data_font.size(controls)[0]
        self.draw_text(max(18, (self.width - width) // 2), self.height - 34, controls,
                       self.data_font, (163, 180, 205))

    def capture(self, path=None):
        folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")
        os.makedirs(folder, exist_ok=True)
        path = path or os.path.join(folder, "helios-orrery.png")
        pixels = glReadPixels(0, 0, self.width, self.height, GL_RGB, GL_UNSIGNED_BYTE)
        surface = pygame.image.fromstring(pixels, (self.width, self.height), "RGB", True)
        pygame.image.save(surface, path)

    def update_target(self, positions, delta):
        focus = positions[FOCUS_ORDER[self.focus_index]]
        amount = 1.0 - math.exp(-5.0 * delta)
        for axis in range(3):
            self.target[axis] = lerp(self.target[axis], focus[axis], amount)

    def draw(self, positions, fps):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        horizontal = self.distance * math.cos(math.radians(self.pitch))
        eye = (
            self.target[0] + horizontal * math.sin(math.radians(self.yaw)),
            self.target[1] - horizontal * math.cos(math.radians(self.yaw)),
            self.target[2] + self.distance * math.sin(math.radians(self.pitch)),
        )
        gluLookAt(*eye, *self.target, 0, 0, 1)
        glLightfv(GL_LIGHT0, GL_POSITION, (0.0, 0.0, 0.0, 1.0))
        self.draw_stars()
        if self.show_orbits:
            for body in BODIES:
                self.draw_orbit(body)
        if self.show_trails:
            for body in BODIES:
                self.draw_trail(body.name, body.color)
        self.draw_sun()
        for body in BODIES:
            self.draw_sphere(positions[body.name], self.radius_for(body), body.color)
        self.draw_sphere(positions["Moon"], 0.12 if self.diagram_scale else 0.09,
                         (0.72, 0.74, 0.76), 18, 12)
        if self.show_hud:
            self.draw_hud(positions, fps)
        pygame.display.flip()

    def run(self):
        while self.running:
            delta = min(self.clock.tick(60) / 1000.0, 0.05)
            self.events()
            self.simulation.update(delta)
            positions = self.simulation.positions()
            for body in BODIES:
                self.trails[body.name].append(positions[body.name])
            self.update_target(positions, delta)
            self.draw(positions, self.clock.get_fps())
            self.frames += 1
            if self.pending_capture or (self.capture_path and self.frames == self.capture_frame):
                self.capture(self.capture_path)
                self.pending_capture = False
                if self.capture_path:
                    self.running = False
        pygame.quit()


if __name__ == "__main__":
    OrreryApp().run()
