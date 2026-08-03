import math
import os
import random
from dataclasses import dataclass, field

import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GL.shaders import compileProgram, compileShader


START_SIZE = (1280, 720)
MAX_PARTICLES = 4000
MODE_NAMES = ("FOUNTAIN", "VORTEX", "EMBERS", "FIREWORKS")


def clamp(value, minimum, maximum):
    return max(minimum, min(value, maximum))


def mix_color(first, second, amount):
    amount = clamp(amount, 0.0, 1.0)
    return tuple(first[i] + (second[i] - first[i]) * amount
                 for i in range(3))


@dataclass
class Particle:
    position: list
    velocity: list
    age: float
    life: float
    size: float
    mode: str
    base_color: tuple = (1.0, 1.0, 1.0)
    phase: float = 0.0
    trail: list = field(default_factory=list)
    trail_timer: float = 0.0


class ParticleSystem:
    def __init__(self):
        self.particles = []
        self.mode_index = 0
        self.spawn_rate = 220
        self.launch_speed = 8.5
        self.cone_angle = 28
        self.gravity = -9.8
        self.spawn_leftover = 0.0
        self.firework_leftover = 0.0
        self.time = 0.0
        self.trails_enabled = True
        self.impact_sparks = True

    @property
    def mode(self):
        return MODE_NAMES[self.mode_index]

    def set_mode(self, mode_index):
        self.mode_index = mode_index
        self.clear()

    def clear(self):
        self.particles.clear()
        self.spawn_leftover = 0.0
        self.firework_leftover = 0.0

    def create_fountain_particle(self):
        direction = random.uniform(0.0, math.tau)
        tilt = math.radians(random.uniform(0.0, self.cone_angle))
        speed = random.uniform(self.launch_speed * 0.82,
                               self.launch_speed * 1.18)
        horizontal = math.sin(tilt) * speed
        radius = math.sqrt(random.random()) * 0.15
        start_angle = random.uniform(0.0, math.tau)

        return Particle(
            [radius * math.cos(start_angle), 1.88,
             radius * math.sin(start_angle)],
            [horizontal * math.cos(direction), math.cos(tilt) * speed,
             horizontal * math.sin(direction)],
            0.0, random.uniform(1.8, 2.7), random.uniform(0.09, 0.16),
            "FOUNTAIN", phase=random.uniform(0.0, math.tau)
        )

    def create_vortex_particle(self):
        angle = random.uniform(0.0, math.tau)
        radius = random.uniform(0.18, 0.48)
        return Particle(
            [math.cos(angle) * radius, 1.65,
             math.sin(angle) * radius],
            [-math.sin(angle) * random.uniform(2.0, 3.8),
             random.uniform(1.2, 2.1),
             math.cos(angle) * random.uniform(2.0, 3.8)],
            0.0, random.uniform(3.2, 4.6), random.uniform(0.08, 0.15),
            "VORTEX", phase=random.uniform(0.0, math.tau)
        )

    def create_ember_particle(self):
        angle = random.uniform(0.0, math.tau)
        radius = math.sqrt(random.random()) * 0.23
        return Particle(
            [math.cos(angle) * radius, 1.72,
             math.sin(angle) * radius],
            [random.uniform(-0.45, 0.45), random.uniform(1.7, 3.6),
             random.uniform(-0.45, 0.45)],
            0.0, random.uniform(2.2, 4.1), random.uniform(0.06, 0.14),
            "EMBERS", phase=random.uniform(0.0, math.tau)
        )

    def create_rocket(self):
        return Particle(
            [random.uniform(-0.12, 0.12), 1.88,
             random.uniform(-0.12, 0.12)],
            [random.uniform(-0.75, 0.75), random.uniform(4.8, 6.2),
             random.uniform(-0.75, 0.75)],
            0.0, random.uniform(0.70, 0.95), 0.16,
            "ROCKET", phase=random.uniform(0.0, math.tau)
        )

    def create_firework_burst(self, position):
        palette = random.choice((
            ((1.00, 0.10, 0.65), (0.20, 0.85, 1.00)),
            ((1.00, 0.52, 0.08), (1.00, 0.92, 0.30)),
            ((0.28, 1.00, 0.72), (0.36, 0.45, 1.00)),
        ))
        burst = []
        amount = int(clamp(self.spawn_rate * 0.38, 45, 115))

        for index in range(amount):
            direction = random.uniform(0.0, math.tau)
            vertical = random.uniform(-0.9, 0.75)
            horizontal = math.sqrt(max(0.0, 1.0 - vertical * vertical))
            speed = random.uniform(2.2, 4.8)
            color = mix_color(palette[0], palette[1], index / max(1, amount - 1))
            burst.append(Particle(
                list(position),
                [math.cos(direction) * horizontal * speed,
                 vertical * speed,
                 math.sin(direction) * horizontal * speed],
                0.0, random.uniform(1.3, 2.3), random.uniform(0.07, 0.13),
                "FIREWORK", base_color=color,
                phase=random.uniform(0.0, math.tau)
            ))
        return burst

    def create_impact_sparks(self, position):
        sparks = []
        for _ in range(4):
            angle = random.uniform(0.0, math.tau)
            speed = random.uniform(0.8, 2.2)
            sparks.append(Particle(
                [position[0], 0.05, position[2]],
                [math.cos(angle) * speed, random.uniform(0.7, 1.8),
                 math.sin(angle) * speed],
                0.0, random.uniform(0.25, 0.55), random.uniform(0.035, 0.075),
                "IMPACT", base_color=(0.20, 0.90, 1.00)
            ))
        return sparks

    def spawn_particles(self, delta_time):
        created = []

        if self.mode == "FIREWORKS":
            rockets_per_second = clamp(self.spawn_rate / 180.0, 0.3, 5.5)
            self.firework_leftover += rockets_per_second * delta_time
            while self.firework_leftover >= 1.0:
                created.append(self.create_rocket())
                self.firework_leftover -= 1.0
        else:
            self.spawn_leftover += self.spawn_rate * delta_time
            while self.spawn_leftover >= 1.0:
                if self.mode == "FOUNTAIN":
                    created.append(self.create_fountain_particle())
                elif self.mode == "VORTEX":
                    created.append(self.create_vortex_particle())
                else:
                    created.append(self.create_ember_particle())
                self.spawn_leftover -= 1.0

        room = max(0, MAX_PARTICLES - len(self.particles))
        self.particles.extend(created[:room])

    def update(self, delta_time):
        self.time += delta_time
        self.spawn_particles(delta_time)
        alive = []
        created = []

        for particle in self.particles:
            particle.age += delta_time
            particle.trail_timer += delta_time

            if self.trails_enabled and particle.trail_timer >= 0.035:
                particle.trail.append(tuple(particle.position))
                particle.trail = particle.trail[-6:]
                particle.trail_timer = 0.0

            if particle.mode == "VORTEX":
                x = particle.position[0]
                z = particle.position[2]
                particle.velocity[0] += (-x * 1.1 - z * 1.65) * delta_time
                particle.velocity[2] += (-z * 1.1 + x * 1.65) * delta_time
                particle.velocity[1] += 0.18 * delta_time
                damping = pow(0.992, delta_time * 60.0)
                particle.velocity[0] *= damping
                particle.velocity[2] *= damping
            elif particle.mode == "EMBERS":
                particle.velocity[0] += math.sin(
                    self.time * 2.3 + particle.phase) * 0.9 * delta_time
                particle.velocity[2] += math.cos(
                    self.time * 1.9 + particle.phase) * 0.9 * delta_time
                particle.velocity[1] += 0.18 * delta_time
            elif particle.mode in ("FOUNTAIN", "ROCKET", "FIREWORK", "IMPACT"):
                gravity = self.gravity
                if particle.mode == "ROCKET":
                    gravity *= 0.35
                elif particle.mode == "FIREWORK":
                    gravity *= 0.50
                elif particle.mode == "IMPACT":
                    gravity *= 0.75
                particle.velocity[1] += gravity * delta_time

            if particle.mode == "FIREWORK":
                damping = pow(0.985, delta_time * 60.0)
                for axis in range(3):
                    particle.velocity[axis] *= damping

            for axis in range(3):
                particle.position[axis] += particle.velocity[axis] * delta_time

            if particle.mode == "ROCKET" and particle.age >= particle.life:
                created.extend(self.create_firework_burst(particle.position))
                continue

            hit_ground = (particle.position[1] <= 0.04 and
                          particle.mode in ("FOUNTAIN", "FIREWORK", "IMPACT"))
            if hit_ground:
                if (self.impact_sparks and particle.mode == "FOUNTAIN" and
                        random.random() < 0.12):
                    created.extend(self.create_impact_sparks(particle.position))
                continue

            if particle.age < particle.life and particle.position[1] < 18.0:
                alive.append(particle)

        room = max(0, MAX_PARTICLES - len(alive))
        alive.extend(created[:room])
        self.particles = alive

    def particle_appearance(self, particle):
        remaining = clamp(1.0 - particle.age / particle.life, 0.0, 1.0)
        progress = 1.0 - remaining

        if particle.mode == "FOUNTAIN":
            if progress < 0.55:
                color = mix_color((1.00, 0.06, 0.65),
                                  (0.05, 0.86, 1.00), progress / 0.55)
            else:
                color = mix_color((0.05, 0.86, 1.00),
                                  (0.35, 1.00, 0.72), (progress - 0.55) / 0.45)
        elif particle.mode == "VORTEX":
            color = mix_color((0.12, 0.92, 1.00),
                              (0.72, 0.18, 1.00), progress)
        elif particle.mode == "EMBERS":
            if progress < 0.45:
                color = mix_color((1.00, 0.95, 0.62),
                                  (1.00, 0.35, 0.05), progress / 0.45)
            else:
                color = mix_color((1.00, 0.35, 0.05),
                                  (0.42, 0.03, 0.01), (progress - 0.45) / 0.55)
        elif particle.mode == "ROCKET":
            color = (0.60, 0.92, 1.00)
        else:
            color = particle.base_color

        pulse = 0.92 + 0.13 * math.sin(self.time * 15.0 + particle.phase)
        alpha = clamp(remaining * 2.8, 0.0, 1.0)
        return color, alpha, particle.size * pulse


def read_text_file(path):
    with open(path, "r", encoding="utf-8") as source_file:
        return source_file.read()


def load_texture(path):
    surface = pygame.image.load(path).convert_alpha()
    texture_data = pygame.image.tostring(surface, "RGBA", True)
    width, height = surface.get_size()
    texture = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texture)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0,
                 GL_RGBA, GL_UNSIGNED_BYTE, texture_data)
    glGenerateMipmap(GL_TEXTURE_2D)
    return texture


def draw_torus(major_radius, minor_radius, major_steps=48, minor_steps=10):
    for major_index in range(major_steps):
        first_angle = math.tau * major_index / major_steps
        second_angle = math.tau * (major_index + 1) / major_steps
        glBegin(GL_QUAD_STRIP)
        for minor_index in range(minor_steps + 1):
            minor_angle = math.tau * minor_index / minor_steps
            cos_minor = math.cos(minor_angle)
            sin_minor = math.sin(minor_angle)

            for major_angle in (first_angle, second_angle):
                cos_major = math.cos(major_angle)
                sin_major = math.sin(major_angle)
                radius = major_radius + minor_radius * cos_minor
                glNormal3f(cos_major * cos_minor, sin_minor,
                           sin_major * cos_minor)
                glVertex3f(radius * cos_major, minor_radius * sin_minor,
                           radius * sin_major)
        glEnd()


class Renderer:
    def __init__(self, folder, width, height):
        self.folder = folder
        self.width = width
        self.height = height
        self.shader = None
        self.texture = None
        self.quadric = None
        self.small_font = pygame.font.SysFont("consolas", 17)
        self.medium_font = pygame.font.SysFont("consolas", 21, bold=True)
        self.title_font = pygame.font.SysFont("arial", 26, bold=True)
        self.initialize_gl()

    def initialize_gl(self):
        glClearColor(0.004, 0.006, 0.016, 1.0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_NORMALIZE)
        glShadeModel(GL_SMOOTH)
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)

        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_LIGHT1)
        glLightfv(GL_LIGHT0, GL_AMBIENT, (0.10, 0.12, 0.20, 1.0))
        glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.90, 0.92, 1.00, 1.0))
        glLightfv(GL_LIGHT0, GL_SPECULAR, (1.00, 1.00, 1.00, 1.0))
        glLightfv(GL_LIGHT1, GL_AMBIENT, (0.02, 0.04, 0.08, 1.0))
        glLightfv(GL_LIGHT1, GL_DIFFUSE, (0.05, 0.72, 1.00, 1.0))
        glLightfv(GL_LIGHT1, GL_SPECULAR, (0.30, 0.90, 1.00, 1.0))
        glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, (0.85, 0.90, 1.00, 1.0))
        glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 56.0)

        vertex_path = os.path.join(self.folder, "shaders", "particle.vert")
        fragment_path = os.path.join(self.folder, "shaders", "particle.frag")
        self.shader = compileProgram(
            compileShader(read_text_file(vertex_path), GL_VERTEX_SHADER),
            compileShader(read_text_file(fragment_path), GL_FRAGMENT_SHADER)
        )
        self.texture = load_texture(
            os.path.join(self.folder, "assets", "fountain_texture.png"))
        self.quadric = gluNewQuadric()
        gluQuadricNormals(self.quadric, GLU_SMOOTH)
        self.resize(self.width, self.height)

    def resize(self, width, height):
        self.width = max(1, width)
        self.height = max(1, height)
        glViewport(0, 0, self.width, self.height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(48.0, self.width / self.height, 0.08, 80.0)
        glMatrixMode(GL_MODELVIEW)

    def draw_ground(self, time_value):
        glDisable(GL_TEXTURE_2D)
        glColor3f(0.018, 0.028, 0.055)
        glNormal3f(0.0, 1.0, 0.0)
        glBegin(GL_QUADS)
        glVertex3f(-12.0, 0.0, -12.0)
        glVertex3f(-12.0, 0.0, 12.0)
        glVertex3f(12.0, 0.0, 12.0)
        glVertex3f(12.0, 0.0, -12.0)
        glEnd()

        glDisable(GL_LIGHTING)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE)
        glLineWidth(1.0)
        glBegin(GL_LINES)
        for grid_line in range(-10, 11):
            alpha = 0.16 if grid_line % 2 else 0.26
            glColor4f(0.04, 0.45, 0.68, alpha)
            glVertex3f(grid_line, 0.006, -10.0)
            glVertex3f(grid_line, 0.006, 10.0)
            glVertex3f(-10.0, 0.006, grid_line)
            glVertex3f(10.0, 0.006, grid_line)
        glEnd()

        pulse = 0.32 + 0.12 * math.sin(time_value * 2.2)
        for radius in (2.0, 3.6, 5.8):
            glColor4f(0.05, 0.72, 1.0, pulse / (radius * 0.55))
            glBegin(GL_LINE_LOOP)
            for index in range(96):
                angle = math.tau * index / 96
                glVertex3f(math.cos(angle) * radius, 0.012,
                           math.sin(angle) * radius)
            glEnd()
        glDisable(GL_BLEND)
        glEnable(GL_LIGHTING)

    def draw_reactor(self, time_value, mode_index):
        slices = 48
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.texture)
        glColor3f(0.75, 0.82, 0.95)
        glBegin(GL_QUAD_STRIP)
        for index in range(slices + 1):
            angle = math.tau * index / slices
            x = math.cos(angle)
            z = math.sin(angle)
            glNormal3f(x, 0.0, z)
            glTexCoord2f(5.0 * index / slices, 0.0)
            glVertex3f(1.18 * x, 0.12, 1.18 * z)
            glTexCoord2f(5.0 * index / slices, 1.0)
            glVertex3f(1.18 * x, 0.78, 1.18 * z)
        glEnd()
        glDisable(GL_TEXTURE_2D)

        glPushMatrix()
        glTranslatef(0.0, 0.12, 0.0)
        glRotatef(-90.0, 1.0, 0.0, 0.0)
        glColor3f(0.035, 0.055, 0.10)
        gluDisk(self.quadric, 0.0, 1.30, slices, 1)
        glPopMatrix()

        colors = ((0.06, 0.82, 1.00), (0.66, 0.12, 1.00),
                  (1.00, 0.24, 0.04), (1.00, 0.60, 0.10))
        reactor_color = colors[mode_index]
        glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION,
                     (*tuple(value * 0.32 for value in reactor_color), 1.0))

        glPushMatrix()
        glTranslatef(0.0, 1.12, 0.0)
        glColor3f(*reactor_color)
        gluSphere(self.quadric, 0.34 + 0.025 * math.sin(time_value * 5.0),
                  28, 20)
        glPopMatrix()

        for rotation, speed, radius in ((0.0, 32.0, 0.72),
                                        (60.0, -24.0, 0.92),
                                        (-60.0, 18.0, 1.12)):
            glPushMatrix()
            glTranslatef(0.0, 1.12, 0.0)
            glRotatef(rotation, 1.0, 0.0, 0.0)
            glRotatef(time_value * speed, 0.0, 1.0, 0.0)
            glColor3f(*reactor_color)
            draw_torus(radius, 0.026 if radius < 1.0 else 0.032)
            glPopMatrix()

        glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, (0.0, 0.0, 0.0, 1.0))

        glPushMatrix()
        glTranslatef(0.0, 1.42, 0.0)
        glRotatef(-90.0, 1.0, 0.0, 0.0)
        glColor3f(0.05, 0.11, 0.19)
        gluCylinder(self.quadric, 0.34, 0.20, 0.35, 32, 1)
        glTranslatef(0.0, 0.0, 0.35)
        glColor3f(*reactor_color)
        gluDisk(self.quadric, 0.0, 0.20, 32, 1)
        glPopMatrix()

    def draw_trails(self, system):
        if not system.trails_enabled:
            return

        glUseProgram(0)
        glDisable(GL_LIGHTING)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE)
        glDepthMask(GL_FALSE)
        glLineWidth(1.4)

        glBegin(GL_LINES)
        for particle_index, particle in enumerate(system.particles):
            if particle_index % 2:
                continue
            if len(particle.trail) < 2:
                continue
            color, alpha, _ = system.particle_appearance(particle)
            count = len(particle.trail)
            for index in range(count - 1):
                first_alpha = alpha * (index / count) * 0.34
                second_alpha = alpha * ((index + 1) / count) * 0.34
                glColor4f(*color, first_alpha)
                glVertex3f(*particle.trail[index])
                glColor4f(*color, second_alpha)
                glVertex3f(*particle.trail[index + 1])
        glEnd()

        glLineWidth(1.0)
        glDepthMask(GL_TRUE)
        glDisable(GL_BLEND)
        glEnable(GL_LIGHTING)

    def draw_particles(self, system):
        glDisable(GL_LIGHTING)
        glDisable(GL_TEXTURE_2D)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE)
        glDepthMask(GL_FALSE)
        glEnable(GL_PROGRAM_POINT_SIZE)
        try:
            glEnable(GL_POINT_SPRITE)
        except Exception:
            pass

        glUseProgram(self.shader)
        point_scale = glGetUniformLocation(self.shader, "pointScale")
        particle_size = glGetUniformLocation(self.shader, "particleSize")
        glUniform1f(point_scale, self.height * 1.25)

        size_groups = {}
        for particle in system.particles:
            color, alpha, size = system.particle_appearance(particle)
            size_key = round(size, 2)
            size_groups.setdefault(size_key, []).append((particle, color, alpha))

        for size, particles in size_groups.items():
            glUniform1f(particle_size, size)
            glBegin(GL_POINTS)
            for particle, color, alpha in particles:
                glColor4f(*color, alpha)
                glVertex3f(*particle.position)
            glEnd()
        glUseProgram(0)

        glDepthMask(GL_TRUE)
        glDisable(GL_BLEND)
        glEnable(GL_LIGHTING)

    def draw_panel(self, x, y, width, height):
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, self.width, self.height, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_LIGHTING)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glColor4f(0.015, 0.025, 0.055, 0.84)
        glBegin(GL_QUADS)
        glVertex2f(x, y)
        glVertex2f(x + width, y)
        glVertex2f(x + width, y + height)
        glVertex2f(x, y + height)
        glEnd()
        glColor4f(0.05, 0.72, 1.0, 0.75)
        glLineWidth(1.4)
        glBegin(GL_LINE_LOOP)
        glVertex2f(x, y)
        glVertex2f(x + width, y)
        glVertex2f(x + width, y + height)
        glVertex2f(x, y + height)
        glEnd()
        glLineWidth(1.0)
        glDisable(GL_BLEND)
        glEnable(GL_DEPTH_TEST)
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)

    def draw_text(self, x, y, text, font, color):
        surface = font.render(text, True, color)
        data = pygame.image.tostring(surface, "RGBA", True)
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_LIGHTING)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glWindowPos2d(x, self.height - y - surface.get_height())
        glDrawPixels(surface.get_width(), surface.get_height(), GL_RGBA,
                     GL_UNSIGNED_BYTE, data)
        glDisable(GL_BLEND)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)

    def draw_hud(self, system, fps, paused):
        panel_width = 385
        panel_height = 222
        self.draw_panel(22, 22, panel_width, panel_height)
        self.draw_text(42, 35, "AETHER REACTOR", self.title_font,
                       (245, 250, 255))
        self.draw_text(42, 72, "MODE", self.small_font, (90, 210, 255))
        self.draw_text(116, 69, system.mode, self.medium_font,
                       (255, 80, 190))
        self.draw_text(42, 104, "Particles  %4d / %d" %
                       (len(system.particles), MAX_PARTICLES),
                       self.small_font, (215, 225, 240))
        self.draw_text(42, 130, "Launch     %4.1f    Cone %2d deg" %
                       (system.launch_speed, system.cone_angle),
                       self.small_font, (215, 225, 240))
        self.draw_text(42, 156, "Rate       %4d/s  Gravity %4.1f" %
                       (system.spawn_rate, system.gravity),
                       self.small_font, (215, 225, 240))
        self.draw_text(42, 182, "FPS        %4.0f    Trails %s" %
                       (fps, "ON" if system.trails_enabled else "OFF"),
                       self.small_font, (215, 225, 240))
        status = "PAUSED" if paused else "LIVE SIMULATION"
        status_color = (255, 190, 75) if paused else (80, 255, 190)
        self.draw_text(42, 208, status, self.small_font, status_color)

        controls = "1-4 MODE   DRAG ORBIT   W/S ZOOM   TAB HUD   P CAPTURE   F11 FULLSCREEN"
        text_width = self.small_font.size(controls)[0]
        x = max(18, (self.width - text_width) // 2)
        self.draw_text(x, self.height - 34, controls, self.small_font,
                       (155, 210, 235))


class AetherReactorApp:
    def __init__(self):
        pygame.init()
        pygame.font.init()
        pygame.display.set_caption("Aether Reactor - Particle Simulation")
        self.folder = os.path.dirname(os.path.abspath(__file__))
        self.windowed_size = START_SIZE
        self.fullscreen = False
        self.width, self.height = START_SIZE
        self.renderer = None
        self.system = ParticleSystem()
        self.clock = pygame.time.Clock()
        self.running = True
        self.paused = False
        self.show_hud = True
        self.dragging = False
        self.camera_yaw = 28.0
        self.camera_pitch = 20.0
        self.camera_distance = 12.5
        self.pending_screenshot = False
        self.capture_path = os.environ.get("AETHER_CAPTURE")
        self.capture_at_frame = int(os.environ.get("AETHER_CAPTURE_FRAME", "90"))
        self.capture_frame = 0
        self.create_display()

    def create_display(self):
        try:
            pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 1)
            pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, 4)
        except pygame.error:
            pass

        flags = DOUBLEBUF | OPENGL
        if self.fullscreen:
            flags |= FULLSCREEN
            size = pygame.display.get_desktop_sizes()[0]
        else:
            flags |= RESIZABLE
            size = self.windowed_size

        try:
            pygame.display.set_mode(size, flags, vsync=1)
        except pygame.error:
            pygame.display.set_mode(size, flags)

        self.width, self.height = pygame.display.get_window_size()
        self.renderer = Renderer(self.folder, self.width, self.height)

    def toggle_fullscreen(self):
        if not self.fullscreen:
            self.windowed_size = pygame.display.get_window_size()
        self.fullscreen = not self.fullscreen
        self.create_display()

    def reset_camera(self):
        self.camera_yaw = 28.0
        self.camera_pitch = 20.0
        self.camera_distance = 12.5

    def handle_key(self, key):
        if key == K_ESCAPE:
            self.running = False
        elif key in (K_1, K_2, K_3, K_4):
            self.system.set_mode(key - K_1)
        elif key == K_SPACE:
            self.paused = not self.paused
        elif key == K_r:
            self.system.clear()
        elif key == K_TAB:
            self.show_hud = not self.show_hud
        elif key == K_F11:
            self.toggle_fullscreen()
        elif key == K_t:
            self.system.trails_enabled = not self.system.trails_enabled
        elif key == K_p:
            self.pending_screenshot = True
        elif key == K_0:
            self.reset_camera()
        elif key == K_LEFT:
            self.system.launch_speed = clamp(
                self.system.launch_speed - 0.5, 3.0, 15.0)
        elif key == K_RIGHT:
            self.system.launch_speed = clamp(
                self.system.launch_speed + 0.5, 3.0, 15.0)
        elif key == K_COMMA:
            self.system.cone_angle = int(clamp(
                self.system.cone_angle - 2, 4, 75))
        elif key == K_PERIOD:
            self.system.cone_angle = int(clamp(
                self.system.cone_angle + 2, 4, 75))
        elif key in (K_EQUALS, K_PLUS, K_KP_PLUS):
            self.system.spawn_rate = int(clamp(
                self.system.spawn_rate + 25, 20, 1000))
        elif key in (K_MINUS, K_KP_MINUS):
            self.system.spawn_rate = int(clamp(
                self.system.spawn_rate - 25, 20, 1000))
        elif key == K_UP:
            self.system.gravity = clamp(self.system.gravity + 0.5, -18.0, -1.0)
        elif key == K_DOWN:
            self.system.gravity = clamp(self.system.gravity - 0.5, -18.0, -1.0)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == QUIT:
                self.running = False
            elif event.type == KEYDOWN:
                self.handle_key(event.key)
            elif event.type == MOUSEBUTTONDOWN and event.button == 1:
                self.dragging = True
            elif event.type == MOUSEBUTTONUP and event.button == 1:
                self.dragging = False
            elif event.type == MOUSEMOTION and self.dragging:
                self.camera_yaw += event.rel[0] * 0.28
                self.camera_pitch = clamp(
                    self.camera_pitch - event.rel[1] * 0.24, -8.0, 72.0)
            elif event.type == MOUSEWHEEL:
                self.camera_distance = clamp(
                    self.camera_distance - event.y * 0.7, 5.5, 25.0)
            elif event.type in (VIDEORESIZE, WINDOWRESIZED):
                self.width, self.height = pygame.display.get_window_size()
                if not self.fullscreen:
                    self.windowed_size = (self.width, self.height)
                self.renderer.resize(self.width, self.height)

    def update_camera_keys(self, delta_time):
        keys = pygame.key.get_pressed()
        if keys[K_a]:
            self.camera_yaw -= 42.0 * delta_time
        if keys[K_d]:
            self.camera_yaw += 42.0 * delta_time
        if keys[K_w]:
            self.camera_distance = clamp(
                self.camera_distance - 5.0 * delta_time, 5.5, 25.0)
        if keys[K_s]:
            self.camera_distance = clamp(
                self.camera_distance + 5.0 * delta_time, 5.5, 25.0)

    def apply_camera(self):
        yaw = math.radians(self.camera_yaw)
        pitch = math.radians(self.camera_pitch)
        horizontal = self.camera_distance * math.cos(pitch)
        eye_x = horizontal * math.sin(yaw)
        eye_y = 1.75 + self.camera_distance * math.sin(pitch)
        eye_z = horizontal * math.cos(yaw)
        gluLookAt(eye_x, eye_y, eye_z, 0.0, 2.0, 0.0, 0.0, 1.0, 0.0)

    def draw(self, fps):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        self.apply_camera()

        glLightfv(GL_LIGHT0, GL_POSITION, (3.0, 8.0, 4.0, 1.0))
        glLightfv(GL_LIGHT1, GL_POSITION, (0.0, 2.1, 0.0, 1.0))
        self.renderer.draw_ground(self.system.time)
        self.renderer.draw_reactor(self.system.time, self.system.mode_index)
        self.renderer.draw_trails(self.system)
        self.renderer.draw_particles(self.system)

        if self.show_hud:
            self.renderer.draw_hud(self.system, fps, self.paused)

        self.capture_frame += 1
        if (self.pending_screenshot or
                (self.capture_path and self.capture_frame >= self.capture_at_frame)):
            self.save_screenshot()
        pygame.display.flip()

    def save_screenshot(self):
        if self.capture_path:
            path = self.capture_path
        else:
            screenshot_folder = os.path.join(self.folder, "screenshots")
            os.makedirs(screenshot_folder, exist_ok=True)
            path = os.path.join(
                screenshot_folder,
                f"aether-reactor-{pygame.time.get_ticks()}.png"
            )

        folder = os.path.dirname(os.path.abspath(path))
        os.makedirs(folder, exist_ok=True)
        glReadBuffer(GL_BACK)
        pixels = glReadPixels(0, 0, self.width, self.height,
                              GL_RGB, GL_UNSIGNED_BYTE)
        image = pygame.image.fromstring(
            bytes(pixels), (self.width, self.height), "RGB", True
        )
        pygame.image.save(image, path)
        self.pending_screenshot = False
        if self.capture_path:
            self.running = False

    def run(self):
        while self.running:
            delta_time = min(self.clock.tick(120) / 1000.0, 0.04)
            self.handle_events()
            self.update_camera_keys(delta_time)
            if not self.paused:
                self.system.update(delta_time)
            self.draw(self.clock.get_fps())

        pygame.quit()


if __name__ == "__main__":
    AetherReactorApp().run()
