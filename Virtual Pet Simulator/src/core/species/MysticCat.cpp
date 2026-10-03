#include "core/species/MysticCat.h"

namespace vpet {

// StatChange fields: hunger, fatigue, boredom, happiness, health, discipline.

MysticCat::MysticCat(const std::string& name) : Pet(name) {}

std::string MysticCat::species() const {
    return "Mystic Cat";
}

std::array<SpecialAction, 2> MysticCat::specialActions() const {
    return {{
        SpecialAction{"Telekinesis", "Focus", "{name} carefully lifts a toy with focused thought.", StatChange{0, 12, -14, 7, 0, 6}},
        SpecialAction{"Study a trick", "Trick", "{name} masters a clever new trick.", StatChange{5, 0, -20, 9, 0, 8}},
    }};
}

std::vector<PetEvent> MysticCat::events() const {
    return {
        PetEvent{"{name} knocked a cup off the table, on purpose.", StatChange{0, 0, -6, 0, 0, -4}},
        PetEvent{"{name} found a sunbeam and napped in it.", StatChange{0, -8, 0, 3, 0, 0}},
        PetEvent{"{name} stared at an empty corner for a long time.", StatChange{0, 0, -3, 0, 0, 0}},
        PetEvent{"{name} brought you a mysterious glowing feather.", StatChange{0, 0, 0, 6, 0, 0}},
    };
}

}  // namespace vpet
