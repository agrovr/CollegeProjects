import math

import pytest

from geometry import create_solids

EXPECTED = {
    "Tetrahedron": (4, 6, 4, 1.6330, "Tetrahedron"),
    "Cube": (8, 12, 6, 1.1547, "Octahedron"),
    "Octahedron": (6, 12, 8, 1.4142, "Cube"),
    "Dodecahedron": (20, 30, 12, 0.7136, "Icosahedron"),
    "Icosahedron": (12, 30, 20, 1.0515, "Dodecahedron"),
}

SOLIDS = create_solids()


def centroid(points):
    return [sum(p[i] for p in points) / len(points) for i in range(3)]


@pytest.mark.parametrize("solid", SOLIDS, ids=lambda s: s.name)
def test_counts_and_euler_characteristic(solid):
    vertices, edges, faces, _, _ = EXPECTED[solid.name]
    assert len(solid.vertices) == vertices
    assert len(solid.edges) == edges
    assert len(solid.faces) == faces
    assert solid.euler == 2


@pytest.mark.parametrize("solid", SOLIDS, ids=lambda s: s.name)
def test_vertices_sit_on_the_unit_sphere(solid):
    for vertex in solid.vertices:
        assert math.dist(vertex, (0, 0, 0)) == pytest.approx(1.0)


@pytest.mark.parametrize("solid", SOLIDS, ids=lambda s: s.name)
def test_every_edge_has_the_same_length(solid):
    lengths = [math.dist(solid.vertices[a], solid.vertices[b]) for a, b in solid.edges]
    assert max(lengths) - min(lengths) < 1e-9
    assert solid.edge_length == pytest.approx(EXPECTED[solid.name][3], abs=1e-4)


@pytest.mark.parametrize("solid", SOLIDS, ids=lambda s: s.name)
def test_face_normals_point_outward(solid):
    for face, normal in zip(solid.faces, solid.normals):
        center = centroid([solid.vertices[i] for i in face])
        assert sum(n * c for n, c in zip(normal, center)) > 0
        assert math.dist(normal, (0, 0, 0)) == pytest.approx(1.0)


@pytest.mark.parametrize("solid", SOLIDS, ids=lambda s: s.name)
def test_dual_has_the_swapped_counts(solid):
    dual_vertices, dual_edges = solid.dual()
    assert len(dual_vertices) == len(solid.faces)
    assert len(dual_edges) == len(solid.edges)
    for vertex in dual_vertices:
        assert math.dist(vertex, (0, 0, 0)) == pytest.approx(1.0)
    # The dual's vertex count matches the named dual solid.
    dual_name = EXPECTED[solid.name][4]
    assert len(dual_vertices) == EXPECTED[dual_name][0]
