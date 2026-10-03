#include "core/species/Dragon.h"

namespace vpet {

// StatChange fields: hunger, fatigue, boredom, happiness, health, discipline.

Dragon::Dragon(const std::string& name) : Pet(name) {}

std::string Dragon::species() const {
    return "Dragon";
}

std::array<SpecialAction, 2> Dragon::specialActions() const {
    return {{
        SpecialAction{"Flight training", "Fly", "{name} completes a sweeping flight circuit.", StatChange{0, 14, -18, 8, 0, 4}},
        SpecialAction{"Controlled flame", "Flame", "{name} shapes a precise ribbon of flame.", StatChange{8, 0, -10, 6, 0, 7}},
    }};
}

std::vector<PetEvent> Dragon::events() const {
    return {
        PetEvent{"{name} found a glittering coin and added it to the hoard.", StatChange{0, 0, 0, 6, 0, 0}},
        PetEvent{"{name} sneezed a spark and singed the curtains.", StatChange{0, 0, -4, 0, 0, -3}},
        PetEvent{"{name} spotted a hawk and chased it for a lap.", StatChange{0, 6, -8, 0, 0, 0}},
        PetEvent{"{name} curled up on a warm rock for a moment.", StatChange{0, -6, 0, 2, 0, 0}},
    };
}

}  // namespace vpet
