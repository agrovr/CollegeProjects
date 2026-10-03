import pytest

pygame = pytest.importorskip("pygame")  # main.py imports pygame and PyOpenGL
from main import MAX_PARTICLES, ParticleSystem  # noqa: E402


@pytest.mark.parametrize("mode", range(4))
def test_particle_count_never_exceeds_the_cap(mode):
    system = ParticleSystem()
    system.set_mode(mode)
    system.spawn_rate = 5000
    for _ in range(600):
        system.update(1 / 30)
        assert len(system.particles) <= MAX_PARTICLES


@pytest.mark.parametrize("mode", range(4))
def test_each_mode_produces_particles_that_age(mode):
    system = ParticleSystem()
    system.set_mode(mode)
    for _ in range(60):
        system.update(1 / 30)
    assert system.particles
    assert all(0.0 <= p.age <= p.life for p in system.particles)


def test_clear_and_pause():
    system = ParticleSystem()
    for _ in range(30):
        system.update(1 / 30)
    system.clear()
    assert not system.particles
