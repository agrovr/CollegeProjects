import math


def subtract(first, second):
    return tuple(first[i] - second[i] for i in range(3))


def cross(first, second):
    return (
        first[1] * second[2] - first[2] * second[1],
        first[2] * second[0] - first[0] * second[2],
        first[0] * second[1] - first[1] * second[0],
    )


def normalize(vector):
    length = math.sqrt(sum(value * value for value in vector))
    if length == 0:
        return (0.0, 0.0, 1.0)
    return tuple(value / length for value in vector)


def load_obj(path):
    vertices = []
    triangles = []
    with open(path, "r", encoding="utf-8") as source:
        for line in source:
            parts = line.strip().split()
            if not parts:
                continue
            if parts[0] == "v":
                vertices.append(tuple(float(value) for value in parts[1:4]))
            elif parts[0] == "f":
                face = [int(value.split("/")[0]) - 1 for value in parts[1:]]
                for index in range(1, len(face) - 1):
                    triangles.append((face[0], face[index], face[index + 1]))
    return Mesh(tuple(vertices), tuple(triangles))


class Mesh:
    def __init__(self, vertices, triangles):
        self.vertices = vertices
        self.triangles = triangles
        self.center = tuple(
            (min(vertex[axis] for vertex in vertices) + max(vertex[axis] for vertex in vertices)) / 2
            for axis in range(3)
        )
        self.radius = max(math.dist(vertex, self.center) for vertex in vertices)
        self.face_normals = self._face_normals()
        self.vertex_normals = self._vertex_normals()
        self.face_centers = tuple(
            tuple(sum(self.vertices[index][axis] for index in triangle) / 3 for axis in range(3))
            for triangle in self.triangles
        )

    def _face_normals(self):
        normals = []
        for a, b, c in self.triangles:
            normals.append(normalize(cross(
                subtract(self.vertices[b], self.vertices[a]),
                subtract(self.vertices[c], self.vertices[a]),
            )))
        return tuple(normals)

    def _vertex_normals(self):
        accumulators = [[0.0, 0.0, 0.0] for _ in self.vertices]
        for triangle, normal in zip(self.triangles, self.face_normals):
            for index in triangle:
                for axis in range(3):
                    accumulators[index][axis] += normal[axis]
        return tuple(normalize(value) for value in accumulators)
