import math

import pytest

from simulation import BODIES, OrrerySimulation, eccentric_anomaly, moon_position, orbital_position

ORBIT_SCALE = 6.0


def distance(point, other=(0.0, 0.0, 0.0)):
    return math.dist(point, other)


@pytest.mark.parametrize("eccentricity", [0.0, 0.0167, 0.2056, 0.6])
def test_kepler_solution_satisfies_the_equation(eccentricity):
    for step in range(24):
        mean = math.tau * step / 24
        anomaly = eccentric_anomaly(mean, eccentricity)
        assert anomaly - eccentricity * math.sin(anomaly) == pytest.approx(mean, abs=1e-9)


@pytest.mark.parametrize("body", BODIES, ids=lambda b: b.name)
def test_orbit_returns_after_one_period(body):
    start = orbital_position(body, 0.0)
    later = orbital_position(body, body.period_days)
    assert later == pytest.approx(start, abs=1e-9)


@pytest.mark.parametrize("body", BODIES, ids=lambda b: b.name)
def test_distance_stays_between_perihelion_and_aphelion(body):
    a = body.orbit_au * ORBIT_SCALE
    perihelion, aphelion = a * (1 - body.eccentricity), a * (1 + body.eccentricity)
    for step in range(200):
        r = distance(orbital_position(body, body.period_days * step / 200))
        assert perihelion - 1e-9 <= r <= aphelion + 1e-9
    assert distance(orbital_position(body, 0.0)) == pytest.approx(perihelion)
    assert distance(orbital_position(body, body.period_days / 2)) == pytest.approx(aphelion)


def test_mercury_is_faster_near_the_sun():
    mercury = BODIES[0]
    step = 0.01

    def speed(day):
        return distance(orbital_position(mercury, day), orbital_position(mercury, day + step)) / step

    ratio = speed(0.0) / speed(mercury.period_days / 2)
    expected = (1 + mercury.eccentricity) / (1 - mercury.eccentricity)
    assert ratio == pytest.approx(expected, rel=1e-3)


def test_inclination_lifts_orbits_out_of_the_plane():
    earth = next(b for b in BODIES if b.name == "Earth")
    mercury = BODIES[0]
    assert max(abs(orbital_position(earth, d)[2]) for d in range(0, 366, 5)) == pytest.approx(0.0)
    assert max(abs(orbital_position(mercury, d)[2]) for d in range(0, 88)) > 0.1


def test_moon_keeps_its_distance_from_earth():
    earth = (3.0, -1.0, 0.0)
    for day in range(0, 28):
        moon = moon_position(earth, day)
        flat = math.dist(moon[:2], earth[:2])
        assert flat == pytest.approx(0.72)


def test_simulation_advances_and_pauses():
    simulation = OrrerySimulation()
    simulation.update(1.0)
    assert simulation.elapsed_days == pytest.approx(36.526)
    simulation.paused = True
    simulation.update(1.0)
    assert simulation.elapsed_days == pytest.approx(36.526)
    positions = simulation.positions()
    assert set(positions) == {"Mercury", "Venus", "Earth", "Mars", "Moon", "Sun"}
    assert positions["Sun"] == (0.0, 0.0, 0.0)
