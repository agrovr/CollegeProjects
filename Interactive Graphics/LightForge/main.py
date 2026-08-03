import math
import os

import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GL.shaders import compileProgram, compileShader

from mesh import load_obj


START_SIZE = (1280, 720)
MODE_NAMES = ("FLAT FACE", "GOURAUD", "PHONG", "NORMAL MAP", "TOON")


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def requested_size():
    raw = os.environ.get("PORTFOLIO_SIZE", "")
    try:
        width, height = (int(value) for value in raw.lower().split("x", 1))
        return (max(640, width), max(480, height))
    except (ValueError, TypeError):
        return START_SIZE


def read_text(path):
    with open(path, "r", encoding="utf-8") as source:
        return source.read()


class LightForgeApp:
    def __init__(self):
        pygame.init()
        pygame.font.init()
        pygame.display.set_caption("LightForge - Mesh Shading Studio")
        self.folder = os.path.dirname(os.path.abspath(__file__))
        self.mesh = load_obj(os.path.join(self.folder, "assets", "teapot.obj"))
        self.mode = int(clamp(int(os.environ.get("LIGHTFORGE_MODE", "0")), 0, 4))
        self.show_normals = False
        self.show_wireframe = False
        self.show_hud = True
        self.auto_rotate = True
        self.rotation = 0.0
        self.yaw = 26.0
        self.pitch = 12.0
        self.distance = 7.0
        self.light_phase = 145.0
        self.shininess = 42.0
        self.dragging = False
        self.running = True
        self.fullscreen = os.environ.get("PORTFOLIO_FULLSCREEN") == "1"
        self.windowed_size = requested_size()
        self.clock = pygame.time.Clock()
        self.pending_capture = False
        self.capture_path = os.environ.get("LIGHTFORGE_CAPTURE")
        self.capture_frame = int(os.environ.get("LIGHTFORGE_CAPTURE_FRAME", "70"))
        self.frames = 0
        self.title_font = pygame.font.SysFont("bahnschrift", 27, bold=True)
        self.body_font = pygame.font.SysFont("segoeui", 18)
        self.data_font = pygame.font.SysFont("consolas", 16)
        self.shader = None
        self.flat_list = None
        self.smooth_list = None
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
        glClearColor(0.018, 0.019, 0.022, 1.0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_NORMALIZE)
        glEnable(GL_CULL_FACE)
        glCullFace(GL_BACK)
        glEnable(GL_LINE_SMOOTH)
        self.shader = compileProgram(
            compileShader(read_text(os.path.join(self.folder, "shaders", "mesh.vert")), GL_VERTEX_SHADER),
            compileShader(read_text(os.path.join(self.folder, "shaders", "mesh.frag")), GL_FRAGMENT_SHADER),
        )
        self.build_display_lists()

    def build_display_lists(self):
        self.flat_list = glGenLists(1)
        glNewList(self.flat_list, GL_COMPILE)
        glBegin(GL_TRIANGLES)
        for face_index, triangle in enumerate(self.mesh.triangles):
            normal = self.mesh.face_normals[face_index]
            for vertex_index in triangle:
                glNormal3fv(normal)
                glVertex3fv(self.mesh.vertices[vertex_index])
        glEnd()
        glEndList()

        self.smooth_list = glGenLists(1)
        glNewList(self.smooth_list, GL_COMPILE)
        glBegin(GL_TRIANGLES)
        for triangle in self.mesh.triangles:
            for vertex_index in triangle:
                glNormal3fv(self.mesh.vertex_normals[vertex_index])
                glVertex3fv(self.mesh.vertices[vertex_index])
        glEnd()
        glEndList()

    def resize(self, width, height):
        self.width, self.height = max(1, width), max(1, height)
        glViewport(0, 0, self.width, self.height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(40.0, self.width / self.height, 0.1, 40.0)
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
            self.mode = key - K_1
        elif key == K_n:
            self.show_normals = not self.show_normals
        elif key == K_w:
            self.show_wireframe = not self.show_wireframe
        elif key == K_SPACE:
            self.auto_rotate = not self.auto_rotate
        elif key == K_q:
            self.light_phase -= 8.0
        elif key == K_e:
            self.light_phase += 8.0
        elif key == K_UP:
            self.shininess = clamp(self.shininess + 4.0, 4.0, 128.0)
        elif key == K_DOWN:
            self.shininess = clamp(self.shininess - 4.0, 4.0, 128.0)
        elif key == K_TAB:
            self.show_hud = not self.show_hud
        elif key == K_p:
            self.pending_capture = True
        elif key == K_F11:
            self.toggle_fullscreen()
        elif key == K_0:
            self.yaw, self.pitch, self.distance = 26.0, 12.0, 7.0

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
                self.pitch = clamp(self.pitch + event.rel[1] * 0.28, -75, 75)
            elif event.type == MOUSEWHEEL:
                self.distance = clamp(self.distance - event.y * 0.35, 4.2, 11.0)

    def lights(self):
        phase = math.radians(self.light_phase)
        blue = (4.2 * math.cos(phase), 3.0 * math.sin(phase), 2.0)
        red = (-blue[0], -blue[1], 1.2)
        return blue, red

    def set_uniforms(self):
        blue, red = self.lights()
        glUniform1i(glGetUniformLocation(self.shader, "renderMode"), self.mode)
        glUniform3f(glGetUniformLocation(self.shader, "blueLight"), *blue)
        glUniform3f(glGetUniformLocation(self.shader, "redLight"), *red)
        glUniform3f(glGetUniformLocation(self.shader, "baseColor"), 0.73, 0.70, 0.64)
        glUniform1f(glGetUniformLocation(self.shader, "shininess"), self.shininess)

    def model_transform(self):
        glRotatef(self.pitch, 1, 0, 0)
        glRotatef(self.yaw + self.rotation, 0, 0, 1)
        glRotatef(-90, 1, 0, 0)
        scale = 2.45 / self.mesh.radius
        glScalef(scale, scale, scale)
        glTranslatef(-self.mesh.center[0], -self.mesh.center[1], -self.mesh.center[2])

    def draw_mesh(self):
        glUseProgram(self.shader)
        self.set_uniforms()
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE if self.show_wireframe else GL_FILL)
        glCallList(self.flat_list if self.mode == 0 else self.smooth_list)
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        glUseProgram(0)

    def draw_normals(self):
        if not self.show_normals:
            return
        glDisable(GL_CULL_FACE)
        glDisable(GL_DEPTH_TEST)
        glColor3f(0.20, 0.82, 0.72)
        glLineWidth(1.0)
        glBegin(GL_LINES)
        step = max(1, len(self.mesh.triangles) // 900)
        length = self.mesh.radius * 0.045
        for index in range(0, len(self.mesh.triangles), step):
            center = self.mesh.face_centers[index]
            normal = self.mesh.face_normals[index]
            glVertex3fv(center)
            glVertex3f(center[0] + normal[0] * length,
                       center[1] + normal[1] * length,
                       center[2] + normal[2] * length)
        glEnd()
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_CULL_FACE)

    def draw_stage(self):
        glDisable(GL_CULL_FACE)
        glDisable(GL_LIGHTING)
        glColor4f(0.10, 0.105, 0.12, 1.0)
        glBegin(GL_QUADS)
        glVertex3f(-7, -7, -2.48); glVertex3f(7, -7, -2.48)
        glVertex3f(7, 7, -2.48); glVertex3f(-7, 7, -2.48)
        glEnd()
        glColor4f(0.22, 0.23, 0.25, 0.55)
        glBegin(GL_LINE_LOOP)
        for index in range(96):
            angle = math.tau * index / 96
            glVertex3f(math.cos(angle) * 3.6, math.sin(angle) * 3.6, -2.46)
        glEnd()
        glEnable(GL_CULL_FACE)

    def draw_text(self, x, y, text, font, color):
        surface = font.render(text, True, color)
        data = pygame.image.tostring(surface, "RGBA", True)
        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glWindowPos2d(x, self.height - y - surface.get_height())
        glDrawPixels(surface.get_width(), surface.get_height(), GL_RGBA, GL_UNSIGNED_BYTE, data)
        glDisable(GL_BLEND)
        glEnable(GL_DEPTH_TEST)

    def draw_hud(self, fps):
        glDisable(GL_DEPTH_TEST)
        glMatrixMode(GL_PROJECTION)
        glPushMatrix(); glLoadIdentity(); glOrtho(0, self.width, self.height, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix(); glLoadIdentity()
        glColor4f(0.035, 0.037, 0.043, 0.93)
        glBegin(GL_QUADS)
        glVertex2f(22, 22); glVertex2f(378, 22); glVertex2f(378, 238); glVertex2f(22, 238)
        glEnd()
        glColor4f(0.34, 0.36, 0.40, 0.86)
        glBegin(GL_LINE_LOOP)
        glVertex2f(22, 22); glVertex2f(378, 22); glVertex2f(378, 238); glVertex2f(22, 238)
        glEnd()
        glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix(); glMatrixMode(GL_MODELVIEW)
        glEnable(GL_DEPTH_TEST)
        self.draw_text(42, 36, "LIGHTFORGE", self.title_font, (238, 236, 230))
        self.draw_text(42, 74, MODE_NAMES[self.mode], self.body_font, (112, 174, 255))
        self.draw_text(42, 108, f"VERTICES   {len(self.mesh.vertices):5d}", self.data_font, (188, 192, 202))
        self.draw_text(42, 136, f"TRIANGLES  {len(self.mesh.triangles):5d}", self.data_font, (188, 192, 202))
        self.draw_text(42, 164, f"SHININESS  {self.shininess:5.1f}", self.data_font, (188, 192, 202))
        self.draw_text(42, 192, f"NORMALS {'VISIBLE' if self.show_normals else 'HIDDEN':>9}    {fps:3.0f} FPS", self.data_font, (134, 208, 190))
        controls = "1-5 SHADING  DRAG ORBIT  WHEEL ZOOM  Q/E LIGHTS  N NORMALS  W WIREFRAME"
        width = self.data_font.size(controls)[0]
        self.draw_text(max(18, (self.width - width) // 2), self.height - 34,
                       controls, self.data_font, (176, 180, 190))

    def capture(self, path=None):
        folder = os.path.join(self.folder, "screenshots")
        os.makedirs(folder, exist_ok=True)
        path = path or os.path.join(folder, "lightforge.png")
        pixels = glReadPixels(0, 0, self.width, self.height, GL_RGB, GL_UNSIGNED_BYTE)
        surface = pygame.image.fromstring(pixels, (self.width, self.height), "RGB", True)
        pygame.image.save(surface, path)

    def draw(self, fps):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        glTranslatef(0, 0, -self.distance)
        self.draw_stage()
        glPushMatrix()
        self.model_transform()
        self.draw_mesh()
        self.draw_normals()
        glPopMatrix()
        if self.show_hud:
            self.draw_hud(fps)
        pygame.display.flip()

    def run(self):
        while self.running:
            delta = min(self.clock.tick(60) / 1000.0, 0.05)
            self.events()
            if self.auto_rotate and not self.dragging:
                self.rotation = (self.rotation + 12.0 * delta) % 360
            self.draw(self.clock.get_fps())
            self.frames += 1
            if self.pending_capture or (self.capture_path and self.frames == self.capture_frame):
                self.capture(self.capture_path)
                self.pending_capture = False
                if self.capture_path:
                    self.running = False
        pygame.quit()


if __name__ == "__main__":
    LightForgeApp().run()
