#include "core/species/Unicorn.h"

namespace vpet {

// StatChange fields: hunger, fatigue, boredom, happiness, health, discipline.

Unicorn::Unicorn(const std::string& name) : Pet(name) {}

std::string Unicorn::species() const {
    return "Unicorn";
}

std::array<SpecialAction, 2> Unicorn::specialActions() const {
    return {{
        SpecialAction{"Restore vitality", "Heal", "{name} releases a calm restorative glow.", StatChange{0, 6, 0, 4, 18, 0}},
        SpecialAction{"Light spell", "Spell", "{name} forms a bright constellation in the air.", StatChange{0, 10, -16, 10, 0, 5}},
    }};
}

std::vector<PetEvent> Unicorn::events() const {
    return {
        PetEvent{"A rainbow appeared and {name} pranced underneath it.", StatChange{0, 0, -5, 7, 0, 0}},
        PetEvent{"{name} found a patch of clover.", StatChange{-8, 0, 0, 2, 0, 0}},
        PetEvent{"{name} tangled a mane in the brambles.", StatChange{0, 3, 0, -4, 0, 0}},
        PetEvent{"{name} hummed a quiet tune to itself.", StatChange{0, 0, -6, 0, 0, 0}},
    };
}

}  // namespace vpet
