from dataclasses import dataclass
import math


SHELL_CAPACITIES = (2, 8, 8)
CHARGE_STATES = (0, 1, -1)
HC_EV_NM = 1239.841984


@dataclass(frozen=True)
class Element:
    name: str
    symbol: str
    atomic_number: int
    isotopes: tuple[int, ...]
    representative_wavelength_nm: float


ELEMENTS = (
    Element("Hydrogen", "H", 1, (1, 2, 3), 656.28),
    Element("Helium", "He", 2, (4, 3), 587.56),
    Element("Lithium", "Li", 3, (7, 6), 670.78),
    Element("Carbon", "C", 6, (12, 13, 14), 658.76),
    Element("Oxygen", "O", 8, (16, 17, 18), 615.82),
    Element("Neon", "Ne", 10, (20, 21, 22), 640.22),
)


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def shell_occupancy(electron_count):

    remaining = max(0, min(sum(SHELL_CAPACITIES), int(electron_count)))
    shells = []
    for capacity in SHELL_CAPACITIES:
        count = min(capacity, remaining)
        if count or shells:
            shells.append(count)
        remaining -= count
        if remaining <= 0:
            break
    return tuple(shells)


def wavelength_to_rgb(wavelength_nm):

    wavelength = clamp(float(wavelength_nm), 380.0, 780.0)
    if wavelength < 440:
        red, green, blue = -(wavelength - 440) / 60, 0.0, 1.0
    elif wavelength < 490:
        red, green, blue = 0.0, (wavelength - 440) / 50, 1.0
    elif wavelength < 510:
        red, green, blue = 0.0, 1.0, -(wavelength - 510) / 20
    elif wavelength < 580:
        red, green, blue = (wavelength - 510) / 70, 1.0, 0.0
    elif wavelength < 645:
        red, green, blue = 1.0, -(wavelength - 645) / 65, 0.0
    else:
        red, green, blue = 1.0, 0.0, 0.0

    if wavelength < 420:
        factor = 0.35 + 0.65 * (wavelength - 380) / 40
    elif wavelength > 700:
        factor = 0.35 + 0.65 * (780 - wavelength) / 80
    else:
        factor = 1.0
    gamma = 0.8
    return tuple((max(0.0, channel * factor) ** gamma) for channel in (red, green, blue))


def nucleus_layout(protons, neutrons):

    total = int(protons) + int(neutrons)
    if total <= 0:
        return ()

    spacing = 0.56
    candidates = []
    for x_index in range(-2, 3):
        for y_index in range(-2, 3):
            for z_index in range(-2, 3):
                x = spacing * (x_index + (y_index & 1) * 0.5)
                y = spacing * 0.87 * y_index
                z = spacing * 0.82 * (z_index + ((x_index + y_index) & 1) * 0.5)
                distance = x * x + y * y + z * z
                candidates.append((distance, x, y, z))
    candidates.sort(key=lambda item: (round(item[0], 6),
                                      math.sin(item[1] * 11 + item[2] * 7 + item[3] * 5)))

    particles = []
    proton_count = 0
    for index, (_, x, y, z) in enumerate(candidates[:total]):
        target = ((index + 1) * protons) // total
        kind = "proton" if target > proton_count else "neutron"
        proton_count += kind == "proton"
        particles.append((kind, (x, y, z)))
    return tuple(particles)


class AtomicSimulation:


    EXCITED_DURATION = 1.15
    EMISSION_DURATION = 1.05

    def __init__(self, element_index=3):
        self.element_index = int(element_index) % len(ELEMENTS)
        self.isotope_index = 0
        self.charge_index = 0
        self.time = 0.0
        self.speed = 1.0
        self.paused = False
        self.phase = "idle"
        self.phase_elapsed = 0.0
        self.emission_time = 0.0
        self.event_count = 0

    @property
    def element(self):
        return ELEMENTS[self.element_index]

    @property
    def mass_number(self):
        return self.element.isotopes[self.isotope_index]

    @property
    def protons(self):
        return self.element.atomic_number

    @property
    def neutrons(self):
        return self.mass_number - self.protons

    @property
    def charge(self):
        return CHARGE_STATES[self.charge_index]

    @property
    def electrons(self):
        return max(0, self.protons - self.charge)

    @property
    def shells(self):
        return shell_occupancy(self.electrons)

    @property
    def outer_shell(self):
        return len(self.shells) if self.shells else 0

    @property
    def wavelength_nm(self):
        return self.element.representative_wavelength_nm

    @property
    def photon_energy_ev(self):
        return HC_EV_NM / self.wavelength_nm

    @property
    def photon_progress(self):
        if self.phase != "emitting":
            return 0.0
        return clamp(self.phase_elapsed / self.EMISSION_DURATION, 0.0, 1.0)

    @property
    def transition_label(self):
        if not self.shells:
            return "UNAVAILABLE"
        lower = max(1, self.outer_shell)
        return f"n={lower + 1} > n={lower}"

    def reset_event(self):
        self.phase = "idle"
        self.phase_elapsed = 0.0

    def select_element(self, index):
        self.element_index = int(index) % len(ELEMENTS)
        self.isotope_index = 0
        self.charge_index = 0
        self.reset_event()

    def cycle_isotope(self):
        self.isotope_index = (self.isotope_index + 1) % len(self.element.isotopes)
        self.reset_event()

    def cycle_charge(self):
        self.charge_index = (self.charge_index + 1) % len(CHARGE_STATES)
        self.reset_event()

    def excite(self):
        if self.phase != "idle" or self.electrons <= 0:
            return False
        self.phase = "excited"
        self.phase_elapsed = 0.0
        return True

    def update(self, delta):
        if self.paused:
            return
        elapsed = max(0.0, float(delta)) * self.speed
        self.time += elapsed
        if self.phase == "idle":
            return
        self.phase_elapsed += elapsed
        if self.phase == "excited" and self.phase_elapsed >= self.EXCITED_DURATION:
            self.phase = "emitting"
            self.phase_elapsed -= self.EXCITED_DURATION
            self.emission_time = self.time
        elif self.phase == "emitting" and self.phase_elapsed >= self.EMISSION_DURATION:
            self.phase = "idle"
            self.phase_elapsed = 0.0
            self.event_count += 1
