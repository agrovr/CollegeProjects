import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Body:
    name: str
    color: tuple
    relative_radius: float
    orbit_au: float
    period_days: float
    eccentricity: float
    inclination: float


BODIES = (
    Body("Mercury", (0.66, 0.54, 0.43), 0.38, 0.39, 87.97, 0.2056, 7.00),
    Body("Venus", (0.88, 0.65, 0.30), 0.95, 0.72, 224.70, 0.0068, 3.39),
    Body("Earth", (0.18, 0.42, 0.78), 1.00, 1.00, 365.26, 0.0167, 0.00),
    Body("Mars", (0.72, 0.24, 0.12), 0.53, 1.50, 686.98, 0.0934, 1.85),
)


def orbital_position(body, elapsed_days, orbit_scale=6.0):
    angle = math.tau * elapsed_days / body.period_days
    semi_major = body.orbit_au * orbit_scale
    semi_minor = semi_major * math.sqrt(1.0 - body.eccentricity ** 2)
    distance_offset = semi_major * body.eccentricity
    x = math.cos(angle) * semi_major - distance_offset
    y = math.sin(angle) * semi_minor
    inclination = math.radians(body.inclination)
    return (x, y * math.cos(inclination), y * math.sin(inclination))


def moon_position(earth_position, elapsed_days, orbit_radius=0.72):
    angle = math.tau * elapsed_days / 27.3
    return (
        earth_position[0] + math.cos(angle) * orbit_radius,
        earth_position[1] + math.sin(angle) * orbit_radius,
        earth_position[2] + math.sin(angle) * 0.12,
    )


class OrrerySimulation:
    def __init__(self):
        self.elapsed_days = 0.0
        self.days_per_second = 36.526
        self.paused = False

    def update(self, delta_time):
        if not self.paused:
            self.elapsed_days += delta_time * self.days_per_second

    def positions(self):
        planets = {body.name: orbital_position(body, self.elapsed_days) for body in BODIES}
        planets["Moon"] = moon_position(planets["Earth"], self.elapsed_days)
        planets["Sun"] = (0.0, 0.0, 0.0)
        return planets
