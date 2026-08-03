import math
import random


def quaternion_multiply(first, second):
    w1, x1, y1, z1 = first
    w2, x2, y2, z2 = second
    return (
        w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
        w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
        w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
        w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
    )


def quaternion_normalize(value):
    length = math.sqrt(sum(component * component for component in value))
    return tuple(component / length for component in value)


def axis_angle(axis, angle):
    length = math.sqrt(sum(value * value for value in axis))
    if length == 0:
        return (1.0, 0.0, 0.0, 0.0)
    sine = math.sin(angle / 2.0) / length
    return quaternion_normalize((math.cos(angle / 2.0),
                                 axis[0] * sine, axis[1] * sine, axis[2] * sine))


def rotate_vector(quaternion, vector):
    value = quaternion_multiply(
        quaternion_multiply(quaternion, (0.0, *vector)),
        (quaternion[0], -quaternion[1], -quaternion[2], -quaternion[3]),
    )
    return value[1:]


def align_vectors(source, target):
    source_length = math.sqrt(sum(value * value for value in source))
    target_length = math.sqrt(sum(value * value for value in target))
    a = tuple(value / source_length for value in source)
    b = tuple(value / target_length for value in target)
    dot = max(-1.0, min(1.0, sum(a[i] * b[i] for i in range(3))))
    if dot < -0.999999:
        axis = (1.0, 0.0, 0.0) if abs(a[0]) < 0.8 else (0.0, 1.0, 0.0)
        cross = (a[1] * axis[2] - a[2] * axis[1],
                 a[2] * axis[0] - a[0] * axis[2],
                 a[0] * axis[1] - a[1] * axis[0])
        return axis_angle(cross, math.pi)
    cross = (a[1] * b[2] - a[2] * b[1],
             a[2] * b[0] - a[0] * b[2],
             a[0] * b[1] - a[1] * b[0])
    return quaternion_normalize((1.0 + dot, *cross))


def quaternion_matrix(quaternion):
    w, x, y, z = quaternion_normalize(quaternion)
    return (
        1 - 2 * (y * y + z * z), 2 * (x * y + z * w), 2 * (x * z - y * w), 0,
        2 * (x * y - z * w), 1 - 2 * (x * x + z * z), 2 * (y * z + x * w), 0,
        2 * (x * z + y * w), 2 * (y * z - x * w), 1 - 2 * (x * x + y * y), 0,
        0, 0, 0, 1,
    )


class DiceSimulation:
    def __init__(self, solid, numbers):
        self.solid = solid
        self.numbers = numbers
        self.orientation = (1.0, 0.0, 0.0, 0.0)
        self.angular_velocity = (0.0, 0.0, 0.0)
        self.height = 1.0
        self.vertical_velocity = 0.0
        self.rolling = False
        self.elapsed = 0.0
        self.impacts = 0
        self.result = None
        self.settle()

    def set_die(self, solid, numbers):
        self.solid = solid
        self.numbers = numbers
        self.orientation = (1.0, 0.0, 0.0, 0.0)
        self.angular_velocity = (0.0, 0.0, 0.0)
        self.rolling = False
        self.result = None
        self.settle()

    def roll(self, seed=None, strength=1.0):
        rng = random.Random(seed)
        axis = (rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))
        self.orientation = axis_angle(axis, rng.uniform(0.2, math.tau))
        self.angular_velocity = (
            rng.uniform(4.5, 8.0) * strength,
            rng.uniform(-7.0, 7.0) * strength,
            rng.uniform(4.0, 8.5) * strength,
        )
        self.height = 2.2 + 0.6 * strength
        self.vertical_velocity = 4.2 + 1.5 * strength
        self.rolling = True
        self.elapsed = 0.0
        self.impacts = 0
        self.result = None

    def transformed_vertices(self):
        return tuple(rotate_vector(self.orientation, vertex) for vertex in self.solid.vertices)

    def top_face_index(self):
        values = [rotate_vector(self.orientation, normal)[2] for normal in self.solid.normals]
        return max(range(len(values)), key=values.__getitem__)

    def floor_offset(self):
        return -min(vertex[2] for vertex in self.transformed_vertices())

    def settle(self):
        face_index = self.top_face_index()
        world_normal = rotate_vector(self.orientation, self.solid.normals[face_index])
        correction = align_vectors(world_normal, (0.0, 0.0, 1.0))
        self.orientation = quaternion_normalize(
            quaternion_multiply(correction, self.orientation)
        )
        self.height = self.floor_offset() + 0.025
        self.vertical_velocity = 0.0
        self.angular_velocity = (0.0, 0.0, 0.0)
        self.rolling = False
        self.result = self.numbers[self.top_face_index()]

    def update(self, delta_time):
        if not self.rolling:
            return
        delta_time = min(delta_time, 0.04)
        self.elapsed += delta_time
        speed = math.sqrt(sum(value * value for value in self.angular_velocity))
        if speed > 0:
            rotation = axis_angle(self.angular_velocity, speed * delta_time)
            self.orientation = quaternion_normalize(
                quaternion_multiply(rotation, self.orientation)
            )
        self.vertical_velocity -= 9.8 * delta_time
        self.height += self.vertical_velocity * delta_time

        minimum = min(vertex[2] for vertex in self.transformed_vertices()) + self.height
        if minimum < 0.0:
            self.height -= minimum
            self.impacts += 1
            self.vertical_velocity = abs(self.vertical_velocity) * 0.34
            self.angular_velocity = tuple(value * 0.58 for value in self.angular_velocity)

        self.angular_velocity = tuple(value * math.pow(0.992, delta_time * 60.0)
                                      for value in self.angular_velocity)
        angular_speed = math.sqrt(sum(value * value for value in self.angular_velocity))
        if self.elapsed > 5.0 or (self.impacts >= 4 and
                                 self.vertical_velocity < 0.22 and angular_speed < 0.65):
            self.settle()
