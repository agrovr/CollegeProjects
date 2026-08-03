import math
import os

import pygame
from OpenGL.GL import *
from OpenGL.GLU import gluLookAt, gluPerspective

import maze


_font_cache = {}


def initialize_opengl():
    glClearColor(0.004, 0.007, 0.012, 1.0)
    glClearDepth(1.0)
    glEnable(GL_DEPTH_TEST)
    glDepthFunc(GL_LEQUAL)
    glShadeModel(GL_SMOOTH)
    glEnable(GL_NORMALIZE)

    glEnable(GL_TEXTURE_2D)
    glTexEnvi(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_MODULATE)

    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_LIGHT1)
    glEnable(GL_LIGHT2)
    glEnable(GL_LIGHT3)
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
    glLightModelfv(GL_LIGHT_MODEL_AMBIENT, (0.045, 0.055, 0.075, 1.0))

    glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, (0.28, 0.30, 0.34, 1.0))
    glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 28.0)

    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glEnable(GL_FOG)
    glFogi(GL_FOG_MODE, GL_LINEAR)
    glFogfv(GL_FOG_COLOR, (0.004, 0.007, 0.012, 1.0))
    glFogf(GL_FOG_START, 9.0)
    glFogf(GL_FOG_END, 34.0)

    glHint(GL_PERSPECTIVE_CORRECTION_HINT, GL_NICEST)
    glHint(GL_FOG_HINT, GL_NICEST)

    try:
        glEnable(GL_MULTISAMPLE)
    except Exception:
        pass


def load_texture(filename, repeat=True):
    surface = pygame.image.load(filename).convert_alpha()
    image_data = pygame.image.tostring(surface, "RGBA", True)
    width, height = surface.get_size()

    texture = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texture)
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
    glTexImage2D(
        GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0,
        GL_RGBA, GL_UNSIGNED_BYTE, image_data
    )

    wrap_mode = GL_REPEAT if repeat else GL_CLAMP_TO_EDGE
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, wrap_mode)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, wrap_mode)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

    try:
        glGenerateMipmap(GL_TEXTURE_2D)
        glTexParameteri(
            GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR
        )
    except Exception:
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)

    glBindTexture(GL_TEXTURE_2D, 0)
    return texture


def load_textures(folder):
    return {
        "wall": load_texture(os.path.join(folder, "obsidian_wall.png")),
        "floor": load_texture(os.path.join(folder, "forge_floor.png")),
        "lava": load_texture(os.path.join(folder, "lava.png")),
        "portal": load_texture(
            os.path.join(folder, "portal.png"), repeat=False
        ),
    }


def delete_textures(textures):
    for texture in textures.values():
        glDeleteTextures([texture])


def _set_projection(screen_width, screen_height):
    glViewport(0, 0, screen_width, screen_height)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(70.0, screen_width / float(screen_height), 0.12, 110.0)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()


def set_camera(player_x, player_y, yaw, pitch, overhead,
               maze_data, cell_size, camera_bob=0.0):
    if overhead:
        center_x = maze_data["width"] * cell_size * 0.5
        center_y = maze_data["height"] * cell_size * 0.5
        maze_span = max(maze_data["width"], maze_data["height"]) * cell_size
        height = maze_span * 0.92
        gluLookAt(
            center_x, center_y - 0.01, height,
            center_x, center_y, 0.0,
            0.0, 1.0, 0.0,
        )
    else:
        eye_height = 1.15 + camera_bob
        look_x = math.cos(yaw) * math.cos(pitch)
        look_y = math.sin(yaw) * math.cos(pitch)
        look_z = math.sin(pitch)
        gluLookAt(
            player_x, player_y, eye_height,
            player_x + look_x, player_y + look_y, eye_height + look_z,
            0.0, 0.0, 1.0,
        )


def _set_lights(player_x, player_y, finish_x, finish_y, overhead, time_value,
                brazier_locations):
    flicker = (0.92 + 0.055 * math.sin(time_value * 16.0)
               + 0.025 * math.sin(time_value * 37.0))
    glLightfv(GL_LIGHT0, GL_POSITION, (player_x, player_y, 1.45, 1.0))
    glLightfv(GL_LIGHT0, GL_AMBIENT, (0.035, 0.018, 0.008, 1.0))
    glLightfv(GL_LIGHT0, GL_DIFFUSE,
              (1.0 * flicker, 0.46 * flicker, 0.16 * flicker, 1.0))
    glLightfv(GL_LIGHT0, GL_SPECULAR,
              (1.0 * flicker, 0.55 * flicker, 0.22 * flicker, 1.0))
    glLightf(GL_LIGHT0, GL_CONSTANT_ATTENUATION, 0.42)
    glLightf(GL_LIGHT0, GL_LINEAR_ATTENUATION, 0.055)
    glLightf(GL_LIGHT0, GL_QUADRATIC_ATTENUATION, 0.012)

    glLightfv(GL_LIGHT1, GL_POSITION, (finish_x, finish_y, 1.15, 1.0))
    glLightfv(GL_LIGHT1, GL_AMBIENT, (0.005, 0.022, 0.035, 1.0))
    glLightfv(GL_LIGHT1, GL_DIFFUSE, (0.10, 0.62, 1.0, 1.0))
    glLightfv(GL_LIGHT1, GL_SPECULAR, (0.25, 0.78, 1.0, 1.0))
    glLightf(GL_LIGHT1, GL_CONSTANT_ATTENUATION, 0.34)
    glLightf(GL_LIGHT1, GL_LINEAR_ATTENUATION, 0.075)
    glLightf(GL_LIGHT1, GL_QUADRATIC_ATTENUATION, 0.018)

    closest = sorted(
        brazier_locations,
        key=lambda location: ((location[0] - player_x) ** 2
                              + (location[1] - player_y) ** 2),
    )[:2]
    brazier_lights = (GL_LIGHT2, GL_LIGHT3)
    for light_index, light in enumerate(brazier_lights):
        if overhead or light_index >= len(closest):
            glDisable(light)
            continue

        center_x, center_y, wall = closest[light_index]
        inside_x, inside_y = _wall_inside_direction(wall)
        flicker = (0.88 + 0.08 * math.sin(time_value * 11.0
                                          + light_index * 2.3)
                   + 0.04 * math.sin(time_value * 23.0
                                     + light_index * 1.4))
        glEnable(light)
        glLightfv(
            light, GL_POSITION,
            (center_x + inside_x * 0.30,
             center_y + inside_y * 0.30, 1.42, 1.0),
        )
        glLightfv(light, GL_AMBIENT, (0.025, 0.008, 0.002, 1.0))
        glLightfv(
            light, GL_DIFFUSE,
            (0.92 * flicker, 0.28 * flicker, 0.055 * flicker, 1.0),
        )
        glLightfv(
            light, GL_SPECULAR,
            (0.82 * flicker, 0.35 * flicker, 0.10 * flicker, 1.0),
        )
        glLightf(light, GL_CONSTANT_ATTENUATION, 0.62)
        glLightf(light, GL_LINEAR_ATTENUATION, 0.18)
        glLightf(light, GL_QUADRATIC_ATTENUATION, 0.08)

    if overhead:
        glDisable(GL_FOG)
        glLightModelfv(GL_LIGHT_MODEL_AMBIENT, (0.20, 0.22, 0.27, 1.0))
    else:
        glEnable(GL_FOG)
        glLightModelfv(GL_LIGHT_MODEL_AMBIENT, (0.045, 0.055, 0.075, 1.0))


def _draw_floor(maze_data, texture, cell_size):
    width = maze_data["width"] * cell_size
    height = maze_data["height"] * cell_size

    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture)
    glColor3f(0.82, 0.86, 0.91)
    glBegin(GL_QUADS)
    glNormal3f(0.0, 0.0, 1.0)
    glTexCoord2f(0.0, 0.0)
    glVertex3f(0.0, 0.0, -0.035)
    glTexCoord2f(maze_data["width"], 0.0)
    glVertex3f(width, 0.0, -0.035)
    glTexCoord2f(maze_data["width"], maze_data["height"])
    glVertex3f(width, height, -0.035)
    glTexCoord2f(0.0, maze_data["height"])
    glVertex3f(0.0, height, -0.035)
    glEnd()


def _draw_ceiling(maze_data, texture, cell_size, wall_height):
    width = maze_data["width"] * cell_size
    height = maze_data["height"] * cell_size
    ceiling_z = wall_height + 0.10

    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture)
    glColor3f(0.31, 0.33, 0.38)
    glBegin(GL_QUADS)
    glNormal3f(0.0, 0.0, -1.0)
    glTexCoord2f(0.0, 0.0)
    glVertex3f(0.0, height, ceiling_z)
    glTexCoord2f(maze_data["width"], 0.0)
    glVertex3f(width, height, ceiling_z)
    glTexCoord2f(maze_data["width"], maze_data["height"])
    glVertex3f(width, 0.0, ceiling_z)
    glTexCoord2f(0.0, maze_data["height"])
    glVertex3f(0.0, 0.0, ceiling_z)
    glEnd()


def _draw_box(x1, x2, y1, y2, z1, z2, texture, minimum_repeat=0.05):
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture)
    glColor3f(0.90, 0.91, 0.94)

    repeat_x = max((x2 - x1) / 3.0, minimum_repeat)
    repeat_y = max((y2 - y1) / 3.0, minimum_repeat)

    glBegin(GL_QUADS)
    glNormal3f(0.0, -1.0, 0.0)
    glTexCoord2f(0.0, 0.0); glVertex3f(x1, y1, z1)
    glTexCoord2f(repeat_x, 0.0); glVertex3f(x2, y1, z1)
    glTexCoord2f(repeat_x, 1.0); glVertex3f(x2, y1, z2)
    glTexCoord2f(0.0, 1.0); glVertex3f(x1, y1, z2)

    glNormal3f(0.0, 1.0, 0.0)
    glTexCoord2f(0.0, 0.0); glVertex3f(x2, y2, z1)
    glTexCoord2f(repeat_x, 0.0); glVertex3f(x1, y2, z1)
    glTexCoord2f(repeat_x, 1.0); glVertex3f(x1, y2, z2)
    glTexCoord2f(0.0, 1.0); glVertex3f(x2, y2, z2)

    glNormal3f(-1.0, 0.0, 0.0)
    glTexCoord2f(0.0, 0.0); glVertex3f(x1, y2, z1)
    glTexCoord2f(repeat_y, 0.0); glVertex3f(x1, y1, z1)
    glTexCoord2f(repeat_y, 1.0); glVertex3f(x1, y1, z2)
    glTexCoord2f(0.0, 1.0); glVertex3f(x1, y2, z2)

    glNormal3f(1.0, 0.0, 0.0)
    glTexCoord2f(0.0, 0.0); glVertex3f(x2, y1, z1)
    glTexCoord2f(repeat_y, 0.0); glVertex3f(x2, y2, z1)
    glTexCoord2f(repeat_y, 1.0); glVertex3f(x2, y2, z2)
    glTexCoord2f(0.0, 1.0); glVertex3f(x2, y1, z2)

    glNormal3f(0.0, 0.0, 1.0)
    glTexCoord2f(0.0, 0.0); glVertex3f(x1, y1, z2)
    glTexCoord2f(repeat_x, 0.0); glVertex3f(x2, y1, z2)
    glTexCoord2f(repeat_x, repeat_y); glVertex3f(x2, y2, z2)
    glTexCoord2f(0.0, repeat_y); glVertex3f(x1, y2, z2)
    glEnd()


def _wall_segments(maze_data, cell_size):
    walls = maze_data["walls"]
    width = maze_data["width"]
    height = maze_data["height"]

    for y in range(height):
        for x in range(width):
            x1 = x * cell_size
            x2 = (x + 1) * cell_size
            y1 = y * cell_size
            y2 = (y + 1) * cell_size

            if walls[y][x] & maze.NORTH:
                yield (x1, y1, x2, y1)
            if walls[y][x] & maze.WEST:
                yield (x1, y1, x1, y2)
            if y == height - 1 and walls[y][x] & maze.SOUTH:
                yield (x1, y2, x2, y2)
            if x == width - 1 and walls[y][x] & maze.EAST:
                yield (x2, y1, x2, y2)


def _draw_walls(maze_data, texture, cell_size, wall_height):
    thickness = 0.16
    half = thickness * 0.5

    for x1, y1, x2, y2 in _wall_segments(maze_data, cell_size):
        if y1 == y2:
            _draw_box(
                x1 - half, x2 + half, y1 - half, y1 + half,
                0.0, wall_height, texture
            )
        else:
            _draw_box(
                x1 - half, x1 + half, y1 - half, y2 + half,
                0.0, wall_height, texture
            )


def _draw_ring(radius, z, red, green, blue, alpha=1.0, segments=40):
    glColor4f(red, green, blue, alpha)
    glBegin(GL_LINE_LOOP)
    for index in range(segments):
        angle = index * 2.0 * math.pi / segments
        glVertex3f(math.cos(angle) * radius, math.sin(angle) * radius, z)
    glEnd()


def _draw_sphere(radius, slices=16, stacks=9):
    for stack in range(stacks):
        lower = -math.pi / 2.0 + stack * math.pi / stacks
        upper = -math.pi / 2.0 + (stack + 1) * math.pi / stacks
        glBegin(GL_QUAD_STRIP)
        for index in range(slices + 1):
            angle = index * 2.0 * math.pi / slices
            for latitude in (upper, lower):
                nx = math.cos(latitude) * math.cos(angle)
                ny = math.cos(latitude) * math.sin(angle)
                nz = math.sin(latitude)
                glNormal3f(nx, ny, nz)
                glVertex3f(nx * radius, ny * radius, nz * radius)
        glEnd()


def _draw_octahedron(radius):
    top = (0.0, 0.0, radius)
    bottom = (0.0, 0.0, -radius)
    middle = ((radius, 0.0, 0.0), (0.0, radius, 0.0),
              (-radius, 0.0, 0.0), (0.0, -radius, 0.0))

    glBegin(GL_TRIANGLES)
    for index in range(4):
        first = middle[index]
        second = middle[(index + 1) % 4]
        glColor4f(0.20 + index * 0.04, 0.84, 1.0, 0.92)
        glVertex3fv(top); glVertex3fv(first); glVertex3fv(second)
        glColor4f(0.08, 0.38 + index * 0.06, 0.82, 0.92)
        glVertex3fv(bottom); glVertex3fv(second); glVertex3fv(first)
    glEnd()


def _begin_glow():
    glDisable(GL_LIGHTING)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE)
    glDepthMask(GL_FALSE)


def _end_glow():
    glDepthMask(GL_TRUE)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glEnable(GL_LIGHTING)


def _draw_lava(cell, texture, cell_size, time_value):
    center_x, center_y = maze.cell_center(cell, cell_size)
    half = cell_size * 0.32

    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture)
    glDisable(GL_LIGHTING)
    glColor4f(1.0, 0.58, 0.25, 0.96)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(center_x - half, center_y - half, 0.012)
    glTexCoord2f(1.0, 0.0); glVertex3f(center_x + half, center_y - half, 0.012)
    glTexCoord2f(1.0, 1.0); glVertex3f(center_x + half, center_y + half, 0.012)
    glTexCoord2f(0.0, 1.0); glVertex3f(center_x - half, center_y + half, 0.012)
    glEnd()

    glDisable(GL_TEXTURE_2D)
    _begin_glow()
    glPushMatrix()
    glTranslatef(center_x, center_y, 0.0)
    glLineWidth(2.0)
    pulse = 0.92 + 0.08 * math.sin(time_value * 3.2)
    _draw_ring(half * pulse, 0.025, 1.0, 0.22, 0.03, 0.82)

    glPointSize(4.0)
    glBegin(GL_POINTS)
    for index in range(11):
        angle = index * 2.399 + time_value * (0.35 + index * 0.015)
        distance = half * (0.2 + (index % 5) * 0.14)
        height = 0.10 + ((time_value * 0.55 + index * 0.17) % 1.0) * 1.05
        glColor4f(1.0, 0.22 + (index % 3) * 0.12, 0.03, 0.72)
        glVertex3f(math.cos(angle) * distance,
                   math.sin(angle) * distance, height)
    glEnd()
    glPopMatrix()
    _end_glow()
    glEnable(GL_TEXTURE_2D)


def _draw_speed(cell, cell_size, time_value):
    center_x, center_y = maze.cell_center(cell, cell_size)
    glDisable(GL_TEXTURE_2D)
    _begin_glow()
    glPushMatrix()
    glTranslatef(center_x, center_y, 0.67 + 0.08 * math.sin(time_value * 3.0))
    glRotatef(time_value * 80.0, 0.0, 0.0, 1.0)
    _draw_octahedron(0.40)
    glLineWidth(2.0)
    _draw_ring(0.56, -0.56, 0.05, 0.76, 1.0, 0.58)
    _draw_ring(0.38, -0.50 + 0.08 * math.sin(time_value * 2.0),
               0.24, 0.92, 1.0, 0.70)
    glPopMatrix()
    _end_glow()
    glEnable(GL_TEXTURE_2D)


def _draw_eye(cell, cell_size, time_value):
    center_x, center_y = maze.cell_center(cell, cell_size)
    glDisable(GL_TEXTURE_2D)
    _begin_glow()
    glPushMatrix()
    glTranslatef(center_x, center_y, 0.58 + 0.07 * math.sin(time_value * 2.4))
    glColor4f(0.10, 1.0, 0.67, 0.90)
    _draw_sphere(0.25, 16, 8)
    glColor4f(0.22, 0.55, 1.0, 0.96)
    glPushMatrix()
    glScalef(1.0, 0.28, 1.0)
    _draw_sphere(0.31, 16, 8)
    glPopMatrix()
    glLineWidth(2.0)
    glRotatef(76.0, 1.0, 0.0, 0.0)
    _draw_ring(0.47, 0.0, 0.18, 1.0, 0.72, 0.66)
    glPopMatrix()
    _end_glow()
    glEnable(GL_TEXTURE_2D)


def _draw_lift(cell, cell_size, time_value):
    center_x, center_y = maze.cell_center(cell, cell_size)
    glDisable(GL_TEXTURE_2D)
    _begin_glow()
    glPushMatrix()
    glTranslatef(center_x, center_y, 0.0)

    for index in range(4):
        height = ((time_value * 0.72 + index * 0.25) % 1.0) * 2.25
        radius = 0.56 - height * 0.09
        glLineWidth(2.2)
        _draw_ring(max(0.22, radius), 0.06 + height,
                   0.58, 0.24, 1.0, 0.64 - height * 0.16)

    glColor4f(0.34, 0.12, 1.0, 0.16)
    glBegin(GL_QUADS)
    glVertex3f(-0.48, 0.0, 0.02); glVertex3f(0.48, 0.0, 0.02)
    glVertex3f(0.22, 0.0, 2.3); glVertex3f(-0.22, 0.0, 2.3)
    glVertex3f(0.0, -0.48, 0.02); glVertex3f(0.0, 0.48, 0.02)
    glVertex3f(0.0, 0.22, 2.3); glVertex3f(0.0, -0.22, 2.3)
    glEnd()
    glPopMatrix()
    _end_glow()
    glEnable(GL_TEXTURE_2D)


def _draw_turn(cell, cell_size, time_value):
    center_x, center_y = maze.cell_center(cell, cell_size)
    glDisable(GL_TEXTURE_2D)
    _begin_glow()
    glPushMatrix()
    glTranslatef(center_x, center_y, 0.025)
    glRotatef(time_value * 25.0, 0.0, 0.0, 1.0)
    glLineWidth(3.0)
    _draw_ring(0.58, 0.0, 1.0, 0.72, 0.08, 0.72, 32)

    glColor4f(1.0, 0.82, 0.16, 0.84)
    glBegin(GL_LINE_STRIP)
    for index in range(18):
        angle = -0.25 + index * 1.65 * math.pi / 17.0
        glVertex3f(math.cos(angle) * 0.39, math.sin(angle) * 0.39, 0.02)
    glEnd()
    glBegin(GL_TRIANGLES)
    glVertex3f(-0.06, 0.38, 0.02)
    glVertex3f(0.16, 0.52, 0.02)
    glVertex3f(0.18, 0.26, 0.02)
    glEnd()
    glPopMatrix()
    _end_glow()
    glEnable(GL_TEXTURE_2D)


def _draw_curse(cell, cell_size, time_value):
    center_x, center_y = maze.cell_center(cell, cell_size)
    glDisable(GL_TEXTURE_2D)
    _begin_glow()
    glPushMatrix()
    glTranslatef(center_x, center_y, 0.026)
    glRotatef(-time_value * 18.0, 0.0, 0.0, 1.0)
    glLineWidth(2.5)
    _draw_ring(0.61, 0.0, 1.0, 0.06, 0.20, 0.70, 36)
    _draw_ring(0.34, 0.01, 0.72, 0.08, 1.0, 0.58, 24)

    glColor4f(1.0, 0.08, 0.25, 0.72)
    glBegin(GL_LINES)
    for index in range(8):
        angle = index * math.pi / 4.0
        glVertex3f(math.cos(angle) * 0.18, math.sin(angle) * 0.18, 0.015)
        glVertex3f(math.cos(angle) * 0.72, math.sin(angle) * 0.72, 0.015)
    glEnd()
    glPopMatrix()
    _end_glow()
    glEnable(GL_TEXTURE_2D)


def _draw_feature_beacon(cell, feature, cell_size, time_value):
    colors = {
        "lava": (1.0, 0.16, 0.02),
        "speed": (0.08, 0.76, 1.0),
        "eye": (0.16, 1.0, 0.66),
        "lift": (0.58, 0.24, 1.0),
        "turn": (1.0, 0.72, 0.08),
        "curse": (1.0, 0.05, 0.24),
    }
    red, green, blue = colors[feature]
    center_x, center_y = maze.cell_center(cell, cell_size)
    collectible = feature in ("speed", "eye", "lift")
    pulse = 0.78 + 0.08 * math.sin(time_value * 2.8 + center_x + center_y)

    glDisable(GL_TEXTURE_2D)
    _begin_glow()
    glPushMatrix()
    glTranslatef(center_x, center_y, 0.0)

    _draw_ring(0.72 * pulse, 0.018, red, green, blue, 0.30, 36)
    _draw_ring(0.49, 0.024, red, green, blue, 0.16, 28)

    if collectible:
        glColor4f(red, green, blue, 0.055)
        glBegin(GL_QUADS)
        glVertex3f(-0.18, 0.0, 0.03); glVertex3f(0.18, 0.0, 0.03)
        glVertex3f(0.10, 0.0, 1.45); glVertex3f(-0.10, 0.0, 1.45)
        glVertex3f(0.0, -0.18, 0.03); glVertex3f(0.0, 0.18, 0.03)
        glVertex3f(0.0, 0.10, 1.45); glVertex3f(0.0, -0.10, 1.45)
        glEnd()

    glPointSize(3.0)
    glBegin(GL_POINTS)
    for particle in range(12):
        progress = (time_value * 0.38 + particle / 12.0) % 1.0
        angle = particle * 2.399 + time_value * 0.55
        radius = 0.34 + (particle % 3) * 0.11
        alpha = 0.58 * (1.0 - progress)
        glColor4f(red, green, blue, alpha)
        glVertex3f(math.cos(angle) * radius,
                   math.sin(angle) * radius,
                   0.08 + progress * 1.28)
    glEnd()

    glPopMatrix()
    _end_glow()
    glEnable(GL_TEXTURE_2D)


def _draw_features(maze_data, textures, cell_size, time_value, collected):
    for cell, feature in maze_data["features"].items():
        if cell in collected and feature in ("speed", "eye", "lift"):
            continue

        _draw_feature_beacon(cell, feature, cell_size, time_value)
        if feature == "lava":
            _draw_lava(cell, textures["lava"], cell_size, time_value)
        elif feature == "speed":
            _draw_speed(cell, cell_size, time_value)
        elif feature == "eye":
            _draw_eye(cell, cell_size, time_value)
        elif feature == "lift":
            _draw_lift(cell, cell_size, time_value)
        elif feature == "turn":
            _draw_turn(cell, cell_size, time_value)
        elif feature == "curse":
            _draw_curse(cell, cell_size, time_value)


def _brazier_locations(maze_data, cell_size):
    walls = maze_data["walls"]
    blocked = set(maze_data["features"])
    blocked.add(maze_data["start"])
    blocked.add(maze_data["finish"])

    candidates = list(maze_data["path"][7:-5:12])
    dead_ends = []
    for y in range(maze_data["height"]):
        for x in range(maze_data["width"]):
            cell = (x, y)
            if (cell not in blocked
                    and len(maze.open_neighbors(walls, cell)) == 1):
                dead_ends.append(cell)
    dead_ends.sort(key=lambda cell: maze_data["distances"][cell], reverse=True)
    candidates.extend(dead_ends[:5])

    locations = []
    used = set()
    for cell in candidates:
        if cell in blocked or cell in used:
            continue
        used.add(cell)
        x, y = cell
        available_walls = [
            wall for wall in (maze.NORTH, maze.EAST, maze.SOUTH, maze.WEST)
            if walls[y][x] & wall
        ]
        if not available_walls:
            continue
        wall = available_walls[(x * 3 + y * 5) % len(available_walls)]
        center_x, center_y = maze.cell_center(cell, cell_size)
        inset = 0.20
        if wall == maze.NORTH:
            center_y = y * cell_size + inset
        elif wall == maze.SOUTH:
            center_y = (y + 1) * cell_size - inset
        elif wall == maze.WEST:
            center_x = x * cell_size + inset
        else:
            center_x = (x + 1) * cell_size - inset
        locations.append((center_x, center_y, wall))
    return locations[:6]


def _wall_inside_direction(wall):
    if wall == maze.NORTH:
        return 0.0, 1.0
    if wall == maze.SOUTH:
        return 0.0, -1.0
    if wall == maze.WEST:
        return 1.0, 0.0
    return -1.0, 0.0


def _draw_brazier_light_pool(center_x, center_y, wall, time_value, index):
    inside_x, inside_y = _wall_inside_direction(wall)
    side_x = -inside_y
    side_y = inside_x
    pool_x = center_x + inside_x * 0.48
    pool_y = center_y + inside_y * 0.48
    pulse = 0.15 + 0.025 * math.sin(time_value * 10.0 + index * 1.7)

    glDisable(GL_TEXTURE_2D)
    _begin_glow()
    glBegin(GL_TRIANGLE_FAN)
    glColor4f(1.0, 0.22, 0.025, pulse)
    glVertex3f(pool_x, pool_y, 0.012)
    for point in range(25):
        angle = point * 2.0 * math.pi / 24.0
        along = math.cos(angle) * 1.00
        across = math.sin(angle) * 0.78
        glColor4f(0.78, 0.055, 0.008, 0.0)
        glVertex3f(
            pool_x + inside_x * along + side_x * across,
            pool_y + inside_y * along + side_y * across,
            0.012,
        )
    glEnd()
    _end_glow()
    glEnable(GL_TEXTURE_2D)


def _draw_brazier_bowl(center_x, center_y):
    glDisable(GL_TEXTURE_2D)
    glColor3f(0.24, 0.14, 0.09)
    glBegin(GL_QUAD_STRIP)
    for index in range(9):
        angle = index * 2.0 * math.pi / 8.0
        normal_x = math.cos(angle)
        normal_y = math.sin(angle)
        glNormal3f(normal_x, normal_y, 0.28)
        glVertex3f(center_x + normal_x * 0.13,
                   center_y + normal_y * 0.13, 1.02)
        glVertex3f(center_x + normal_x * 0.24,
                   center_y + normal_y * 0.24, 1.19)
    glEnd()

    glDisable(GL_LIGHTING)
    glColor4f(0.72, 0.30, 0.10, 0.88)
    glLineWidth(2.0)
    glBegin(GL_LINE_LOOP)
    for index in range(8):
        angle = index * 2.0 * math.pi / 8.0
        glVertex3f(center_x + math.cos(angle) * 0.24,
                   center_y + math.sin(angle) * 0.24, 1.19)
    glEnd()
    glEnable(GL_LIGHTING)


def _draw_braziers(brazier_locations, time_value):
    for index, (center_x, center_y, wall) in enumerate(brazier_locations):
        _draw_brazier_light_pool(
            center_x, center_y, wall, time_value, index
        )
        _draw_brazier_bowl(center_x, center_y)

        pulse = 1.0 + 0.10 * math.sin(time_value * 9.0 + index * 1.7)
        glDisable(GL_TEXTURE_2D)
        _begin_glow()
        glPushMatrix()
        glTranslatef(center_x, center_y, 1.22)

        for angle in (0.0, 90.0):
            glPushMatrix()
            glRotatef(angle, 0.0, 0.0, 1.0)
            glColor4f(1.0, 0.12, 0.015, 0.24)
            glBegin(GL_TRIANGLES)
            glVertex3f(-0.17 * pulse, 0.0, 0.0)
            glVertex3f(0.17 * pulse, 0.0, 0.0)
            glVertex3f(0.02, 0.0, 0.62 * pulse)
            glEnd()
            glColor4f(1.0, 0.68, 0.08, 0.46)
            glBegin(GL_TRIANGLES)
            glVertex3f(-0.08 * pulse, -0.002, 0.0)
            glVertex3f(0.08 * pulse, -0.002, 0.0)
            glVertex3f(-0.02, -0.002, 0.39 * pulse)
            glEnd()
            glPopMatrix()

        glPointSize(3.0)
        glBegin(GL_POINTS)
        for spark in range(4):
            height = ((time_value * 0.55 + spark * 0.27 + index * 0.13) % 1.0)
            glColor4f(1.0, 0.30 + spark * 0.10, 0.04, 0.68 - height * 0.42)
            glVertex3f(math.sin(index * 2.1 + spark) * 0.10,
                       math.cos(index + spark * 1.8) * 0.10,
                       0.28 + height * 0.72)
        glEnd()
        glPopMatrix()
        _end_glow()
        glEnable(GL_TEXTURE_2D)


def _draw_ambient_embers(maze_data, cell_size, time_value):
    width = maze_data["width"] * cell_size
    height = maze_data["height"] * cell_size

    glDisable(GL_TEXTURE_2D)
    _begin_glow()
    glPointSize(2.5)
    glBegin(GL_POINTS)
    for index in range(90):
        base_x = ((index * 47) % 109) / 109.0 * width
        base_y = ((index * 71 + 13) % 113) / 113.0 * height
        drift = time_value * (0.045 + (index % 7) * 0.004)
        ember_x = base_x + math.sin(time_value * 0.37 + index) * 0.18
        ember_y = base_y + math.cos(time_value * 0.29 + index * 1.7) * 0.18
        ember_z = 0.18 + ((index * 0.173 + drift) % 1.0) * 2.45
        brightness = 0.46 + (index % 5) * 0.08
        glColor4f(1.0, 0.16 + (index % 4) * 0.07, 0.025, brightness)
        glVertex3f(ember_x, ember_y, ember_z)
    glEnd()
    _end_glow()
    glEnable(GL_TEXTURE_2D)


def _draw_start_seal(cell, cell_size, time_value):
    center_x, center_y = maze.cell_center(cell, cell_size)
    glDisable(GL_TEXTURE_2D)
    _begin_glow()
    glPushMatrix()
    glTranslatef(center_x, center_y, 0.018)
    glLineWidth(2.0)
    pulse = 0.94 + 0.04 * math.sin(time_value * 2.2)
    _draw_ring(0.76 * pulse, 0.0, 1.0, 0.31, 0.04, 0.52, 32)
    _draw_ring(0.48, 0.006, 0.22, 0.76, 1.0, 0.42, 24)
    glColor4f(1.0, 0.42, 0.08, 0.52)
    glBegin(GL_LINES)
    for index in range(4):
        angle = index * math.pi / 2.0 + math.pi / 4.0
        glVertex3f(math.cos(angle) * 0.28, math.sin(angle) * 0.28, 0.01)
        glVertex3f(math.cos(angle) * 0.66, math.sin(angle) * 0.66, 0.01)
    glEnd()
    glPopMatrix()
    _end_glow()
    glEnable(GL_TEXTURE_2D)


def _draw_portal_arch(maze_data, texture, cell_size, time_value):
    finish = maze_data["finish"]
    center_x, center_y = maze.cell_center(finish, cell_size)
    previous = maze_data["path"][-2]
    direction_x = finish[0] - previous[0]
    direction_y = finish[1] - previous[1]
    direction_angle = math.degrees(math.atan2(direction_y, direction_x)) - 90.0

    glPushMatrix()
    glTranslatef(center_x, center_y, 0.0)
    glRotatef(direction_angle, 0.0, 0.0, 1.0)
    _draw_box(-1.03, -0.72, -0.24, 0.24, 0.0, 2.48, texture, 1.0)
    _draw_box(0.72, 1.03, -0.24, 0.24, 0.0, 2.48, texture, 1.0)
    _draw_box(-1.03, 1.03, -0.24, 0.24, 2.25, 2.60, texture, 1.0)

    glDisable(GL_TEXTURE_2D)
    _begin_glow()
    glLineWidth(2.2)
    pulse = 0.55 + 0.12 * math.sin(time_value * 3.0)
    glColor4f(0.12, 0.76, 1.0, pulse)
    glBegin(GL_LINES)
    for side in (-1.0, 1.0):
        glVertex3f(side * 0.86, -0.255, 0.28)
        glVertex3f(side * 0.86, -0.255, 2.25)
    glVertex3f(-0.72, -0.255, 2.40)
    glVertex3f(0.72, -0.255, 2.40)
    glEnd()
    _end_glow()
    glEnable(GL_TEXTURE_2D)
    glPopMatrix()


def _draw_portal(cell, texture, cell_size, time_value):
    center_x, center_y = maze.cell_center(cell, cell_size)
    width = 1.48 + 0.05 * math.sin(time_value * 2.8)
    height = 2.30

    _begin_glow()
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture)
    glPushMatrix()
    glTranslatef(center_x, center_y, 0.06)
    glRotatef(time_value * 16.0, 0.0, 0.0, 1.0)

    for angle in (0.0, 45.0, 90.0, 135.0):
        glPushMatrix()
        glRotatef(angle, 0.0, 0.0, 1.0)
        glColor4f(0.60, 0.92, 1.0, 0.62)
        glBegin(GL_QUADS)
        glTexCoord2f(0.0, 0.0); glVertex3f(-width * 0.5, 0.0, 0.0)
        glTexCoord2f(1.0, 0.0); glVertex3f(width * 0.5, 0.0, 0.0)
        glTexCoord2f(1.0, 1.0); glVertex3f(width * 0.5, 0.0, height)
        glTexCoord2f(0.0, 1.0); glVertex3f(-width * 0.5, 0.0, height)
        glEnd()
        glPopMatrix()

    glDisable(GL_TEXTURE_2D)
    glLineWidth(2.5)
    for index in range(3):
        radius = 0.55 + index * 0.18
        _draw_ring(radius, 0.03 + index * 0.015,
                   0.10 + index * 0.10, 0.62, 1.0, 0.62 - index * 0.12)

    glPointSize(4.0)
    glBegin(GL_POINTS)
    for index in range(22):
        angle = index * 2.399 + time_value * (0.34 + index * 0.006)
        radius = 0.64 + (index % 4) * 0.10
        height_value = 0.15 + ((index * 0.23 + time_value * 0.32) % 1.0) * 2.0
        glColor4f(0.18, 0.65 + (index % 3) * 0.10, 1.0, 0.78)
        glVertex3f(math.cos(angle) * radius,
                   math.sin(angle) * radius, height_value)
    glEnd()
    glPopMatrix()
    _end_glow()
    glEnable(GL_TEXTURE_2D)


def draw_world(maze_data, textures, player_x, player_y, yaw, pitch,
               cell_size, wall_height, time_value, collected,
               overhead, screen_width, screen_height, camera_bob=0.0):
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    _set_projection(screen_width, screen_height)
    set_camera(player_x, player_y, yaw, pitch, overhead, maze_data, cell_size,
               camera_bob)

    finish_x, finish_y = maze.cell_center(maze_data["finish"], cell_size)
    brazier_locations = _brazier_locations(maze_data, cell_size)
    _set_lights(
        player_x, player_y, finish_x, finish_y, overhead, time_value,
        brazier_locations,
    )

    glEnable(GL_LIGHTING)
    glEnable(GL_TEXTURE_2D)
    _draw_floor(maze_data, textures["floor"], cell_size)
    if not overhead:
        _draw_ceiling(
            maze_data, textures["floor"], cell_size, wall_height
        )
    _draw_walls(maze_data, textures["wall"], cell_size, wall_height)
    _draw_braziers(brazier_locations, time_value)
    _draw_start_seal(maze_data["start"], cell_size, time_value)
    _draw_features(maze_data, textures, cell_size, time_value, collected)
    _draw_portal_arch(maze_data, textures["wall"], cell_size, time_value)
    _draw_portal(maze_data["finish"], textures["portal"], cell_size, time_value)
    if not overhead:
        _draw_ambient_embers(maze_data, cell_size, time_value)


def _begin_2d(screen_width, screen_height):
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    glOrtho(0.0, screen_width, screen_height, 0.0, -1.0, 1.0)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    glDisable(GL_DEPTH_TEST)
    glDisable(GL_LIGHTING)
    glDisable(GL_FOG)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)


def _end_2d():
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)
    glEnable(GL_FOG)
    glMatrixMode(GL_MODELVIEW)
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)


def _panel(x, y, width, height, border_color):
    glDisable(GL_TEXTURE_2D)
    glColor4f(0.01, 0.018, 0.030, 0.84)
    glBegin(GL_QUADS)
    glVertex2f(x, y); glVertex2f(x + width, y)
    glVertex2f(x + width, y + height); glVertex2f(x, y + height)
    glEnd()

    glColor4f(*border_color)
    glLineWidth(1.5)
    glBegin(GL_LINE_LOOP)
    glVertex2f(x, y); glVertex2f(x + width, y)
    glVertex2f(x + width, y + height); glVertex2f(x, y + height)
    glEnd()


def _font(size, bold=False):
    key = (size, bold)
    if key not in _font_cache:
        _font_cache[key] = pygame.font.SysFont(
            "consolas", size, bold=bold
        )
    return _font_cache[key]


def _draw_text(x, y, text, size, color, bold=False):
    surface = _font(size, bold).render(text, True, color)
    width, height = surface.get_size()
    pixels = pygame.image.tostring(surface, "RGBA", True)

    texture = glGenTextures(1)
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
    glTexImage2D(
        GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0,
        GL_RGBA, GL_UNSIGNED_BYTE, pixels
    )

    glColor4f(1.0, 1.0, 1.0, 1.0)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 1.0); glVertex2f(x, y)
    glTexCoord2f(1.0, 1.0); glVertex2f(x + width, y)
    glTexCoord2f(1.0, 0.0); glVertex2f(x + width, y + height)
    glTexCoord2f(0.0, 0.0); glVertex2f(x, y + height)
    glEnd()

    glDeleteTextures([texture])
    return width, height


def _format_time(seconds):
    minutes = int(seconds // 60)
    remaining = seconds - minutes * 60
    return f"{minutes:02d}:{remaining:04.1f}"


def _escape_rank(seconds):
    if seconds < 90.0:
        return "PHOENIX"
    if seconds < 180.0:
        return "RIFT RUNNER"
    return "VAULT BREAKER"


def _draw_minimap(maze_data, player_x, player_y, yaw,
                   screen_width, screen_height, cell_size):
    ui_scale = max(0.85, min(1.5, screen_height / 720.0))
    panel_size = min(int(278 * ui_scale), int(screen_width * 0.21))
    panel_x = screen_width - panel_size - int(22 * ui_scale)
    panel_y = int(22 * ui_scale)
    title_height = int(32 * ui_scale)
    _panel(panel_x, panel_y, panel_size, panel_size + title_height,
           (0.08, 0.78, 1.0, 0.82))
    _draw_text(panel_x + int(13 * ui_scale),
               panel_y + int(8 * ui_scale),
               "PHOENIX SIGHT", int(17 * ui_scale),
               (106, 224, 255), True)

    inset = int(14 * ui_scale)
    map_x = panel_x + inset
    map_y = panel_y + int(34 * ui_scale)
    map_size = panel_size - inset * 2
    scale = map_size / float(max(maze_data["width"], maze_data["height"]))

    glDisable(GL_TEXTURE_2D)

    glColor4f(0.05, 0.78, 1.0, 0.38)
    glLineWidth(max(2.0, scale * 0.10))
    glBegin(GL_LINE_STRIP)
    for cell_x, cell_y in maze_data["path"]:
        glVertex2f(map_x + (cell_x + 0.5) * scale,
                   map_y + (cell_y + 0.5) * scale)
    glEnd()

    glColor4f(0.90, 0.48, 0.18, 0.92)
    glLineWidth(max(1.0, scale * 0.07))
    for x1, y1, x2, y2 in _wall_segments(maze_data, 1.0):
        glBegin(GL_LINES)
        glVertex2f(map_x + x1 * scale, map_y + y1 * scale)
        glVertex2f(map_x + x2 * scale, map_y + y2 * scale)
        glEnd()

    finish_x, finish_y = maze_data["finish"]
    marker_x = map_x + (finish_x + 0.5) * scale
    marker_y = map_y + (finish_y + 0.5) * scale
    marker = max(3.0, scale * 0.24)
    glColor4f(0.64, 0.22, 1.0, 1.0)
    glBegin(GL_QUADS)
    glVertex2f(marker_x, marker_y - marker)
    glVertex2f(marker_x + marker, marker_y)
    glVertex2f(marker_x, marker_y + marker)
    glVertex2f(marker_x - marker, marker_y)
    glEnd()

    map_player_x = map_x + (player_x / cell_size) * scale
    map_player_y = map_y + (player_y / cell_size) * scale
    direction_x = math.cos(yaw)
    direction_y = math.sin(yaw)
    side_x = -direction_y
    side_y = direction_x
    arrow = max(4.5, scale * 0.30)
    glColor4f(0.18, 1.0, 0.72, 1.0)
    glBegin(GL_TRIANGLES)
    glVertex2f(map_player_x + direction_x * arrow,
               map_player_y + direction_y * arrow)
    glVertex2f(map_player_x - direction_x * arrow * 0.55 + side_x * arrow * 0.55,
               map_player_y - direction_y * arrow * 0.55 + side_y * arrow * 0.55)
    glVertex2f(map_player_x - direction_x * arrow * 0.55 - side_x * arrow * 0.55,
               map_player_y - direction_y * arrow * 0.55 - side_y * arrow * 0.55)
    glEnd()


def _draw_status_effect(status, screen_width, screen_height, time_value, ui_scale):
    colors = {
        "HASTE": (0.12, 0.78, 1.0),
        "SLOWED": (1.0, 0.22, 0.04),
        "PHOENIX SIGHT": (0.18, 1.0, 0.68),
        "ASCENDING": (0.58, 0.24, 1.0),
    }
    if status not in colors:
        return

    red, green, blue = colors[status]
    pulse = 0.07 + 0.025 * math.sin(time_value * 4.0)
    edge = 13.0 * ui_scale
    glDisable(GL_TEXTURE_2D)
    glColor4f(red, green, blue, pulse)
    glBegin(GL_QUADS)
    glVertex2f(0, 0); glVertex2f(screen_width, 0)
    glVertex2f(screen_width, edge); glVertex2f(0, edge)
    glVertex2f(0, screen_height - edge); glVertex2f(screen_width, screen_height - edge)
    glVertex2f(screen_width, screen_height); glVertex2f(0, screen_height)
    glVertex2f(0, edge); glVertex2f(edge, edge)
    glVertex2f(edge, screen_height - edge); glVertex2f(0, screen_height - edge)
    glVertex2f(screen_width - edge, edge); glVertex2f(screen_width, edge)
    glVertex2f(screen_width, screen_height - edge)
    glVertex2f(screen_width - edge, screen_height - edge)
    glEnd()

    glColor4f(red, green, blue, 0.26)
    glLineWidth(1.7)
    if status == "HASTE":
        glBegin(GL_LINES)
        for index in range(9):
            y = (index + 0.5) * screen_height / 9.0
            length = (26 + (index % 3) * 14) * ui_scale
            glVertex2f(0, y); glVertex2f(length, y - 6 * ui_scale)
            glVertex2f(screen_width, y)
            glVertex2f(screen_width - length, y - 6 * ui_scale)
        glEnd()
    elif status == "PHOENIX SIGHT":
        corner = 38 * ui_scale
        inset = 17 * ui_scale
        glBegin(GL_LINES)
        for x_sign, y_sign in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
            x = inset if x_sign == 1 else screen_width - inset
            y = inset if y_sign == 1 else screen_height - inset
            glVertex2f(x, y); glVertex2f(x + x_sign * corner, y)
            glVertex2f(x, y); glVertex2f(x, y + y_sign * corner)
        glEnd()
    elif status == "ASCENDING":
        glBegin(GL_LINES)
        for index in range(8):
            x = (index + 1) * screen_width / 9.0
            offset = ((time_value * 70 + index * 31) % 80) * ui_scale
            glVertex2f(x, screen_height - offset)
            glVertex2f(x, screen_height - offset - 42 * ui_scale)
        glEnd()


def _draw_vignette(screen_width, screen_height, time_value):
    edge = min(screen_width, screen_height) * 0.15
    pulse = 0.015 * (1.0 + math.sin(time_value * 1.7))

    glDisable(GL_TEXTURE_2D)
    glBegin(GL_QUADS)

    glColor4f(0.0, 0.0, 0.0, 0.24)
    glVertex2f(0, 0); glVertex2f(screen_width, 0)
    glColor4f(0.0, 0.0, 0.0, 0.0)
    glVertex2f(screen_width, edge); glVertex2f(0, edge)

    glColor4f(0.0, 0.0, 0.0, 0.0)
    glVertex2f(0, screen_height - edge)
    glVertex2f(screen_width, screen_height - edge)
    glColor4f(0.16, 0.025, 0.0, 0.16 + pulse)
    glVertex2f(screen_width, screen_height); glVertex2f(0, screen_height)

    glColor4f(0.0, 0.0, 0.0, 0.25)
    glVertex2f(0, 0); glColor4f(0.0, 0.0, 0.0, 0.0)
    glVertex2f(edge, 0); glVertex2f(edge, screen_height)
    glColor4f(0.0, 0.0, 0.0, 0.25)
    glVertex2f(0, screen_height)

    glColor4f(0.0, 0.0, 0.0, 0.0)
    glVertex2f(screen_width - edge, 0)
    glColor4f(0.0, 0.0, 0.0, 0.25)
    glVertex2f(screen_width, 0); glVertex2f(screen_width, screen_height)
    glColor4f(0.0, 0.0, 0.0, 0.0)
    glVertex2f(screen_width - edge, screen_height)
    glEnd()


def _draw_victory_effect(screen_width, screen_height, time_value, ui_scale):
    center_x = screen_width * 0.5
    center_y = screen_height * 0.5
    travel = 260.0 * ui_scale

    glDisable(GL_TEXTURE_2D)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE)
    for ring in range(3):
        phase = (time_value * 55.0 + ring * travel / 3.0) % travel
        radius = 65.0 * ui_scale + phase
        alpha = 0.34 * (1.0 - phase / travel)
        glColor4f(0.08, 0.72, 1.0, alpha)
        glLineWidth(1.5 + ring * 0.4)
        glBegin(GL_LINE_LOOP)
        for point in range(64):
            angle = point * 2.0 * math.pi / 64.0
            glVertex2f(center_x + math.cos(angle) * radius,
                       center_y + math.sin(angle) * radius * 0.48)
        glEnd()

    glPointSize(max(2.0, 3.5 * ui_scale))
    glBegin(GL_POINTS)
    for spark in range(36):
        angle = spark * 2.399 + time_value * 0.18
        radius = (85.0 + (spark % 7) * 34.0) * ui_scale
        if spark % 4 == 0:
            glColor4f(1.0, 0.28, 0.04, 0.48)
        else:
            glColor4f(0.20, 0.76, 1.0, 0.48)
        glVertex2f(center_x + math.cos(angle) * radius,
                   center_y + math.sin(angle) * radius * 0.55)
    glEnd()
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)


def _draw_victory_panel(elapsed, screen_width, screen_height,
                        time_value, ui_scale):
    _draw_victory_effect(screen_width, screen_height, time_value, ui_scale)
    box_width = min(int(610 * ui_scale),
                    screen_width - int(60 * ui_scale))
    box_height = int(230 * ui_scale)
    box_x = (screen_width - box_width) * 0.5
    box_y = (screen_height - box_height) * 0.5
    _panel(box_x, box_y, box_width, box_height,
           (0.16, 0.82, 1.0, 0.95))

    title_size = int(34 * ui_scale)
    title_width = _font(title_size, True).size("RIFT SEALED")[0]
    _draw_text(box_x + (box_width - title_width) * 0.5,
               box_y + int(20 * ui_scale), "RIFT SEALED", title_size,
               (104, 224, 255), True)

    subtitle = "YOU ESCAPED THE SHIFTING FORGE"
    subtitle_size = int(16 * ui_scale)
    subtitle_width = _font(subtitle_size, True).size(subtitle)[0]
    _draw_text(box_x + (box_width - subtitle_width) * 0.5,
               box_y + int(67 * ui_scale), subtitle, subtitle_size,
               (255, 151, 65), True)

    result = f"ESCAPE TIME  {_format_time(elapsed)}"
    result_size = int(21 * ui_scale)
    result_width = _font(result_size, True).size(result)[0]
    _draw_text(box_x + (box_width - result_width) * 0.5,
               box_y + int(105 * ui_scale), result, result_size,
               (238, 241, 245), True)

    rank = f"FORGE RANK  {_escape_rank(elapsed)}"
    rank_size = int(18 * ui_scale)
    rank_width = _font(rank_size, True).size(rank)[0]
    _draw_text(box_x + (box_width - rank_width) * 0.5,
               box_y + int(143 * ui_scale), rank, rank_size,
               (255, 206, 83), True)

    footer = "R replay this vault  |  N generate a new vault"
    footer_size = int(16 * ui_scale)
    footer_width = _font(footer_size).size(footer)[0]
    _draw_text(box_x + (box_width - footer_width) * 0.5,
               box_y + int(190 * ui_scale), footer, footer_size,
               (163, 195, 209))


def draw_hud(maze_data, player_x, player_y, yaw, elapsed,
             sight_charges, status, message, message_alpha,
             show_map, overhead, won, screen_width, screen_height,
             cell_size, time_value=0.0):
    _begin_2d(screen_width, screen_height)

    ui_scale = max(0.85, min(1.5, screen_height / 720.0))
    _draw_vignette(screen_width, screen_height, time_value)
    if won:
        _draw_victory_panel(
            elapsed, screen_width, screen_height, time_value, ui_scale
        )
        _end_2d()
        return

    _draw_status_effect(status, screen_width, screen_height,
                        time_value, ui_scale)
    panel_x = int(22 * ui_scale)
    panel_y = int(22 * ui_scale)
    panel_width = min(int(430 * ui_scale), int(screen_width * 0.43))
    panel_height = int(116 * ui_scale)
    _panel(panel_x, panel_y, panel_width, panel_height,
           (0.95, 0.36, 0.08, 0.86))
    _draw_text(int(38 * ui_scale), int(32 * ui_scale), "EMBERVAULT",
               int(25 * ui_scale), (255, 151, 65), True)
    _draw_text(int(218 * ui_scale), int(38 * ui_scale),
               "THE SHIFTING FORGE", int(14 * ui_scale),
               (133, 199, 219))

    cell_x, cell_y = maze.world_to_cell(player_x, player_y, cell_size)
    cell_text = f"CELL  {cell_x + 1:02d},{cell_y + 1:02d}"
    time_text = f"TIME  {_format_time(elapsed)}"
    _draw_text(int(38 * ui_scale), int(72 * ui_scale), cell_text,
               int(18 * ui_scale), (226, 232, 236), True)
    _draw_text(int(230 * ui_scale), int(72 * ui_scale), time_text,
               int(18 * ui_scale), (226, 232, 236), True)

    status_colors = {
        "NORMAL": (130, 218, 235),
        "HASTE": (75, 231, 255),
        "SLOWED": (255, 113, 62),
        "PHOENIX SIGHT": (124, 255, 198),
        "ASCENDING": (188, 112, 255),
        "OVERRIDE": (255, 206, 83),
    }
    sight_text = ("SIGHT MAX" if sight_charges == "MAX"
                  else f"SIGHT x{sight_charges}")
    _draw_text(int(38 * ui_scale), int(103 * ui_scale),
               sight_text, int(15 * ui_scale),
               (104, 245, 190), True)
    _draw_text(int(185 * ui_scale), int(103 * ui_scale), status,
               int(15 * ui_scale),
               status_colors.get(status, (225, 225, 225)), True)

    if show_map or overhead:
        _draw_minimap(
            maze_data, player_x, player_y, yaw,
            screen_width, screen_height, cell_size
        )

    if not overhead and not won:
        center_x = screen_width * 0.5
        center_y = screen_height * 0.5
        glDisable(GL_TEXTURE_2D)
        glColor4f(0.32, 0.88, 1.0, 0.72)
        glLineWidth(1.5)
        glBegin(GL_LINES)
        arm = 7 * ui_scale
        gap = 2 * ui_scale
        glVertex2f(center_x - arm, center_y); glVertex2f(center_x - gap, center_y)
        glVertex2f(center_x + gap, center_y); glVertex2f(center_x + arm, center_y)
        glVertex2f(center_x, center_y - arm); glVertex2f(center_x, center_y - gap)
        glVertex2f(center_x, center_y + gap); glVertex2f(center_x, center_y + arm)
        glEnd()

    if message and message_alpha > 0.0:
        message_size = int(20 * ui_scale)
        text_width = _font(message_size, True).size(message)[0]
        box_width = text_width + int(42 * ui_scale)
        box_x = (screen_width - box_width) * 0.5
        box_y = screen_height - int(88 * ui_scale)
        _panel(box_x, box_y, box_width, int(46 * ui_scale),
               (0.20, 0.78, 1.0, 0.60 * message_alpha))
        _draw_text(box_x + int(21 * ui_scale),
                   box_y + int(12 * ui_scale), message, message_size,
                   (210, 242, 255), True)

    glDisable(GL_TEXTURE_2D)
    glColor4f(0.07, 0.38, 0.50, 0.38)
    glLineWidth(1.0)
    glBegin(GL_LINE_LOOP)
    frame = 8 * ui_scale
    glVertex2f(frame, frame); glVertex2f(screen_width - frame, frame)
    glVertex2f(screen_width - frame, screen_height - frame)
    glVertex2f(frame, screen_height - frame)
    glEnd()

    _end_2d()


def _draw_help_row(x, y, key, description, ui_scale):
    key_size = int(17 * ui_scale)
    text_size = int(16 * ui_scale)
    _draw_text(x, y, key, key_size, (255, 151, 65), True)
    _draw_text(x + int(100 * ui_scale), y, description, text_size,
               (220, 228, 233))


def draw_jumpscare(screen_width, screen_height, scare_time, remaining):
    _begin_2d(screen_width, screen_height)

    ui_scale = max(0.55, min(1.5, screen_height / 720.0))
    flash = 0.30 + 0.22 * abs(math.sin(scare_time * 24.0))
    shake_x = math.sin(scare_time * 83.0) * 13.0 * ui_scale
    shake_y = math.cos(scare_time * 71.0) * 9.0 * ui_scale
    center_x = screen_width * 0.5 + shake_x
    center_y = screen_height * 0.48 + shake_y
    face_width = min(screen_width * 0.58, 520 * ui_scale)
    face_height = min(screen_height * 0.76, 500 * ui_scale)

    glDisable(GL_TEXTURE_2D)
    glColor4f(0.11, 0.0, 0.0, 0.88)
    glBegin(GL_QUADS)
    glVertex2f(0, 0); glVertex2f(screen_width, 0)
    glVertex2f(screen_width, screen_height); glVertex2f(0, screen_height)
    glEnd()

    glColor4f(0.13 + flash, 0.025, 0.012, 0.98)
    glBegin(GL_POLYGON)
    glVertex2f(center_x - face_width * 0.40, center_y - face_height * 0.48)
    glVertex2f(center_x + face_width * 0.40, center_y - face_height * 0.48)
    glVertex2f(center_x + face_width * 0.52, center_y - face_height * 0.08)
    glVertex2f(center_x + face_width * 0.33, center_y + face_height * 0.42)
    glVertex2f(center_x, center_y + face_height * 0.54)
    glVertex2f(center_x - face_width * 0.33, center_y + face_height * 0.42)
    glVertex2f(center_x - face_width * 0.52, center_y - face_height * 0.08)
    glEnd()

    glBlendFunc(GL_SRC_ALPHA, GL_ONE)
    for side in (-1, 1):
        eye_x = center_x + side * face_width * 0.22
        glColor4f(1.0, 0.28 + flash, 0.02, 0.95)
        glBegin(GL_TRIANGLES)
        glVertex2f(eye_x - face_width * 0.13, center_y - face_height * 0.15)
        glVertex2f(eye_x + face_width * 0.13, center_y - face_height * 0.10)
        glVertex2f(eye_x + side * face_width * 0.04,
                   center_y - face_height * 0.01)
        glEnd()

    tooth_width = face_width * 0.075
    glColor4f(1.0, 0.58, 0.12, 0.95)
    glBegin(GL_TRIANGLES)
    for tooth in range(-4, 5):
        tooth_x = center_x + tooth * tooth_width
        glVertex2f(tooth_x - tooth_width * 0.42,
                   center_y + face_height * 0.16)
        glVertex2f(tooth_x + tooth_width * 0.42,
                   center_y + face_height * 0.16)
        glVertex2f(tooth_x, center_y + face_height * 0.32)
    glEnd()
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    warning = "THE FORGE SEES YOU"
    text_size = int(27 * ui_scale)
    text_width = _font(text_size, True).size(warning)[0]
    alpha = min(1.0, remaining * 2.4)
    _draw_text((screen_width - text_width) * 0.5,
               screen_height - int(70 * ui_scale),
               warning, text_size,
               (255, int(90 + 80 * alpha), 38), True)

    _end_2d()


def draw_help_overlay(screen_width, screen_height, jumpscare_enabled=True):
    _begin_2d(screen_width, screen_height)

    ui_scale = max(0.50, min(1.35, screen_height / 720.0))
    glDisable(GL_TEXTURE_2D)
    glColor4f(0.0, 0.008, 0.014, 0.78)
    glBegin(GL_QUADS)
    glVertex2f(0, 0); glVertex2f(screen_width, 0)
    glVertex2f(screen_width, screen_height); glVertex2f(0, screen_height)
    glEnd()

    panel_width = min(int(900 * ui_scale),
                      screen_width - int(40 * ui_scale))
    panel_height = min(int(660 * ui_scale),
                       screen_height - int(40 * ui_scale))
    panel_x = (screen_width - panel_width) * 0.5
    panel_y = (screen_height - panel_height) * 0.5
    _panel(panel_x, panel_y, panel_width, panel_height,
           (0.95, 0.36, 0.08, 0.96))

    title = "VAULT BRIEFING"
    title_size = int(30 * ui_scale)
    title_width = _font(title_size, True).size(title)[0]
    _draw_text(panel_x + (panel_width - title_width) * 0.5,
               panel_y + int(25 * ui_scale), title, title_size,
               (255, 151, 65), True)

    mission = "Reach the cyan rift gate and escape the shifting forge."
    mission_size = int(16 * ui_scale)
    mission_width = _font(mission_size).size(mission)[0]
    _draw_text(panel_x + (panel_width - mission_width) * 0.5,
               panel_y + int(72 * ui_scale), mission, mission_size,
               (142, 218, 239))

    glDisable(GL_TEXTURE_2D)
    glColor4f(0.20, 0.68, 0.82, 0.55)
    glLineWidth(1.0)
    glBegin(GL_LINES)
    line_y = panel_y + int(112 * ui_scale)
    glVertex2f(panel_x + int(35 * ui_scale), line_y)
    glVertex2f(panel_x + panel_width - int(35 * ui_scale), line_y)
    glEnd()

    left_x = panel_x + int(55 * ui_scale)
    right_x = panel_x + panel_width * 0.53
    heading_y = panel_y + int(134 * ui_scale)
    _draw_text(left_x, heading_y, "MOVEMENT", int(17 * ui_scale),
               (104, 245, 190), True)
    _draw_text(right_x, heading_y, "RUN CONTROL", int(17 * ui_scale),
               (104, 245, 190), True)

    row_y = panel_y + int(174 * ui_scale)
    row_step = int(40 * ui_scale)
    _draw_help_row(left_x, row_y, "WASD", "Move through halls", ui_scale)
    _draw_help_row(left_x, row_y + row_step, "MOUSE", "Look around", ui_scale)
    _draw_help_row(left_x, row_y + row_step * 2, "Q",
                   "Reveal route (uses charge)", ui_scale)
    _draw_help_row(left_x, row_y + row_step * 3, "H", "Open this briefing",
                   ui_scale)
    _draw_help_row(left_x, row_y + row_step * 4, "ENTER",
                   "Start / close briefing", ui_scale)

    _draw_help_row(right_x, row_y, "R", "Restart maze and timer", ui_scale)
    _draw_help_row(right_x, row_y + row_step, "N", "Make a new maze",
                   ui_scale)
    _draw_help_row(right_x, row_y + row_step * 2, "M", "Toggle audio",
                   ui_scale)
    scare_state = "ON" if jumpscare_enabled else "OFF"
    _draw_help_row(right_x, row_y + row_step * 3, "J",
                   f"Jump scare {scare_state} / toggle", ui_scale)
    _draw_help_row(right_x, row_y + row_step * 4, "F10",
                   "Cycle window size", ui_scale)
    _draw_help_row(right_x, row_y + row_step * 5, "F11",
                   "Fullscreen / windowed", ui_scale)

    note_y = panel_y + int(414 * ui_scale)
    _draw_text(left_x, note_y, "CONTENT WARNING", int(17 * ui_scale),
               (255, 96, 74), True)
    warning = "One Ash Curse has a brief jump scare. Press J any time to disable it."
    warning_size = int(14 * ui_scale)
    warning_width = _font(warning_size).size(warning)[0]
    _draw_text(panel_x + (panel_width - warning_width) * 0.5,
               panel_y + int(444 * ui_scale), warning, warning_size,
               (241, 208, 201))

    _draw_text(left_x, panel_y + int(474 * ui_scale),
               "FORGE SECRETS", int(17 * ui_scale),
               (188, 112, 255), True)
    note = "A legendary 10-key game code grants eternal sight. It begins by looking UP twice."
    note_size = int(14 * ui_scale)
    note_width = _font(note_size).size(note)[0]
    _draw_text(panel_x + (panel_width - note_width) * 0.5,
               panel_y + int(504 * ui_scale), note, note_size,
               (213, 218, 224))

    prompt = "PRESS ENTER OR SPACE TO ENTER THE VAULT"
    prompt_size = int(19 * ui_scale)
    prompt_width = _font(prompt_size, True).size(prompt)[0]
    _draw_text(panel_x + (panel_width - prompt_width) * 0.5,
               panel_y + int(560 * ui_scale), prompt, prompt_size,
               (112, 226, 255), True)

    hint = "H opens briefing  |  ESC quits"
    hint_size = int(14 * ui_scale)
    hint_width = _font(hint_size).size(hint)[0]
    _draw_text(panel_x + (panel_width - hint_width) * 0.5,
               panel_y + int(612 * ui_scale), hint, hint_size,
               (157, 177, 187))

    _end_2d()
