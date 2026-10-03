import math

import pytest

from geometry import create_solids
from physics import DiceSimulation, quaternion_multiply, quaternion_normalize, axis_angle, rotate_vector

NUMBER_MAPS = None
try:
    from main import NUMBER_MAPS  # needs pygame and PyOpenGL installed
except ImportError:
    pass

SOLIDS = create_solids()
SIDES = [4, 6, 8, 12, 20]


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def test_five_dice_with_the_right_face_counts():
    assert [len(s.faces) for s in SOLIDS] == SIDES


@pytest.mark.skipif(NUMBER_MAPS is None, reason="pygame or PyOpenGL not installed")
@pytest.mark.parametrize("index", range(5), ids=["D4", "D6", "D8", "D12", "D20"])
def test_numbering_uses_every_value_and_opposite_faces_add_up(index):
    solid, numbers = SOLIDS[index], NUMBER_MAPS[index]
    assert sorted(numbers) == list(range(1, len(numbers) + 1))
    for i, a in enumerate(solid.normals):
        for j, b in enumerate(solid.normals):
            if j > i and dot(a, b) < -0.999:
                assert numbers[i] + numbers[j] == len(numbers) + 1


def test_quaternions_stay_unit_length_and_rotate_correctly():
    quarter = axis_angle((0, 0, 1), math.pi / 2)
    assert math.dist(rotate_vector(quarter, (1, 0, 0)), (0, 1, 0)) < 1e-9
    combined = quaternion_normalize(quaternion_multiply(quarter, quarter))
    assert math.dist(rotate_vector(combined, (1, 0, 0)), (-1, 0, 0)) < 1e-9
    assert math.sqrt(sum(c * c for c in combined)) == pytest.approx(1.0)


@pytest.mark.parametrize("index", range(5), ids=["D4", "D6", "D8", "D12", "D20"])
def test_a_throw_settles_flat_with_a_valid_result(index):
    numbers = tuple(range(1, SIDES[index] + 1))
    for seed in range(10):
        simulation = DiceSimulation(SOLIDS[index], numbers)
        simulation.roll(seed=seed)
        for _ in range(400):  # 400 steps of 1/60 s is longer than the 5 s limit
            simulation.update(1 / 60)
            if not simulation.rolling:
                break
        assert not simulation.rolling
        top = simulation.top_face_index()
        up = rotate_vector(simulation.orientation, simulation.solid.normals[top])
        assert up[2] == pytest.approx(1.0, abs=1e-6)
        assert simulation.result == numbers[top]


def test_same_seed_same_result():
    numbers = tuple(range(1, 21))
    results = []
    for _ in range(2):
        simulation = DiceSimulation(SOLIDS[4], numbers)
        simulation.roll(seed=1234)
        while simulation.rolling:
            simulation.update(1 / 60)
        results.append(simulation.result)
    assert results[0] == results[1]
