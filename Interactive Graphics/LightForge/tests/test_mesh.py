import math
import os

import pytest

from mesh import load_obj

TEAPOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "teapot.obj")


def test_teapot_loads():
    mesh = load_obj(TEAPOT)
    assert len(mesh.vertices) == 3242
    assert len(mesh.triangles) == 6320
    assert mesh.radius > 0


def test_quads_are_split_into_a_fan(tmp_path):
    path = tmp_path / "quad.obj"
    path.write_text("v 0 0 0\nv 1 0 0\nv 1 1 0\nv 0 1 0\nf 1/1/1 2/2/2 3/3/3 4/4/4\n")
    mesh = load_obj(str(path))
    assert mesh.triangles == ((0, 1, 2), (0, 2, 3))


def test_normals_follow_the_winding_and_are_unit_length(tmp_path):
    path = tmp_path / "triangle.obj"
    path.write_text("v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n")
    mesh = load_obj(str(path))
    assert mesh.face_normals[0] == pytest.approx((0.0, 0.0, 1.0))
    for normal in mesh.vertex_normals:
        assert normal == pytest.approx((0.0, 0.0, 1.0))


def test_vertex_normals_average_neighbouring_faces(tmp_path):
    # Two faces at right angles share an edge; the shared vertices point between them.
    path = tmp_path / "corner.obj"
    path.write_text("v 0 0 0\nv 1 0 0\nv 0 1 0\nv 0 0 1\nf 1 2 3\nf 1 4 2\n")
    mesh = load_obj(str(path))
    shared = mesh.vertex_normals[0]
    assert math.sqrt(sum(c * c for c in shared)) == pytest.approx(1.0)
    assert shared == pytest.approx((0.0, math.sqrt(0.5), math.sqrt(0.5)))
