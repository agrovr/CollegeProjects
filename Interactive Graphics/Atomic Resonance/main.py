import math
import os

import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *

from simulation import (AtomicSimulation, ELEMENTS, clamp, nucleus_layout,
                        wavelength_to_rgb)


START_SIZE = (1280, 720)
CHAMBER = (0.018, 0.024, 0.065)
INK = (0.67, 0.72, 0.82)
PROTON = (0.94, 0.34, 0.29)
NEUTRON = (0.76, 0.59, 0.28)
ELECTRON = (0.34, 0.83, 0.91)


def requested_size():
    raw = os.environ.get("PORTFOLIO_SIZE", "")
    try:
        width, height = (int(value) for value in raw.lower().split("x", 1))
        return max(640, width), max(480, height)
    except (ValueError, TypeError):
        return START_SIZE


def rotate_x(point, degrees):
    angle = math.radians(degrees)
    x, y, z = point
    return x, y * math.cos(angle) - z * math.sin(angle), y * math.sin(angle) + z * math.cos(angle)


def rotate_z(point, degrees):
    angle = math.radians(degrees)
    x, y, z = point
    return x * math.cos(angle) - y * math.sin(angle), x * math.sin(angle) + y * math.cos(angle), z


def normalize(vector):
    length = math.sqrt(sum(value * value for value in vector)) or 1.0
    return tuple(value / length for value in vector)


class AtomicResonanceApp:
    def __init__(self):
        pygame.init()
        pygame.font.init()
        pygame.display.set_caption("Atomic Resonance")
        self.simulation = AtomicSimulation(self.element_from_environment())
        self.yaw = 24.0
        self.pitch = 22.0
        self.distance = 13.2
        self.target = (-0.25, 0.0, 0.0)
        self.dragging = False
        self.running = True
        self.show_hud = True
        self.show_model_note = True
        self.fullscreen = os.environ.get("PORTFOLIO_FULLSCREEN") == "1"
        self.windowed_size = requested_size()
        self.clock = pygame.time.Clock()
        self.frames = 0
        self.pending_capture = False
        self.capture_path = os.environ.get("ATOM_CAPTURE")
        self.capture_frame = int(os.environ.get("ATOM_CAPTURE_FRAME", "100"))
        self.title_font = pygame.font.SysFont("cambria", 27, bold=True)
        self.element_font = pygame.font.SysFont("segoeui", 22)
        self.body_font = pygame.font.SysFont("segoeui", 17)
        self.data_font = pygame.font.SysFont("consolas", 15)
        self.quadric = None
        self.nucleus_cache = {}
        self.create_display()
        if os.environ.get("ATOM_AUTO_EXCITE") == "1":
            self.simulation.excite()

    def element_from_environment(self):
        raw = os.environ.get("ATOM_ELEMENT", "C").strip().lower()
        if raw.isdigit():
            return clamp(int(raw) - 1, 0, len(ELEMENTS) - 1)
        for index, element in enumerate(ELEMENTS):
            if raw in (element.symbol.lower(), element.name.lower()):
                return index
        return 3

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
        glClearColor(*CHAMBER, 1.0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_NORMALIZE)
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        glShadeModel(GL_SMOOTH)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_POINT_SMOOTH)
        glEnable(GL_LINE_SMOOTH)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_LIGHT1)
        glLightfv(GL_LIGHT0, GL_AMBIENT, (0.055, 0.06, 0.10, 1.0))
        glLightfv(GL_LIGHT0, GL_DIFFUSE, (1.0, 0.74, 0.55, 1.0))
        glLightfv(GL_LIGHT0, GL_SPECULAR, (1.0, 0.86, 0.72, 1.0))
        glLightfv(GL_LIGHT1, GL_AMBIENT, (0.01, 0.02, 0.04, 1.0))
        glLightfv(GL_LIGHT1, GL_DIFFUSE, (0.10, 0.24, 0.34, 1.0))
        glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, (0.48, 0.48, 0.52, 1.0))
        glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 38.0)
        self.quadric = gluNewQuadric()
        gluQuadricNormals(self.quadric, GLU_SMOOTH)

    def resize(self, width, height):
        self.width, self.height = max(1, width), max(1, height)
        glViewport(0, 0, self.width, self.height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(43.0, self.width / self.height, 0.12, 60.0)
        glMatrixMode(GL_MODELVIEW)

    def toggle_fullscreen(self):
        if not self.fullscreen:
            self.windowed_size = pygame.display.get_window_size()
        self.fullscreen = not self.fullscreen
        self.create_display()

    def handle_key(self, key):
        if key == K_ESCAPE:
            self.running = False
        elif K_1 <= key <= K_6:
            self.simulation.select_element(key - K_1)
        elif key == K_SPACE:
            self.simulation.excite()
        elif key == K_i:
            self.simulation.cycle_charge()
        elif key == K_n:
            self.simulation.cycle_isotope()
        elif key in (K_PLUS, K_EQUALS, K_KP_PLUS):
            self.simulation.speed = clamp(self.simulation.speed * 1.25, 0.25, 3.0)
        elif key in (K_MINUS, K_KP_MINUS):
            self.simulation.speed = clamp(self.simulation.speed / 1.25, 0.25, 3.0)
        elif key == K_m:
            self.show_model_note = not self.show_model_note
        elif key == K_TAB:
            self.show_hud = not self.show_hud
        elif key == K_p:
            self.pending_capture = True
        elif key == K_F11:
            self.toggle_fullscreen()
        elif key == K_0:
            self.yaw, self.pitch, self.distance = 24.0, 22.0, 13.2

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
                self.yaw += event.rel[0] * 0.28
                self.pitch = clamp(self.pitch + event.rel[1] * 0.25, -72.0, 72.0)
            elif event.type == MOUSEWHEEL:
                self.distance = clamp(self.distance - event.y * 0.65, 7.4, 18.0)

    def shell_radius(self, shell_number):
        return 1.82 + shell_number * 1.22

    def orbit_point(self, shell_number, angle, radius=None):
        radius = self.shell_radius(shell_number) if radius is None else radius
        point = (radius * math.cos(angle), radius * math.sin(angle), 0.0)
        tilts = (32.0, 58.0, -24.0)
        turns = (7.0, -19.0, 30.0)
        point = rotate_x(point, tilts[min(shell_number - 1, 2)])
        return rotate_z(point, turns[min(shell_number - 1, 2)])

    def electron_angle(self, shell_number, slot, count, at_time=None):
        moment = self.simulation.time if at_time is None else at_time
        direction = -1.0 if shell_number % 2 == 0 else 1.0
        return direction * moment * (0.72 + shell_number * 0.18) + math.tau * slot / max(1, count)

    def electron_records(self):
        records = []
        global_index = 0
        last_index = self.simulation.electrons - 1
        for shell_number, count in enumerate(self.simulation.shells, start=1):
            for slot in range(count):
                radius = self.shell_radius(shell_number)
                is_outer = global_index == last_index
                if is_outer and self.simulation.phase == "excited":
                    rise = min(1.0, self.simulation.phase_elapsed / 0.32)
                    radius += 1.12 * (1.0 - (1.0 - rise) ** 3)
                elif is_outer and self.simulation.phase == "emitting":
                    radius += 1.12 * (1.0 - self.simulation.photon_progress)
                angle = self.electron_angle(shell_number, slot, count)
                records.append((self.orbit_point(shell_number, angle, radius), is_outer,
                                shell_number, slot, count))
                global_index += 1
        return records

    def emission_origin(self):
        if not self.simulation.shells:
            return (0.0, 0.0, 0.0)
        shell_number = self.simulation.outer_shell
        count = self.simulation.shells[-1]
        slot = count - 1
        angle = self.electron_angle(shell_number, slot, count, self.simulation.emission_time)
        return self.orbit_point(shell_number, angle, self.shell_radius(shell_number) + 1.12)

    def draw_sphere(self, position, radius, color, slices=22, stacks=14):
        glPushMatrix()
        glTranslatef(*position)
        glColor3f(*color)
        gluSphere(self.quadric, radius, slices, stacks)
        glPopMatrix()

    def draw_chamber(self):
        glDisable(GL_LIGHTING)
        glDepthMask(GL_FALSE)
        glColor4f(0.18, 0.25, 0.40, 0.22)
        glLineWidth(1.0)
        glBegin(GL_LINE_LOOP)
        for index in range(180):
            angle = math.tau * index / 180
            glVertex3f(5.75 * math.cos(angle), 5.75 * math.sin(angle), -1.75)
        glEnd()
        glBegin(GL_LINES)
        for index in range(48):
            angle = math.tau * index / 48
            inner = 5.55 if index % 4 else 5.36
            glVertex3f(inner * math.cos(angle), inner * math.sin(angle), -1.74)
            glVertex3f(5.75 * math.cos(angle), 5.75 * math.sin(angle), -1.74)
        glEnd()
        glDepthMask(GL_TRUE)
        glEnable(GL_LIGHTING)

    def draw_orbit(self, shell_number, radius=None, active=False, opacity=None):
        glDisable(GL_LIGHTING)
        glLineWidth(1.5 if active else 1.0)
        color = ELECTRON if active else (0.31, 0.43, 0.61)
        alpha = opacity if opacity is not None else (0.52 if active else 0.40)
        glColor4f(*color, alpha)
        glBegin(GL_LINE_LOOP)
        for index in range(180):
            glVertex3fv(self.orbit_point(shell_number, math.tau * index / 180, radius))
        glEnd()
        glEnable(GL_LIGHTING)

    def draw_nucleus(self):
        key = (self.simulation.protons, self.simulation.neutrons)
        layout = self.nucleus_cache.setdefault(key, nucleus_layout(*key))
        for index, (kind, position) in enumerate(layout):
            vibration = 0.018 * math.sin(self.simulation.time * 1.7 + index * 1.91)
            direction = normalize(position) if any(position) else (0.0, 0.0, 1.0)
            moved = tuple(position[axis] + direction[axis] * vibration for axis in range(3))
            self.draw_sphere(moved, 0.34, PROTON if kind == "proton" else NEUTRON, 20, 13)

    def draw_electrons(self, records):
        for position, is_outer, _, _, _ in records:
            glDisable(GL_LIGHTING)
            glDepthMask(GL_FALSE)
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE)
            glPointSize(20.0 if is_outer and self.simulation.phase != "idle" else 14.0)
            glColor4f(*ELECTRON, 0.18)
            glBegin(GL_POINTS); glVertex3fv(position); glEnd()
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            glDepthMask(GL_TRUE)
            glEnable(GL_LIGHTING)
            glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, (0.035, 0.14, 0.18, 1.0))
            self.draw_sphere(position, 0.19 if not is_outer else 0.22, ELECTRON, 20, 13)
            glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, (0.0, 0.0, 0.0, 1.0))

    def draw_photon(self):
        if self.simulation.phase != "emitting":
            return
        origin = self.emission_origin()
        direction = normalize((0.48, 0.76, 0.72))
        perpendicular = normalize((-direction[1], direction[0], 0.35))
        distance = 0.35 + 5.4 * self.simulation.photon_progress
        color = wavelength_to_rgb(self.simulation.wavelength_nm)
        glDisable(GL_LIGHTING)
        glDepthMask(GL_FALSE)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE)
        glLineWidth(2.6)
        glBegin(GL_LINE_STRIP)
        for index in range(80):
            along = distance * index / 79
            wave = 0.10 * math.sin(index * 0.82)
            point = tuple(origin[axis] + direction[axis] * along + perpendicular[axis] * wave
                          for axis in range(3))
            glColor4f(*color, 0.25 + 0.75 * index / 79)
            glVertex3fv(point)
        glEnd()
        end = tuple(origin[axis] + direction[axis] * distance for axis in range(3))
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glDepthMask(GL_TRUE)
        glEnable(GL_LIGHTING)
        glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, (*color, 1.0))
        self.draw_sphere(end, 0.14, color, 18, 11)
        glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, (0.0, 0.0, 0.0, 1.0))

    def begin_overlay(self):
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_LIGHTING)
        glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
        glOrtho(0, self.width, self.height, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()

    def end_overlay(self):
        glPopMatrix()
        glMatrixMode(GL_PROJECTION); glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glEnable(GL_LIGHTING)
        glEnable(GL_DEPTH_TEST)

    def draw_text(self, x, y, text, font, color):
        surface = font.render(text, True, color)
        data = pygame.image.tostring(surface, "RGBA", True)
        glDisable(GL_DEPTH_TEST); glDisable(GL_LIGHTING)
        glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glWindowPos2d(x, self.height - y - surface.get_height())
        glDrawPixels(surface.get_width(), surface.get_height(), GL_RGBA, GL_UNSIGNED_BYTE, data)
        glEnable(GL_LIGHTING); glEnable(GL_DEPTH_TEST)

    def draw_hud_shapes(self):
        panel_width = 360
        self.begin_overlay()
        glColor4f(0.025, 0.034, 0.075, 0.95)
        glBegin(GL_QUADS)
        glVertex2f(22, 22); glVertex2f(22 + panel_width, 22)
        glVertex2f(22 + panel_width, 358); glVertex2f(22, 358)
        glEnd()
        glColor4f(0.38, 0.53, 0.70, 0.72)
        glLineWidth(1.0)
        glBegin(GL_LINE_LOOP)
        glVertex2f(22, 22); glVertex2f(22 + panel_width, 22)
        glVertex2f(22 + panel_width, 358); glVertex2f(22, 358)
        glEnd()

        bar_left, bar_right, bar_y = 42, 350, 335
        segments = 72
        glBegin(GL_QUADS)
        for index in range(segments):
            wavelength = 380 + 340 * index / (segments - 1)
            red, green, blue = wavelength_to_rgb(wavelength)
            x1 = bar_left + (bar_right - bar_left) * index / segments
            x2 = bar_left + (bar_right - bar_left) * (index + 1) / segments
            glColor4f(red, green, blue, 0.76)
            glVertex2f(x1, bar_y); glVertex2f(x2, bar_y)
            glVertex2f(x2, bar_y + 7); glVertex2f(x1, bar_y + 7)
        glEnd()
        marker = bar_left + (bar_right - bar_left) * (self.simulation.wavelength_nm - 380) / 340
        glColor4f(0.92, 0.96, 1.0, 0.95)
        glBegin(GL_LINES); glVertex2f(marker, bar_y - 4); glVertex2f(marker, bar_y + 12); glEnd()

        ladder_x = self.width - (136 if self.width >= 1000 else 104)
        ladder_top = 116
        glColor4f(0.35, 0.48, 0.65, 0.68)
        glBegin(GL_LINES)
        for level in range(1, 5):
            y = ladder_top + (4 - level) * 47
            glVertex2f(ladder_x - 45, y); glVertex2f(ladder_x + 42, y)
        glEnd()
        if self.simulation.outer_shell:
            current = self.simulation.outer_shell
            active = current + 1 if self.simulation.phase != "idle" else current
            active_y = ladder_top + (4 - min(4, active)) * 47
            glColor4f(*ELECTRON, 0.95)
            glLineWidth(2.0)
            glBegin(GL_LINES); glVertex2f(ladder_x - 45, active_y); glVertex2f(ladder_x + 42, active_y); glEnd()
            glPointSize(7.0); glBegin(GL_POINTS); glVertex2f(ladder_x - 45, active_y); glEnd()
        self.end_overlay()

    def draw_hud(self, fps):
        self.draw_hud_shapes()
        element = self.simulation.element
        charge = self.simulation.charge
        charge_text = "0" if charge == 0 else f"{charge:+d}"
        shells = " | ".join(str(value) for value in self.simulation.shells) or "NONE"
        phase = self.simulation.phase.upper()
        self.draw_text(42, 36, "ATOMIC RESONANCE", self.title_font, (235, 239, 247))
        self.draw_text(42, 76, f"{element.name.upper()}  {element.symbol}", self.element_font, (105, 214, 230))
        self.draw_text(42, 111, f"Z  {element.atomic_number:2d}     A  {self.simulation.mass_number:2d}     CHARGE  {charge_text}",
                       self.data_font, (184, 195, 216))
        self.draw_text(42, 140, f"PROTONS  {self.simulation.protons:2d}   NEUTRONS  {self.simulation.neutrons:2d}",
                       self.data_font, (211, 190, 160))
        self.draw_text(42, 168, f"ELECTRONS {self.simulation.electrons:2d}   SHELLS  {shells}",
                       self.data_font, (156, 207, 222))
        phase_color = (105, 214, 230) if phase != "IDLE" else (173, 186, 207)
        self.draw_text(42, 197, f"STATE  {phase:<8}   {fps:3.0f} FPS", self.data_font, phase_color)
        photon_color = tuple(int((0.45 + 0.55 * value) * 255)
                             for value in wavelength_to_rgb(self.simulation.wavelength_nm))
        self.draw_text(42, 225, f"MODEL PHOTON  {self.simulation.wavelength_nm:6.1f} NM  {self.simulation.photon_energy_ev:4.2f} EV",
                       self.data_font, photon_color)
        self.draw_text(42, 253, f"TRANSITION  {self.simulation.transition_label}   EVENTS  {self.simulation.event_count}",
                       self.data_font, (184, 195, 216))
        if self.show_model_note:
            self.draw_text(42, 278, "EDUCATIONAL BOHR-MODEL VIEW", self.body_font, (132, 151, 184))
        self.draw_text(42, 309, "VISIBLE SPECTRUM", self.data_font, (145, 161, 190))

        ladder_x = self.width - (136 if self.width >= 1000 else 104)
        self.draw_text(ladder_x - 55, 78, "ENERGY", self.body_font, (191, 201, 220))
        for level in range(1, 5):
            y = 105 + (4 - level) * 47
            self.draw_text(ladder_x + 51, y, f"n={level}", self.data_font, (153, 169, 197))

        if self.width < 1040:
            controls = "1-6 ELEMENT  SPACE EXCITE  I ION  N ISOTOPE  DRAG ORBIT  TAB HUD"
        else:
            controls = "1-6 ELEMENT  SPACE EXCITE  I ION  N ISOTOPE  DRAG ORBIT  WHEEL ZOOM  +/- TIME  TAB HUD"
        text_width = self.data_font.size(controls)[0]
        self.draw_text(max(18, (self.width - text_width) // 2), self.height - 34,
                       controls, self.data_font, (161, 177, 205))

    def capture(self, path=None):
        folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")
        os.makedirs(folder, exist_ok=True)
        path = path or os.path.join(folder, "atomic-resonance.png")
        pixels = glReadPixels(0, 0, self.width, self.height, GL_RGB, GL_UNSIGNED_BYTE)
        surface = pygame.image.fromstring(pixels, (self.width, self.height), "RGB", True)
        pygame.image.save(surface, path)

    def draw(self, fps):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        horizontal = self.distance * math.cos(math.radians(self.pitch))
        eye = (
            self.target[0] + horizontal * math.sin(math.radians(self.yaw)),
            self.target[1] - horizontal * math.cos(math.radians(self.yaw)),
            self.target[2] + self.distance * math.sin(math.radians(self.pitch)),
        )
        gluLookAt(*eye, *self.target, 0, 0, 1)
        glLightfv(GL_LIGHT0, GL_POSITION, (-4.2, -3.0, 6.5, 1.0))
        glLightfv(GL_LIGHT1, GL_POSITION, (4.0, 2.0, 3.5, 1.0))
        self.draw_chamber()
        active_shell = self.simulation.outer_shell if self.simulation.phase != "idle" else 0
        for shell_number in range(1, len(self.simulation.shells) + 1):
            self.draw_orbit(shell_number, active=shell_number == active_shell)
        if self.simulation.phase != "idle" and self.simulation.outer_shell:
            self.draw_orbit(self.simulation.outer_shell,
                            self.shell_radius(self.simulation.outer_shell) + 1.12,
                            active=True, opacity=0.20)
        self.draw_nucleus()
        records = self.electron_records()
        self.draw_electrons(records)
        self.draw_photon()
        if self.show_hud:
            self.draw_hud(fps)
        pygame.display.flip()

    def run(self):
        while self.running:
            delta = min(self.clock.tick(60) / 1000.0, 0.05)
            self.events()
            self.simulation.update(delta)
            self.draw(self.clock.get_fps())
            self.frames += 1
            if self.pending_capture or (self.capture_path and self.frames == self.capture_frame):
                self.capture(self.capture_path)
                self.pending_capture = False
                if self.capture_path:
                    self.running = False
        pygame.quit()


if __name__ == "__main__":
    AtomicResonanceApp().run()
