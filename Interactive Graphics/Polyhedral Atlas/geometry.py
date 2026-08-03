import math
from dataclasses import dataclass


def _normal(vertices, face):
    a, b, c = (vertices[face[i]] for i in range(3))
    first = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    second = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
    value = (
        first[1] * second[2] - first[2] * second[1],
        first[2] * second[0] - first[0] * second[2],
        first[0] * second[1] - first[1] * second[0],
    )
    length = math.sqrt(sum(component * component for component in value))
    return tuple(component / length for component in value)


def _orient(vertices, faces):
    result = []
    for face in faces:
        normal = _normal(vertices, face)
        center = tuple(
            sum(vertices[index][axis] for index in face) / len(face)
            for axis in range(3)
        )
        if sum(normal[axis] * center[axis] for axis in range(3)) < 0:
            face = tuple(reversed(face))
        result.append(face)
    return tuple(result)


def _edges(faces):
    values = set()
    for face in faces:
        for index in range(len(face)):
            values.add(tuple(sorted((face[index], face[(index + 1) % len(face)]))))
    return tuple(sorted(values))


@dataclass(frozen=True)
class Solid:
    name: str
    vertices: tuple
    faces: tuple
    color: tuple

    @property
    def edges(self):
        return _edges(self.faces)

    @property
    def normals(self):
        return tuple(_normal(self.vertices, face) for face in self.faces)

    @property
    def euler(self):
        return len(self.vertices) - len(self.edges) + len(self.faces)

    @property
    def edge_length(self):
        a, b = self.edges[0]
        return math.dist(self.vertices[a], self.vertices[b])

    def dual(self):
        dual_vertices = []
        for face in self.faces:
            center = [
                sum(self.vertices[index][axis] for index in face) / len(face)
                for axis in range(3)
            ]
            length = math.sqrt(sum(value * value for value in center))
            dual_vertices.append(tuple(value / length for value in center))

        dual_edges = []
        for first in range(len(self.faces)):
            for second in range(first + 1, len(self.faces)):
                if len(set(self.faces[first]) & set(self.faces[second])) == 2:
                    dual_edges.append((first, second))
        return tuple(dual_vertices), tuple(dual_edges)


def _solid(name, vertices, faces, color):
    return Solid(name, tuple(vertices), _orient(vertices, faces), color)


def create_solids():
    d = 1 / math.sqrt(3)
    tetrahedron = _solid(
        "Tetrahedron",
        ((d, d, d), (d, -d, -d), (-d, d, -d), (-d, -d, d)),
        ((0, 1, 2), (3, 1, 0), (0, 2, 3), (3, 2, 1)),
        (0.78, 0.24, 0.18),
    )

    cube = _solid(
        "Cube",
        ((d, -d, -d), (d, d, -d), (-d, d, -d), (-d, -d, -d),
         (d, -d, d), (d, d, d), (-d, -d, d), (-d, d, d)),
        ((0, 1, 2, 3), (3, 2, 7, 6), (6, 7, 5, 4),
         (4, 5, 1, 0), (1, 5, 7, 2), (4, 0, 3, 6)),
        (0.14, 0.35, 0.68),
    )

    octahedron = _solid(
        "Octahedron",
        ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0),
         (0, 0, 1), (0, 0, -1)),
        ((0, 2, 4), (5, 2, 0), (4, 3, 0), (0, 3, 5),
         (4, 2, 1), (1, 2, 5), (1, 3, 4), (5, 3, 1)),
        (0.12, 0.50, 0.40),
    )

    phi = (1 + math.sqrt(5)) / 2
    a = 1 / phi
    scale = 1 / math.sqrt(3)
    dodecahedron_vertices = (
        (1, 1, 1), (1, 1, -1), (1, -1, 1), (1, -1, -1),
        (-1, 1, 1), (-1, 1, -1), (-1, -1, 1), (-1, -1, -1),
        (0, a, phi), (0, a, -phi), (0, -a, phi), (0, -a, -phi),
        (a, phi, 0), (a, -phi, 0), (-a, phi, 0), (-a, -phi, 0),
        (phi, 0, a), (phi, 0, -a), (-phi, 0, a), (-phi, 0, -a),
    )
    dodecahedron_vertices = tuple(
        tuple(value * scale for value in vertex)
        for vertex in dodecahedron_vertices
    )
    dodecahedron = _solid(
        "Dodecahedron", dodecahedron_vertices,
        ((12, 14, 4, 8, 0), (0, 8, 10, 2, 16), (16, 17, 1, 12, 0),
         (1, 9, 5, 14, 12), (17, 3, 11, 9, 1), (2, 10, 6, 15, 13),
         (2, 13, 3, 17, 16), (13, 15, 7, 11, 3), (18, 6, 10, 8, 4),
         (4, 14, 5, 19, 18), (5, 9, 11, 7, 19), (18, 19, 7, 15, 6)),
        (0.35, 0.25, 0.66),
    )

    scale = 1 / math.sqrt(1 + phi * phi)
    icosahedron_vertices = (
        (0, 1, phi), (0, 1, -phi), (0, -1, phi), (0, -1, -phi),
        (1, phi, 0), (1, -phi, 0), (-1, phi, 0), (-1, -phi, 0),
        (phi, 0, 1), (phi, 0, -1), (-phi, 0, 1), (-phi, 0, -1),
    )
    icosahedron_vertices = tuple(
        tuple(value * scale for value in vertex)
        for vertex in icosahedron_vertices
    )
    icosahedron = _solid(
        "Icosahedron", icosahedron_vertices,
        ((0, 2, 8), (10, 2, 0), (0, 4, 6), (8, 4, 0), (0, 6, 10),
         (9, 3, 1), (1, 3, 11), (6, 4, 1), (1, 4, 9), (11, 6, 1),
         (7, 5, 2), (2, 5, 8), (10, 7, 2), (3, 5, 7), (9, 5, 3),
         (3, 7, 11), (4, 8, 9), (9, 8, 5), (11, 10, 6), (7, 10, 11)),
        (0.75, 0.37, 0.12),
    )
    return (tetrahedron, cube, octahedron, dodecahedron, icosahedron)
