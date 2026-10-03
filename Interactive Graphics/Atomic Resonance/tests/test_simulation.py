import pytest

from simulation import ELEMENTS, HC_EV_NM, AtomicSimulation, nucleus_layout, shell_occupancy, wavelength_to_rgb


@pytest.mark.parametrize("electrons, shells", [(0, ()), (1, (1,)), (2, (2,)), (3, (2, 1)), (6, (2, 4)), (10, (2, 8)), (11, (2, 8, 1)), (30, (2, 8, 8))])
def test_shells_fill_two_eight_eight(electrons, shells):
    assert shell_occupancy(electrons) == shells


@pytest.mark.parametrize("index", range(len(ELEMENTS)), ids=[e.symbol for e in ELEMENTS])
def test_neutral_atoms_have_matching_electrons(index):
    simulation = AtomicSimulation(index)
    element = ELEMENTS[index]
    assert simulation.protons == element.atomic_number
    assert simulation.electrons == element.atomic_number
    assert simulation.charge == 0
    assert simulation.mass_number == element.isotopes[0]
    assert simulation.neutrons == element.isotopes[0] - element.atomic_number


def test_charge_states_change_the_electron_count():
    simulation = AtomicSimulation(3)  # carbon
    simulation.cycle_charge()
    assert simulation.charge == 1 and simulation.electrons == 5
    simulation.cycle_charge()
    assert simulation.charge == -1 and simulation.electrons == 7


def test_isotopes_change_only_the_neutrons():
    simulation = AtomicSimulation(3)
    simulation.cycle_isotope()
    assert simulation.protons == 6
    assert simulation.mass_number == 13 and simulation.neutrons == 7


@pytest.mark.parametrize("element", ELEMENTS, ids=lambda e: e.symbol)
def test_photon_energy_is_hc_over_wavelength(element):
    simulation = AtomicSimulation(ELEMENTS.index(element))
    assert simulation.photon_energy_ev == pytest.approx(HC_EV_NM / element.representative_wavelength_nm)
    assert 1.8 < simulation.photon_energy_ev < 2.2


def test_nucleus_layout_places_every_nucleon():
    positions = nucleus_layout(6, 6)
    assert len(positions) == 12


def test_visible_colours_are_in_range_and_red_is_red():
    for wavelength in range(380, 781, 20):
        assert all(0.0 <= channel <= 1.0 for channel in wavelength_to_rgb(wavelength))
    red, green, blue = wavelength_to_rgb(656.28)
    assert red > 0.5 and green < 0.2 and blue < 0.2


def test_excitation_runs_through_its_phases():
    simulation = AtomicSimulation(0)
    assert simulation.excite()
    assert not simulation.excite()  # one event at a time
    phases = set()
    for _ in range(600):
        simulation.update(1 / 60)
        phases.add(simulation.phase)
    assert "emitting" in phases
    assert simulation.phase == "idle"
