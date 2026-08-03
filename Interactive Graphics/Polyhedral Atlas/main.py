import math
import os

import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *

from geometry import create_solids


START_SIZE = (1280, 720)
PAPER = (0.90, 0.88, 0.82)
INK = (0.10, 0.12, 0.14)
COBALT = (0.08, 0.28, 0.58)
VERMILION = (0.78, 0.20, 0.12)


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def requested_size():
    raw = os.environ.get("PORTFOLIO_SIZE", "")
    try:
        width, height = (int(value) for value in raw.lower().split("x", 1))
        return (max(640, width), max(480, height))
    except (ValueError, TypeError):
        return START_SIZE


class AtlasApp:
    def __init__(self):
        pygame.init()
        pygame.font.init()
        pygame.display.set_caption("Polyhedral Atlas")
        self.solids = create_solids()
        self.selected = 0
        self.yaw = 28.0
        self.pitch = 18.0
        self.distance = 5.2
        self.auto_rotate = True
        self.show_faces = True
        self.show_edges = True
        self.show_vertices = True
        self.show_sphere = True
        self.show_dual = True
        self.show_hud = True
        self.dragging = False
        self.running = True
        self.fullscreen = os.environ.get("PORTFOLIO_FULLSCREEN") == "1"
        self.windowed_size = requested_size()
        self.clock = pygame.time.Clock()
        self.angle = 0.0
        self.pending_capture = False
        self.capture_path = os.environ.get("ATLAS_CAPTURE")
        self.capture_frame = int(os.environ.get("ATLAS_CAPTURE_FRAME", "70"))
        self.frames = 0
        self.title_font = pygame.font.SysFont("georgia", 27, bold=True)
        self.body_font = pygame.font.SysFont("segoeui", 18)
        self.data_font = pygame.font.SysFont("consolas", 17)
        self.create_display()

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
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_LINE_SMOOTH)
        glClearColor(*PAPER, 1.0)

    def resize(self, width, height):
        self.width = max(1, width)
        self.height = max(1, height)
        glViewport(0, 0, self.width, self.height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(38.0, self.width / self.height, 0.1, 40.0)
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
            self.selected = key - K_1
        elif key == K_f:
            self.show_faces = not self.show_faces
        elif key == K_e:
            self.show_edges = not self.show_edges
        elif key == K_v:
            self.show_vertices = not self.show_vertices
        elif key == K_b:
            self.show_sphere = not self.show_sphere
        elif key == K_d:
            self.show_dual = not self.show_dual
        elif key == K_SPACE:
            self.auto_rotate = not self.auto_rotate
        elif key == K_TAB:
            self.show_hud = not self.show_hud
        elif key == K_p:
            self.pending_capture = True
        elif key == K_F11:
            self.toggle_fullscreen()
        elif key == K_0:
            self.yaw, self.pitch, self.distance = 28.0, 18.0, 5.2

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
                self.yaw += event.rel[0] * 0.35
                self.pitch = clamp(self.pitch + event.rel[1] * 0.30, -80, 80)
            elif event.type == MOUSEWHEEL:
                self.distance = clamp(self.distance - event.y * 0.35, 2.8, 9.0)

    def draw_face(self, vertices, face, color):
        glColor4f(*color, 0.25)
        glBegin(GL_TRIANGLE_FAN)
        for index in face:
            glVertex3fv(vertices[index])
        glEnd()

    def draw_solid(self, solid):
        if self.show_faces:
            glDepthMask(GL_FALSE)
            for face in solid.faces:
                self.draw_face(solid.vertices, face, solid.color)
            glDepthMask(GL_TRUE)
        if self.show_edges:
            glColor4f(*INK, 0.96)
            glLineWidth(2.0)
            glBegin(GL_LINES)
            for first, second in solid.edges:
                glVertex3fv(solid.vertices[first])
                glVertex3fv(solid.vertices[second])
            glEnd()
        if self.show_vertices:
            glPointSize(8.0)
            glColor4f(*VERMILION, 1.0)
            glBegin(GL_POINTS)
            for vertex in solid.vertices:
                glVertex3fv(vertex)
            glEnd()

    def draw_dual(self, solid):
        vertices, edges = solid.dual()
        display_vertices = tuple(
            tuple(component * 0.68 for component in vertex)
            for vertex in vertices
        )
        glColor4f(*COBALT, 0.88)
        glLineWidth(1.7)
        glBegin(GL_LINES)
        for first, second in edges:
            glVertex3fv(display_vertices[first])
            glVertex3fv(display_vertices[second])
        glEnd()
        glPointSize(5.0)
        glBegin(GL_POINTS)
        for vertex in display_vertices:
            glVertex3fv(vertex)
        glEnd()

    def draw_sphere(self):
        glColor4f(*COBALT, 0.22)
        glLineWidth(1.0)
        for latitude in (-60, -30, 0, 30, 60):
            radius = math.cos(math.radians(latitude))
            z = math.sin(math.radians(latitude))
            glBegin(GL_LINE_LOOP)
            for index in range(96):
                angle = math.tau * index / 96
                glVertex3f(math.cos(angle) * radius, math.sin(angle) * radius, z)
            glEnd()
        for longitude in range(0, 180, 30):
            glBegin(GL_LINE_LOOP)
            angle = math.radians(longitude)
            for index in range(96):
                phase = math.tau * index / 96
                glVertex3f(math.cos(phase) * math.cos(angle),
                           math.cos(phase) * math.sin(angle), math.sin(phase))
            glEnd()

    def draw_text(self, x, y, text, font, color):
        surface = font.render(text, True, color)
        data = pygame.image.tostring(surface, "RGBA", True)
        glDisable(GL_DEPTH_TEST)
        glWindowPos2d(x, self.height - y - surface.get_height())
        glDrawPixels(surface.get_width(), surface.get_height(), GL_RGBA,
                     GL_UNSIGNED_BYTE, data)
        glEnable(GL_DEPTH_TEST)

    def draw_panel(self):
        panel_width = min(360, self.width - 36)
        glDisable(GL_DEPTH_TEST)
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, self.width, self.height, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glColor4f(0.96, 0.95, 0.91, 0.94)
        glBegin(GL_QUADS)
        glVertex2f(20, 20)
        glVertex2f(20 + panel_width, 20)
        glVertex2f(20 + panel_width, 236)
        glVertex2f(20, 236)
        glEnd()
        glColor4f(*INK, 0.38)
        glBegin(GL_LINE_LOOP)
        glVertex2f(20, 20)
        glVertex2f(20 + panel_width, 20)
        glVertex2f(20 + panel_width, 236)
        glVertex2f(20, 236)
        glEnd()
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glEnable(GL_DEPTH_TEST)

        solid = self.solids[self.selected]
        dual_names = ("Tetrahedron", "Octahedron", "Cube", "Icosahedron", "Dodecahedron")
        self.draw_text(42, 36, "POLYHEDRAL ATLAS", self.title_font, (25, 29, 33))
        self.draw_text(42, 76, solid.name, self.body_font, (25, 71, 139))
        self.draw_text(42, 111, f"VERTICES  {len(solid.vertices):>2}    EDGES  {len(solid.edges):>2}", self.data_font, (35, 39, 42))
        self.draw_text(42, 139, f"FACES     {len(solid.faces):>2}    EULER  {solid.euler:>2}", self.data_font, (35, 39, 42))
        self.draw_text(42, 167, f"EDGE LENGTH  {solid.edge_length:.4f}", self.data_font, (35, 39, 42))
        self.draw_text(42, 195, f"DUAL  {dual_names[self.selected]}", self.data_font, (143, 42, 27))
        controls = "1-5 SOLID  DRAG ORBIT  WHEEL ZOOM  D DUAL  B SPHERE  F/E/V LAYERS  TAB HUD"
        text_width = self.data_font.size(controls)[0]
        self.draw_text(max(18, (self.width - text_width) // 2), self.height - 34,
                       controls, self.data_font, (35, 39, 42))

    def capture(self, path=None):
        folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")
        os.makedirs(folder, exist_ok=True)
        if not path:
            path = os.path.join(folder, "polyhedral-atlas.png")
        pixels = glReadPixels(0, 0, self.width, self.height, GL_RGB, GL_UNSIGNED_BYTE)
        surface = pygame.image.fromstring(pixels, (self.width, self.height), "RGB", True)
        pygame.image.save(surface, path)

    def draw(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        x = self.distance * math.cos(math.radians(self.pitch)) * math.sin(math.radians(self.yaw))
        y = -self.distance * math.cos(math.radians(self.pitch)) * math.cos(math.radians(self.yaw))
        z = self.distance * math.sin(math.radians(self.pitch))
        gluLookAt(x, y, z, 0, 0, 0, 0, 0, 1)
        glRotatef(self.angle, 0.2, 0.5, 1.0)
        solid = self.solids[self.selected]
        if self.show_sphere:
            self.draw_sphere()
        self.draw_solid(solid)
        if self.show_dual:
            self.draw_dual(solid)
        if self.show_hud:
            self.draw_panel()
        pygame.display.flip()

    def run(self):
        while self.running:
            delta = self.clock.tick(60) / 1000.0
            self.events()
            if self.auto_rotate and not self.dragging:
                self.angle = (self.angle + 10.0 * delta) % 360
            self.draw()
            self.frames += 1
            if self.pending_capture or (self.capture_path and self.frames == self.capture_frame):
                self.capture(self.capture_path)
                self.pending_capture = False
                if self.capture_path:
                    self.running = False
        pygame.quit()


if __name__ == "__main__":
    AtlasApp().run()
